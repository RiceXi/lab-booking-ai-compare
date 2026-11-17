"""输入校验层。

约定：每个 ``validate_*`` 函数返回 ``None`` 表示校验通过，
返回中文错误信息表示失败，调用方负责把信息展示给用户。
"""

from __future__ import annotations

import re
from datetime import date as date_cls

#: 时间粒度：30 分钟（需求文档第 5 节 MVP 时间规则）。
GRID_MINUTES = 30

_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def parse_time_to_minutes(value: str) -> int:
    """把 ``HH:mm`` 转换成当天零点起的分钟数。

    非法格式抛出 :class:`ValueError`。
    """
    match = _TIME_PATTERN.match((value or "").strip())
    if not match:
        raise ValueError(f"时间格式非法：{value!r}，应为 HH:mm")
    return int(match.group(1)) * 60 + int(match.group(2))


def validate_clock(value: str, field_label: str) -> str | None:
    """只校验 ``HH:mm`` 格式（用于设备可预约时段，允许任意分钟）。"""
    text = (value or "").strip()
    if not text:
        return f"{field_label}不能为空"
    if not _TIME_PATTERN.match(text):
        return f"{field_label}格式必须为 HH:mm（24 小时制），当前为：{value}"
    return None


def validate_time(value: str, field_label: str) -> str | None:
    """校验 ``HH:mm`` 格式，并要求落在 30 分钟粒度上（预约开始/结束时间）。"""
    error = validate_clock(value, field_label)
    if error:
        return error
    minutes = parse_time_to_minutes(value)
    if minutes % GRID_MINUTES != 0:
        return (
            f"{field_label}必须落在 30 分钟刻度上（例如 09:00、09:30、10:00），"
            f"当前为：{value.strip()}"
        )
    return None


def validate_date(value: str, field_label: str = "日期") -> str | None:
    """校验 ``YYYY-MM-DD`` 格式，并且必须是真实存在的日历日期。"""
    text = (value or "").strip()
    if not text:
        return f"{field_label}不能为空"
    match = _DATE_PATTERN.match(text)
    if not match:
        return f"{field_label}格式必须为 YYYY-MM-DD，当前为：{value}"
    try:
        date_cls(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return f"{field_label}不是合法的日历日期：{text}"
    return None


def validate_time_range(start_time: str, end_time: str) -> str | None:
    """校验开始时间早于结束时间，并要求两者都落在 30 分钟粒度上。"""
    start_error = validate_time(start_time, "开始时间")
    if start_error:
        return start_error
    end_error = validate_time(end_time, "结束时间")
    if end_error:
        return end_error
    if parse_time_to_minutes(start_time) >= parse_time_to_minutes(end_time):
        return "开始时间必须早于结束时间"
    return None


def validate_required(value: str, field_label: str, max_length: int = 64) -> str | None:
    """校验必填文本字段。"""
    text = (value or "").strip()
    if not text:
        return f"{field_label}不能为空"
    if len(text) > max_length:
        return f"{field_label}长度不能超过 {max_length} 个字符"
    return None


def validate_opening_hours(opening_start: str, opening_end: str) -> str | None:
    """校验设备每日可预约时段。"""
    start_error = validate_clock(opening_start, "可预约开始时间")
    if start_error:
        return start_error
    end_error = validate_clock(opening_end, "可预约结束时间")
    if end_error:
        return end_error
    if parse_time_to_minutes(opening_start) >= parse_time_to_minutes(opening_end):
        return "可预约开始时间必须早于可预约结束时间"
    return None
