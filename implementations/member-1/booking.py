"""Business rules and SQLite persistence for the lab equipment booking app."""

from __future__ import annotations

import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator


EQUIPMENT_STATUSES = {"available", "maintenance", "retired"}
RESERVATION_STATUSES = {"booked", "in_use", "completed", "cancelled"}
ACTIVE_RESERVATION_STATUSES = {"booked", "in_use"}
STATUS_TRANSITIONS = {
    "booked": {"in_use", "cancelled"},
    "in_use": {"completed"},
    "completed": set(),
    "cancelled": set(),
}
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_LENGTHS = {
    "equipment_code": 40,
    "equipment_name": 80,
    "equipment_location": 120,
    "equipment_notes": 500,
    "requester": 80,
    "reservation_notes": 500,
}


class AppError(Exception):
    """An expected error that can be returned safely by the HTTP API."""

    def __init__(
        self,
        message: str,
        *,
        status: int = 400,
        code: str = "invalid_request",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.details = details or {}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _required_text(
    payload: dict[str, Any],
    key: str,
    label: str,
    *,
    max_length: int | None = None,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AppError(f"{label}不能为空", details={"field": key})
    value = value.strip()
    if max_length is not None and len(value) > max_length:
        raise AppError(
            f"{label}不能超过 {max_length} 个字符",
            details={"field": key, "max_length": max_length},
        )
    return value


def _optional_text(
    payload: dict[str, Any],
    key: str,
    label: str,
    *,
    max_length: int | None = None,
) -> str:
    value = payload.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise AppError(f"{label}必须是文本", details={"field": key})
    value = value.strip()
    if max_length is not None and len(value) > max_length:
        raise AppError(
            f"{label}不能超过 {max_length} 个字符",
            details={"field": key, "max_length": max_length},
        )
    return value


def _validate_date(value: str) -> str:
    if not DATE_PATTERN.fullmatch(value):
        raise AppError("日期格式必须为 YYYY-MM-DD", details={"field": "date"})
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise AppError("日期不合法", details={"field": "date"}) from exc
    return value


def _minutes(value: str) -> int:
    hours, minutes = (int(part) for part in value.split(":"))
    return hours * 60 + minutes


def _validate_time(
    value: str,
    label: str,
    field: str,
    *,
    require_half_hour: bool = True,
) -> tuple[str, int]:
    if not TIME_PATTERN.fullmatch(value):
        raise AppError(f"{label}格式必须为 HH:mm", details={"field": field})
    if require_half_hour and not value.endswith((":00", ":30")):
        raise AppError(
            f"{label}必须按 30 分钟粒度填写",
            details={"field": field},
        )
    return value, _minutes(value)


class BookingService:
    """Coordinates validation, conflict checks, and persistence."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS equipment (
                    id TEXT PRIMARY KEY,
                    code TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    location TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('available', 'maintenance', 'retired')
                    ),
                    opening_start TEXT NOT NULL,
                    opening_end TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reservations (
                    id TEXT PRIMARY KEY,
                    equipment_id TEXT NOT NULL,
                    requester TEXT NOT NULL,
                    date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (
                        status IN ('booked', 'in_use', 'completed', 'cancelled')
                    ),
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (equipment_id) REFERENCES equipment(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_reservations_equipment_date
                    ON reservations(equipment_id, date);
                CREATE INDEX IF NOT EXISTS idx_reservations_status
                    ON reservations(status);
                """
            )

    @staticmethod
    def _equipment_row(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _reservation_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result.pop("equipment_code", None)
        result.pop("equipment_name", None)
        result["equipment_code"] = row["equipment_code"]
        result["equipment_name"] = row["equipment_name"]
        return result

    def _clean_equipment(
        self,
        payload: dict[str, Any],
        *,
        default_available: bool,
    ) -> dict[str, Any]:
        code = _required_text(
            payload,
            "code",
            "设备编号",
            max_length=MAX_LENGTHS["equipment_code"],
        )
        name = _required_text(
            payload,
            "name",
            "设备名称",
            max_length=MAX_LENGTHS["equipment_name"],
        )
        location = _required_text(
            payload,
            "location",
            "存放位置",
            max_length=MAX_LENGTHS["equipment_location"],
        )
        status_value = payload.get("status", "available" if default_available else None)
        if status_value not in EQUIPMENT_STATUSES:
            raise AppError(
                "设备状态必须为 available、maintenance 或 retired",
                details={"field": "status"},
            )
        opening_start = _required_text(payload, "opening_start", "可用开始时间")
        opening_end = _required_text(payload, "opening_end", "可用结束时间")
        _, start_minutes = _validate_time(
            opening_start,
            "可用开始时间",
            "opening_start",
        )
        _, end_minutes = _validate_time(
            opening_end,
            "可用结束时间",
            "opening_end",
        )
        if start_minutes >= end_minutes:
            raise AppError(
                "可用开始时间必须早于结束时间",
                details={"field": "opening_end"},
            )
        return {
            "code": code,
            "name": name,
            "location": location,
            "status": status_value,
            "opening_start": opening_start,
            "opening_end": opening_end,
            "notes": _optional_text(
                payload,
                "notes",
                "设备备注",
                max_length=MAX_LENGTHS["equipment_notes"],
            ),
        }

    def list_equipment(self) -> list[dict[str, Any]]:
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT e.*,
                       SUM(CASE WHEN r.status IN ('booked', 'in_use')
                           THEN 1 ELSE 0 END) AS active_reservations
                FROM equipment e
                LEFT JOIN reservations r ON r.equipment_id = e.id
                GROUP BY e.id
                ORDER BY e.code COLLATE NOCASE ASC
                """
            ).fetchall()
        return [self._equipment_row(row) for row in rows]

    def get_equipment(self, equipment_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM equipment WHERE id = ?",
                (equipment_id,),
            ).fetchone()
        if row is None:
            raise AppError("设备不存在", status=404, code="equipment_not_found")
        return self._equipment_row(row)

    def create_equipment(self, payload: dict[str, Any]) -> dict[str, Any]:
        equipment = self._clean_equipment(payload, default_available=True)
        equipment_id = str(uuid.uuid4())
        timestamp = now_iso()
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    INSERT INTO equipment (
                        id, code, name, location, status, opening_start,
                        opening_end, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        equipment_id,
                        equipment["code"],
                        equipment["name"],
                        equipment["location"],
                        equipment["status"],
                        equipment["opening_start"],
                        equipment["opening_end"],
                        equipment["notes"],
                        timestamp,
                        timestamp,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            if "equipment.code" in str(exc):
                raise AppError(
                    "设备编号已存在，请换一个编号",
                    status=409,
                    code="equipment_code_exists",
                    details={"field": "code"},
                ) from exc
            raise
        return self.get_equipment(equipment_id)

    def update_equipment(
        self,
        equipment_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.get_equipment(equipment_id)
        equipment = self._clean_equipment(payload, default_available=False)
        try:
            with self._connection() as connection:
                connection.execute(
                    """
                    UPDATE equipment
                    SET code = ?, name = ?, location = ?, status = ?,
                        opening_start = ?, opening_end = ?, notes = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        equipment["code"],
                        equipment["name"],
                        equipment["location"],
                        equipment["status"],
                        equipment["opening_start"],
                        equipment["opening_end"],
                        equipment["notes"],
                        now_iso(),
                        equipment_id,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            if "equipment.code" in str(exc):
                raise AppError(
                    "设备编号已存在，请换一个编号",
                    status=409,
                    code="equipment_code_exists",
                    details={"field": "code"},
                ) from exc
            raise
        return self.get_equipment(equipment_id)

    def delete_equipment(self, equipment_id: str) -> None:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            equipment = connection.execute(
                "SELECT id FROM equipment WHERE id = ?",
                (equipment_id,),
            ).fetchone()
            if equipment is None:
                raise AppError(
                    "设备不存在",
                    status=404,
                    code="equipment_not_found",
                )
            active_count = connection.execute(
                """
                SELECT COUNT(*) FROM reservations
                WHERE equipment_id = ? AND status IN ('booked', 'in_use')
                """,
                (equipment_id,),
            ).fetchone()[0]
            if active_count:
                raise AppError(
                    "该设备仍有已预约或使用中的记录，取消或完成预约后才能删除",
                    status=409,
                    code="equipment_in_use",
                    details={"active_reservations": active_count},
                )
            connection.execute("DELETE FROM equipment WHERE id = ?", (equipment_id,))
            connection.commit()

    def list_reservations(
        self,
        *,
        equipment_id: str = "",
        reservation_date: str = "",
        status_value: str = "",
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        values: list[Any] = []
        if equipment_id:
            conditions.append("r.equipment_id = ?")
            values.append(equipment_id)
        if reservation_date:
            conditions.append("r.date = ?")
            values.append(_validate_date(reservation_date))
        if status_value:
            if status_value not in RESERVATION_STATUSES:
                raise AppError(
                    "预约状态筛选条件不合法",
                    details={"field": "status"},
                )
            conditions.append("r.status = ?")
            values.append(status_value)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT r.*, e.code AS equipment_code, e.name AS equipment_name
                FROM reservations r
                JOIN equipment e ON e.id = r.equipment_id
                {where}
                ORDER BY r.date DESC, r.start_time ASC, r.created_at DESC
                """,
                values,
            ).fetchall()
        return [self._reservation_row(row) for row in rows]

    def get_reservation(self, reservation_id: str) -> dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT r.*, e.code AS equipment_code, e.name AS equipment_name
                FROM reservations r
                JOIN equipment e ON e.id = r.equipment_id
                WHERE r.id = ?
                """,
                (reservation_id,),
            ).fetchone()
        if row is None:
            raise AppError(
                "预约记录不存在",
                status=404,
                code="reservation_not_found",
            )
        return self._reservation_row(row)

    def create_reservation(self, payload: dict[str, Any]) -> dict[str, Any]:
        equipment_id = _required_text(payload, "equipment_id", "设备")
        requester = _required_text(
            payload,
            "requester",
            "预约人",
            max_length=MAX_LENGTHS["requester"],
        )
        reservation_date = _validate_date(_required_text(payload, "date", "预约日期"))
        start_time = _required_text(payload, "start_time", "开始时间")
        end_time = _required_text(payload, "end_time", "结束时间")
        _, start_minutes = _validate_time(start_time, "开始时间", "start_time")
        _, end_minutes = _validate_time(end_time, "结束时间", "end_time")
        if start_minutes >= end_minutes:
            raise AppError(
                "开始时间必须早于结束时间",
                details={"field": "end_time"},
            )
        notes = _optional_text(
            payload,
            "notes",
            "预约备注",
            max_length=MAX_LENGTHS["reservation_notes"],
        )

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            equipment = connection.execute(
                "SELECT * FROM equipment WHERE id = ?",
                (equipment_id,),
            ).fetchone()
            if equipment is None:
                raise AppError(
                    "设备不存在",
                    status=404,
                    code="equipment_not_found",
                )
            if equipment["status"] != "available":
                raise AppError(
                    "该设备当前不可预约",
                    status=409,
                    code="equipment_unavailable",
                )
            opening_start = _minutes(equipment["opening_start"])
            opening_end = _minutes(equipment["opening_end"])
            if start_minutes < opening_start or end_minutes > opening_end:
                raise AppError(
                    (
                        f"预约时间必须位于设备开放时段 "
                        f"{equipment['opening_start']}-{equipment['opening_end']} 内"
                    ),
                    details={"field": "start_time"},
                )
            conflict = connection.execute(
                """
                SELECT start_time, end_time, requester
                FROM reservations
                WHERE equipment_id = ?
                  AND date = ?
                  AND status IN ('booked', 'in_use')
                  AND ? < end_time
                  AND start_time < ?
                ORDER BY start_time ASC
                LIMIT 1
                """,
                (equipment_id, reservation_date, start_time, end_time),
            ).fetchone()
            if conflict is not None:
                raise AppError(
                    (
                        f"预约时间冲突：{conflict['start_time']}-"
                        f"{conflict['end_time']} 已被 {conflict['requester']} 预约"
                    ),
                    status=409,
                    code="reservation_conflict",
                    details={
                        "conflict_start": conflict["start_time"],
                        "conflict_end": conflict["end_time"],
                    },
                )
            reservation_id = str(uuid.uuid4())
            timestamp = now_iso()
            connection.execute(
                """
                INSERT INTO reservations (
                    id, equipment_id, requester, date, start_time, end_time,
                    status, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'booked', ?, ?, ?)
                """,
                (
                    reservation_id,
                    equipment_id,
                    requester,
                    reservation_date,
                    start_time,
                    end_time,
                    notes,
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self.get_reservation(reservation_id)

    def update_reservation_status(
        self,
        reservation_id: str,
        new_status: str,
    ) -> dict[str, Any]:
        if new_status not in RESERVATION_STATUSES:
            raise AppError(
                "预约状态不合法",
                details={"field": "status"},
            )
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM reservations WHERE id = ?",
                (reservation_id,),
            ).fetchone()
            if row is None:
                raise AppError(
                    "预约记录不存在",
                    status=404,
                    code="reservation_not_found",
                )
            current_status = row["status"]
            if new_status == current_status:
                return self.get_reservation(reservation_id)
            if new_status not in STATUS_TRANSITIONS[current_status]:
                raise AppError(
                    f"预约状态不能从 {current_status} 变更为 {new_status}",
                    status=409,
                    code="invalid_status_transition",
                )
            connection.execute(
                "UPDATE reservations SET status = ?, updated_at = ? WHERE id = ?",
                (new_status, now_iso(), reservation_id),
            )
            connection.commit()
        return self.get_reservation(reservation_id)

    def stats(self) -> dict[str, Any]:
        with self._connection() as connection:
            counts = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM equipment) AS equipment_count,
                    SUM(CASE WHEN status IN ('booked', 'in_use')
                        THEN 1 ELSE 0 END) AS active_count,
                    SUM(CASE WHEN status = 'cancelled'
                        THEN 1 ELSE 0 END) AS cancelled_count,
                    SUM(CASE WHEN status = 'completed'
                        THEN 1 ELSE 0 END) AS completed_count
                FROM reservations
                """
            ).fetchone()
            by_equipment = connection.execute(
                """
                SELECT e.id, e.code, e.name, e.location, e.status,
                       SUM(CASE WHEN r.status IN ('booked', 'in_use', 'completed')
                           THEN 1 ELSE 0 END) AS reservation_count,
                       COALESCE(SUM(
                           CASE WHEN r.status IN ('booked', 'in_use', 'completed')
                           THEN (
                               (CAST(substr(r.end_time, 1, 2) AS INTEGER) * 60
                                + CAST(substr(r.end_time, 4, 2) AS INTEGER))
                               -
                               (CAST(substr(r.start_time, 1, 2) AS INTEGER) * 60
                                + CAST(substr(r.start_time, 4, 2) AS INTEGER))
                           ) ELSE 0 END
                       ), 0) AS booked_minutes
                FROM equipment e
                LEFT JOIN reservations r ON r.equipment_id = e.id
                GROUP BY e.id
                ORDER BY reservation_count DESC, e.code COLLATE NOCASE ASC
                """
            ).fetchall()
        return {
            "equipment_count": counts["equipment_count"],
            "active_count": counts["active_count"] or 0,
            "cancelled_count": counts["cancelled_count"] or 0,
            "completed_count": counts["completed_count"] or 0,
            "by_equipment": [dict(row) for row in by_equipment],
        }
