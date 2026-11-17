"""冲突检测层。

时间区间按半开区间 ``[start_time, end_time)`` 处理，
因此首尾相接（09:00-10:00 与 10:00-11:00）不算冲突。
"""

from __future__ import annotations

from collections.abc import Iterable

from .models import ACTIVE_RESERVATION_STATUSES, Reservation
from .validation import parse_time_to_minutes


def time_overlaps(new_start: str, new_end: str, old_start: str, old_end: str) -> bool:
    """判断两个时间区间是否重叠。

    判定条件（docs/data-schema.md 第 4 节）::

        new.start_time < old.end_time AND old.start_time < new.end_time
    """
    return (
        parse_time_to_minutes(new_start) < parse_time_to_minutes(old_end)
        and parse_time_to_minutes(old_start) < parse_time_to_minutes(new_end)
    )


def find_conflicts(
    *,
    equipment_id: str,
    date: str,
    start_time: str,
    end_time: str,
    reservations: Iterable[Reservation],
    exclude_id: str | None = None,
) -> list[Reservation]:
    """找出与给定时间冲突的有效预约。

    只与同设备、同日期、状态为 ``booked`` 或 ``in_use`` 的预约比较；
    已取消和已完成的预约不参与判断。
    """
    conflicts: list[Reservation] = []
    for reservation in reservations:
        if exclude_id is not None and reservation.id == exclude_id:
            continue
        if reservation.equipment_id != equipment_id:
            continue
        if reservation.date != date:
            continue
        if reservation.status.value not in ACTIVE_RESERVATION_STATUSES:
            continue
        if time_overlaps(start_time, end_time, reservation.start_time, reservation.end_time):
            conflicts.append(reservation)
    return sorted(conflicts, key=lambda item: (item.start_time, item.created_at))
