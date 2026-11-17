"""输入校验单元测试。"""

from __future__ import annotations

import unittest

from app.validation import (
    parse_time_to_minutes,
    validate_clock,
    validate_date,
    validate_opening_hours,
    validate_required,
    validate_time,
    validate_time_range,
)


class ParseTimeTests(unittest.TestCase):
    def test_parse(self) -> None:
        self.assertEqual(parse_time_to_minutes("00:00"), 0)
        self.assertEqual(parse_time_to_minutes("09:30"), 570)
        self.assertEqual(parse_time_to_minutes("23:59"), 1439)

    def test_parse_invalid_raises(self) -> None:
        for value in ["24:00", "9:00", "09:60", "abc", "", "09:0"]:
            with self.assertRaises(ValueError):
                parse_time_to_minutes(value)


class ValidateClockTests(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertIsNone(validate_clock("00:00", "时间"))
        self.assertIsNone(validate_clock("23:59", "时间"))

    def test_empty(self) -> None:
        self.assertIsNotNone(validate_clock("", "开始时间"))

    def test_bad_format(self) -> None:
        self.assertIsNotNone(validate_clock("9:00", "开始时间"))
        self.assertIsNotNone(validate_clock("24:00", "开始时间"))
        self.assertIsNotNone(validate_clock("12:60", "开始时间"))


class ValidateTimeTests(unittest.TestCase):
    def test_grid_aligned(self) -> None:
        self.assertIsNone(validate_time("09:00", "开始时间"))
        self.assertIsNone(validate_time("09:30", "开始时间"))

    def test_not_on_grid(self) -> None:
        error = validate_time("09:15", "开始时间")
        self.assertIsNotNone(error)
        self.assertIn("30 分钟", error)


class ValidateDateTests(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertIsNone(validate_date("2026-11-17"))

    def test_empty(self) -> None:
        self.assertIsNotNone(validate_date(""))

    def test_bad_format(self) -> None:
        self.assertIsNotNone(validate_date("2026/11/17"))

    def test_not_a_calendar_date(self) -> None:
        self.assertIsNotNone(validate_date("2026-13-01"))
        self.assertIsNotNone(validate_date("2026-02-30"))


class ValidateTimeRangeTests(unittest.TestCase):
    def test_start_before_end(self) -> None:
        self.assertIsNone(validate_time_range("09:00", "10:00"))

    def test_equal_times_rejected(self) -> None:
        error = validate_time_range("09:00", "09:00")
        self.assertIsNotNone(error)
        self.assertIn("早于", error)

    def test_end_before_start_rejected(self) -> None:
        error = validate_time_range("10:00", "09:00")
        self.assertIsNotNone(error)
        self.assertIn("早于", error)

    def test_off_grid_rejected(self) -> None:
        self.assertIsNotNone(validate_time_range("09:00", "10:15"))


class ValidateRequiredTests(unittest.TestCase):
    def test_empty(self) -> None:
        self.assertIsNotNone(validate_required("   ", "预约人"))

    def test_too_long(self) -> None:
        self.assertIsNotNone(validate_required("x" * 100, "预约人"))

    def test_ok(self) -> None:
        self.assertIsNone(validate_required("张三", "预约人"))


class ValidateOpeningHoursTests(unittest.TestCase):
    def test_ok(self) -> None:
        self.assertIsNone(validate_opening_hours("08:00", "20:00"))

    def test_reversed(self) -> None:
        self.assertIsNotNone(validate_opening_hours("20:00", "08:00"))

    def test_equal(self) -> None:
        self.assertIsNotNone(validate_opening_hours("08:00", "08:00"))


if __name__ == "__main__":
    unittest.main()
