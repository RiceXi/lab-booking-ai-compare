"""领域模型层。

本模块只描述"数据长什么样"，不包含校验规则、持久化和界面逻辑。
字段名称、类型和取值范围严格对应 ``docs/data-schema.md``，不额外添加业务字段，
以便与其他成员的实现保持字段语义一致。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from .validation import parse_time_to_minutes


def new_id() -> str:
    """生成系统唯一标识。"""
    return uuid.uuid4().hex


def now_iso() -> str:
    """生成 ISO 8601 时间戳，例如 ``2026-11-17T21:24:00+08:00``。"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


class EquipmentStatus(str, Enum):
    """设备状态。"""

    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class ReservationStatus(str, Enum):
    """预约状态。"""

    BOOKED = "booked"
    IN_USE = "in_use"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


EQUIPMENT_STATUS_LABELS: dict[str, str] = {
    EquipmentStatus.AVAILABLE.value: "可预约",
    EquipmentStatus.MAINTENANCE.value: "维护中",
    EquipmentStatus.RETIRED.value: "已停用",
}

RESERVATION_STATUS_LABELS: dict[str, str] = {
    ReservationStatus.BOOKED.value: "已预约",
    ReservationStatus.IN_USE.value: "使用中",
    ReservationStatus.COMPLETED.value: "已完成",
    ReservationStatus.CANCELLED.value: "已取消",
}

#: 有效预约状态：占用设备时间，参与冲突判断，并阻止设备被删除。
ACTIVE_RESERVATION_STATUSES: tuple[str, ...] = (
    ReservationStatus.BOOKED.value,
    ReservationStatus.IN_USE.value,
)

#: 允许的状态流转（docs/data-schema.md 第 3 节）。
#: 未列出的流转一律禁止，包括 completed->in_use、cancelled->booked、completed->cancelled。
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    ReservationStatus.BOOKED.value: (
        ReservationStatus.IN_USE.value,
        ReservationStatus.CANCELLED.value,
    ),
    ReservationStatus.IN_USE.value: (ReservationStatus.COMPLETED.value,),
    ReservationStatus.COMPLETED.value: (),
    ReservationStatus.CANCELLED.value: (),
}


def _enum_value(value: Any, enum_cls: type[Enum], fallback: Enum) -> Enum:
    """把读取到的原始值转换成枚举；无法识别时回退到默认值。"""
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, TypeError):
        return fallback


@dataclass
class Equipment:
    """设备。字段语义见 docs/data-schema.md 第 1 节。"""

    id: str
    code: str
    name: str
    location: str
    status: EquipmentStatus
    opening_start: str
    opening_end: str
    notes: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    @property
    def status_label(self) -> str:
        return EQUIPMENT_STATUS_LABELS.get(self.status.value, self.status.value)

    @property
    def opening_hours(self) -> str:
        return f"{self.opening_start}-{self.opening_end}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "location": self.location,
            "status": self.status.value,
            "opening_start": self.opening_start,
            "opening_end": self.opening_end,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Equipment":
        return cls(
            id=str(data.get("id") or new_id()),
            code=str(data.get("code", "")),
            name=str(data.get("name", "")),
            location=str(data.get("location", "")),
            status=_enum_value(
                data.get("status"), EquipmentStatus, EquipmentStatus.AVAILABLE
            ),
            opening_start=str(data.get("opening_start", "")),
            opening_end=str(data.get("opening_end", "")),
            notes=str(data.get("notes", "") or ""),
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
        )


@dataclass
class Reservation:
    """预约。字段语义见 docs/data-schema.md 第 2 节。"""

    id: str
    equipment_id: str
    requester: str
    date: str
    start_time: str
    end_time: str
    status: ReservationStatus
    notes: str = ""
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)

    @property
    def status_label(self) -> str:
        return RESERVATION_STATUS_LABELS.get(self.status.value, self.status.value)

    @property
    def time_range(self) -> str:
        return f"{self.start_time}-{self.end_time}"

    @property
    def duration_minutes(self) -> int:
        """占用时长（分钟）。"""
        return parse_time_to_minutes(self.end_time) - parse_time_to_minutes(self.start_time)

    @property
    def is_active(self) -> bool:
        """是否属于有效预约（占用设备时间）。"""
        return self.status.value in ACTIVE_RESERVATION_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "requester": self.requester,
            "date": self.date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status.value,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reservation":
        return cls(
            id=str(data.get("id") or new_id()),
            equipment_id=str(data.get("equipment_id", "")),
            requester=str(data.get("requester", "")),
            date=str(data.get("date", "")),
            start_time=str(data.get("start_time", "")),
            end_time=str(data.get("end_time", "")),
            status=_enum_value(
                data.get("status"), ReservationStatus, ReservationStatus.BOOKED
            ),
            notes=str(data.get("notes", "") or ""),
            created_at=str(data.get("created_at") or now_iso()),
            updated_at=str(data.get("updated_at") or now_iso()),
        )
