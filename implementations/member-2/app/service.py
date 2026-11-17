"""业务服务层。

界面层只负责收集输入和展示结果，所有业务规则（唯一性校验、冲突检测、
状态流转、删除保护、统计口径）都集中在这里，便于测试与复用。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date as date_cls
from datetime import timedelta

from .conflict import find_conflicts
from .errors import ConflictError, ValidationError
from .models import (
    ACTIVE_RESERVATION_STATUSES,
    ALLOWED_TRANSITIONS,
    EQUIPMENT_STATUS_LABELS,
    RESERVATION_STATUS_LABELS,
    Equipment,
    EquipmentStatus,
    Reservation,
    ReservationStatus,
    new_id,
    now_iso,
)
from .store import JsonStore
from .validation import (
    parse_time_to_minutes,
    validate_date,
    validate_opening_hours,
    validate_required,
    validate_time_range,
)


@dataclass
class ReservationFilter:
    """预约筛选条件；全部为 ``None`` 表示不限制。"""

    equipment_id: str | None = None
    date: str | None = None
    status: str | None = None


@dataclass
class EquipmentStat:
    """单台设备的统计结果。"""

    equipment_id: str
    code: str
    name: str
    reservation_count: int = 0
    usage_minutes: int = 0


@dataclass
class Statistics:
    """统计与可视化所需的汇总数据。"""

    equipment_total: int = 0
    active_total: int = 0
    cancelled_total: int = 0
    completed_total: int = 0
    total_minutes: int = 0
    per_equipment: list[EquipmentStat] = field(default_factory=list)
    per_status: list[tuple[str, int]] = field(default_factory=list)


class LabService:
    """实验室设备预约管理器的业务入口。"""

    def __init__(self, store: JsonStore) -> None:
        self.store = store
        self._equipment: list[Equipment] = []
        self._reservations: list[Reservation] = []
        self._listeners: list[Callable[[], None]] = []
        self.reload()

    # ------------------------------------------------------------- 基础设施
    def reload(self) -> None:
        """从数据文件重新加载全部数据。"""
        self._equipment, self._reservations = self.store.load()

    def _persist(self) -> None:
        """写盘并通知界面刷新。"""
        self.store.save(self._equipment, self._reservations)
        self._notify()

    def add_listener(self, callback: Callable[[], None]) -> None:
        """注册数据变化回调（界面用它做跨页签刷新）。"""
        self._listeners.append(callback)

    def _notify(self) -> None:
        for callback in list(self._listeners):
            try:
                callback()
            except Exception:  # pragma: no cover - 界面刷新失败不应影响业务数据
                pass

    # ---------------------------------------------------------------- 设备
    def list_equipment(self) -> list[Equipment]:
        """按设备编号排序返回全部设备。"""
        return sorted(self._equipment, key=lambda item: item.code.lower())

    def get_equipment(self, equipment_id: str) -> Equipment | None:
        for item in self._equipment:
            if item.id == equipment_id:
                return item
        return None

    def find_equipment_by_code(self, code: str) -> Equipment | None:
        target = (code or "").strip().lower()
        for item in self._equipment:
            if item.code.strip().lower() == target:
                return item
        return None

    def bookable_equipment(self) -> list[Equipment]:
        """返回状态为 available 的设备。"""
        return [item for item in self.list_equipment() if item.status is EquipmentStatus.AVAILABLE]

    def _validate_equipment_fields(
        self,
        *,
        code: str,
        name: str,
        location: str,
        status: str,
        opening_start: str,
        opening_end: str,
        exclude_id: str | None = None,
    ) -> tuple[str, str, str, EquipmentStatus, str, str]:
        code = (code or "").strip()
        name = (name or "").strip()
        location = (location or "").strip()

        error = validate_required(code, "设备编号")
        if error:
            raise ValidationError(error)
        error = validate_required(name, "设备名称")
        if error:
            raise ValidationError(error)
        error = validate_required(location, "存放位置")
        if error:
            raise ValidationError(error)

        # 设备编号全局唯一（不区分大小写）。
        duplicated = self.find_equipment_by_code(code)
        if duplicated is not None and duplicated.id != exclude_id:
            raise ValidationError(f"设备编号「{code}」已存在，请更换编号")

        try:
            equipment_status = EquipmentStatus(status)
        except (ValueError, TypeError):
            raise ValidationError(f"设备状态非法：{status}") from None

        error = validate_opening_hours(opening_start, opening_end)
        if error:
            raise ValidationError(error)

        return code, name, location, equipment_status, opening_start.strip(), opening_end.strip()

    def add_equipment(
        self,
        *,
        code: str,
        name: str,
        location: str,
        status: str = EquipmentStatus.AVAILABLE.value,
        opening_start: str,
        opening_end: str,
        notes: str = "",
    ) -> Equipment:
        """新增设备。"""
        code, name, location, equipment_status, opening_start, opening_end = (
            self._validate_equipment_fields(
                code=code,
                name=name,
                location=location,
                status=status,
                opening_start=opening_start,
                opening_end=opening_end,
            )
        )
        equipment = Equipment(
            id=new_id(),
            code=code,
            name=name,
            location=location,
            status=equipment_status,
            opening_start=opening_start,
            opening_end=opening_end,
            notes=(notes or "").strip(),
        )
        self._equipment.append(equipment)
        self._persist()
        return equipment

    def update_equipment(
        self,
        equipment_id: str,
        *,
        code: str,
        name: str,
        location: str,
        status: str,
        opening_start: str,
        opening_end: str,
        notes: str = "",
    ) -> Equipment:
        """编辑设备。"""
        equipment = self.get_equipment(equipment_id)
        if equipment is None:
            raise ValidationError("设备不存在，可能已被删除")

        code, name, location, equipment_status, opening_start, opening_end = (
            self._validate_equipment_fields(
                code=code,
                name=name,
                location=location,
                status=status,
                opening_start=opening_start,
                opening_end=opening_end,
                exclude_id=equipment_id,
            )
        )
        equipment.code = code
        equipment.name = name
        equipment.location = location
        equipment.status = equipment_status
        equipment.opening_start = opening_start
        equipment.opening_end = opening_end
        equipment.notes = (notes or "").strip()
        equipment.updated_at = now_iso()
        self._persist()
        return equipment

    def active_reservations_of(self, equipment_id: str) -> list[Reservation]:
        """返回某设备上状态为 booked / in_use 的预约。"""
        return [
            item
            for item in self._reservations
            if item.equipment_id == equipment_id
            and item.status.value in ACTIVE_RESERVATION_STATUSES
        ]

    def history_reservations_of(self, equipment_id: str) -> list[Reservation]:
        """返回某设备上的历史预约（已完成 / 已取消）。"""
        return [
            item
            for item in self._reservations
            if item.equipment_id == equipment_id
            and item.status.value not in ACTIVE_RESERVATION_STATUSES
        ]

    def delete_equipment(self, equipment_id: str, keep_history: bool = True) -> None:
        """删除设备。

        设备存在有效预约时禁止删除（需求 FR8、数据契约第 5 节）。
        ``keep_history=True`` 时保留历史预约，历史预约不占用时间，不影响后续预约冲突。
        """
        equipment = self.get_equipment(equipment_id)
        if equipment is None:
            raise ValidationError("设备不存在，可能已被删除")

        active = self.active_reservations_of(equipment_id)
        if active:
            detail = "、".join(
                f"{item.date} {item.time_range}（{item.requester}，{item.status_label}）"
                for item in active
            )
            raise ValidationError(
                f"设备「{equipment.code} {equipment.name}」仍有 {len(active)} 条有效预约："
                f"{detail}。请先取消或完成这些预约，再删除设备。"
            )

        self._equipment = [item for item in self._equipment if item.id != equipment_id]
        if not keep_history:
            self._reservations = [
                item for item in self._reservations if item.equipment_id != equipment_id
            ]
        self._persist()

    # ---------------------------------------------------------------- 预约
    def list_reservations(self, filters: ReservationFilter | None = None) -> list[Reservation]:
        """按设备 / 日期 / 状态筛选预约，多个条件之间为"与"关系。"""
        filters = filters or ReservationFilter()
        result = []
        for item in self._reservations:
            if filters.equipment_id and item.equipment_id != filters.equipment_id:
                continue
            if filters.date and item.date != filters.date:
                continue
            if filters.status and item.status.value != filters.status:
                continue
            result.append(item)
        return sorted(result, key=lambda r: (r.date, r.start_time, r.created_at))

    def get_reservation(self, reservation_id: str) -> Reservation | None:
        for item in self._reservations:
            if item.id == reservation_id:
                return item
        return None

    def add_reservation(
        self,
        *,
        equipment_id: str,
        requester: str,
        date: str,
        start_time: str,
        end_time: str,
        notes: str = "",
    ) -> Reservation:
        """创建预约，并执行全部冲突与可预约性检查。"""
        equipment = self.get_equipment(equipment_id)
        if equipment is None:
            raise ValidationError("请选择一个有效的设备")

        if equipment.status is not EquipmentStatus.AVAILABLE:
            raise ValidationError(
                f"设备「{equipment.code} {equipment.name}」当前状态为"
                f"「{EQUIPMENT_STATUS_LABELS[equipment.status.value]}」，不可创建新预约。"
            )

        requester = (requester or "").strip()
        error = validate_required(requester, "预约人")
        if error:
            raise ValidationError(error)

        error = validate_date(date)
        if error:
            raise ValidationError(error)

        error = validate_time_range(start_time, end_time)
        if error:
            raise ValidationError(error)

        start_minutes = parse_time_to_minutes(start_time)
        end_minutes = parse_time_to_minutes(end_time)
        opening_start = parse_time_to_minutes(equipment.opening_start)
        opening_end = parse_time_to_minutes(equipment.opening_end)
        if start_minutes < opening_start or end_minutes > opening_end:
            raise ValidationError(
                f"预约时间必须落在设备可预约时段 {equipment.opening_start}-{equipment.opening_end} 之内"
            )

        conflicts = find_conflicts(
            equipment_id=equipment.id,
            date=date.strip(),
            start_time=start_time.strip(),
            end_time=end_time.strip(),
            reservations=self._reservations,
        )
        if conflicts:
            detail = "、".join(
                f"{item.date} {item.time_range}（{item.requester}，{item.status_label}）"
                for item in conflicts
            )
            raise ConflictError(
                f"创建失败：与已有预约时间冲突——{detail}。"
                "同一设备的同一时间只能有一条有效预约，请调整时间或先取消原预约。",
                conflicts=conflicts,
            )

        reservation = Reservation(
            id=new_id(),
            equipment_id=equipment.id,
            requester=requester,
            date=date.strip(),
            start_time=start_time.strip(),
            end_time=end_time.strip(),
            status=ReservationStatus.BOOKED,
            notes=(notes or "").strip(),
        )
        self._reservations.append(reservation)
        self._persist()
        return reservation

    def transition(self, reservation_id: str, target: ReservationStatus) -> Reservation:
        """按数据契约执行状态流转。"""
        reservation = self.get_reservation(reservation_id)
        if reservation is None:
            raise ValidationError("预约不存在，可能已被删除")

        current = reservation.status
        if current is target:
            return reservation

        allowed = ALLOWED_TRANSITIONS.get(current.value, ())
        if target.value not in allowed:
            source_label = RESERVATION_STATUS_LABELS.get(current.value, current.value)
            target_label = RESERVATION_STATUS_LABELS.get(target.value, target.value)
            if allowed:
                allowed_text = "、".join(
                    RESERVATION_STATUS_LABELS.get(value, value) for value in allowed
                )
                raise ValidationError(
                    f"不允许从「{source_label}」流转到「{target_label}」。"
                    f"当前状态只能流转为：{allowed_text}。"
                )
            raise ValidationError(
                f"不允许从「{source_label}」流转到「{target_label}」。"
                f"预约已处于终态，不能再变更状态。"
            )

        reservation.status = target
        reservation.updated_at = now_iso()
        self._persist()
        return reservation

    def cancel_reservation(self, reservation_id: str) -> Reservation:
        """取消预约（booked -> cancelled）。"""
        return self.transition(reservation_id, ReservationStatus.CANCELLED)

    def start_use(self, reservation_id: str) -> Reservation:
        """开始使用（booked -> in_use）。"""
        return self.transition(reservation_id, ReservationStatus.IN_USE)

    def complete_reservation(self, reservation_id: str) -> Reservation:
        """完成预约（in_use -> completed）。"""
        return self.transition(reservation_id, ReservationStatus.COMPLETED)

    # ---------------------------------------------------------------- 统计
    def statistics(self) -> Statistics:
        """统计设备数、预约数与使用时长。"""
        stats = Statistics(equipment_total=len(self._equipment))
        status_counter: dict[str, int] = {value: 0 for value in RESERVATION_STATUS_LABELS}

        for reservation in self._reservations:
            status_counter[reservation.status.value] = (
                status_counter.get(reservation.status.value, 0) + 1
            )
            if reservation.status.value == ReservationStatus.CANCELLED.value:
                continue
            stats.total_minutes += reservation.duration_minutes

        stats.active_total = sum(
            status_counter.get(value, 0) for value in ACTIVE_RESERVATION_STATUSES
        )
        stats.cancelled_total = status_counter.get(ReservationStatus.CANCELLED.value, 0)
        stats.completed_total = status_counter.get(ReservationStatus.COMPLETED.value, 0)

        equipment_index = {item.id: item for item in self._equipment}
        counters: dict[str, EquipmentStat] = {}
        for equipment in self._equipment:
            counters[equipment.id] = EquipmentStat(
                equipment_id=equipment.id, code=equipment.code, name=equipment.name
            )
        for reservation in self._reservations:
            if reservation.status.value == ReservationStatus.CANCELLED.value:
                continue
            counter = counters.get(reservation.equipment_id)
            if counter is None:
                # 设备已被删除但保留了历史预约：用占位设备统计。
                counter = EquipmentStat(
                    equipment_id=reservation.equipment_id,
                    code="(已删除)",
                    name=self._history_equipment_name(reservation.equipment_id, equipment_index),
                )
                counters[reservation.equipment_id] = counter
            counter.reservation_count += 1
            counter.usage_minutes += reservation.duration_minutes

        stats.per_equipment = sorted(
            counters.values(), key=lambda item: (-item.reservation_count, item.code.lower())
        )
        stats.per_status = [
            (RESERVATION_STATUS_LABELS[value], status_counter.get(value, 0))
            for value in (
                ReservationStatus.BOOKED.value,
                ReservationStatus.IN_USE.value,
                ReservationStatus.COMPLETED.value,
                ReservationStatus.CANCELLED.value,
            )
        ]
        return stats

    @staticmethod
    def _history_equipment_name(
        equipment_id: str, equipment_index: dict[str, Equipment]
    ) -> str:
        equipment = equipment_index.get(equipment_id)
        if equipment is not None:
            return equipment.name
        return "已删除设备"

    # ------------------------------------------------------------ 演示数据
    def seed_demo_data(self) -> None:
        """写入一组演示数据（仅在数据文件为空时使用）。"""
        if self._equipment or self._reservations:
            return
        today = date_cls.today()
        equipment_specs = [
            ("EQ-001", "高速离心机", "生化楼 A-201", "available", "08:00", "20:00", "需提前预约"),
            ("EQ-002", "PCR 扩增仪", "生化楼 A-305", "available", "09:00", "18:00", ""),
            ("EQ-003", "激光共聚焦显微镜", "光学楼 B-102", "maintenance", "08:00", "22:00", "维护中"),
            ("EQ-004", "恒温培养箱", "微生物楼 C-210", "available", "07:30", "21:30", ""),
        ]
        for code, name, location, status, start, end, notes in equipment_specs:
            self.add_equipment(
                code=code,
                name=name,
                location=location,
                status=status,
                opening_start=start,
                opening_end=end,
                notes=notes,
            )
        by_code = {item.code: item for item in self._equipment}
        day1 = today.isoformat()
        day2 = (today + timedelta(days=1)).isoformat()
        demo_reservations = [
            ("EQ-001", "张三", day1, "09:00", "10:30", ""),
            ("EQ-001", "李四", day1, "11:00", "12:00", "与上一条首尾相接，不冲突"),
            ("EQ-002", "王五", day1, "14:00", "16:00", ""),
            ("EQ-004", "赵六", day2, "09:30", "11:30", ""),
            ("EQ-002", "孙七", day2, "10:00", "11:00", ""),
        ]
        for code, requester, day, start, end, notes in demo_reservations:
            equipment = by_code.get(code)
            if equipment is None:
                continue
            self.add_reservation(
                equipment_id=equipment.id,
                requester=requester,
                date=day,
                start_time=start,
                end_time=end,
                notes=notes,
            )
        # 制造一条已取消和一条已完成的预约，用于统计与状态流转演示。
        first = self.list_reservations()[0]
        self.start_use(first.id)
        self.complete_reservation(first.id)
        second = self.list_reservations()[1]
        self.cancel_reservation(second.id)
