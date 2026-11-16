"""Additional edge-case and concurrency checks for the booking rules."""

from __future__ import annotations

import tempfile
import threading
import unittest
from pathlib import Path

from booking import AppError, BookingService


class BookingRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = BookingService(Path(self.temp_dir.name) / "rules.sqlite")
        self.equipment = self.service.create_equipment(
            {
                "code": "RULE-001",
                "name": "规则测试设备",
                "location": "实验楼 D-101",
                "status": "available",
                "opening_start": "08:00",
                "opening_end": "18:00",
            }
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def book(
        self,
        start_time: str = "09:00",
        end_time: str = "10:00",
        *,
        requester: str = "规则测试",
        date_value: str = "2026-11-23",
    ) -> dict:
        return self.service.create_reservation(
            {
                "equipment_id": self.equipment["id"],
                "requester": requester,
                "date": date_value,
                "start_time": start_time,
                "end_time": end_time,
            }
        )

    def test_time_must_use_thirty_minute_increments(self) -> None:
        with self.assertRaises(AppError) as context:
            self.book("09:15", "10:15")
        self.assertIn("30 分钟粒度", context.exception.message)

    def test_reservation_must_stay_inside_opening_hours(self) -> None:
        for start_time, end_time in [("07:30", "08:30"), ("17:30", "18:30")]:
            with self.subTest(start_time=start_time, end_time=end_time):
                with self.assertRaises(AppError) as context:
                    self.book(start_time, end_time)
                self.assertIn("设备开放时段", context.exception.message)

    def test_completed_reservation_does_not_block_its_time(self) -> None:
        first = self.book("09:00", "10:00")
        self.service.update_reservation_status(first["id"], "in_use")
        self.service.update_reservation_status(first["id"], "completed")
        replacement = self.book("09:00", "10:00", requester="后续预约")
        self.assertEqual("booked", replacement["status"])

    def test_illegal_status_transitions_are_rejected(self) -> None:
        first = self.book()
        with self.assertRaises(AppError) as context:
            self.service.update_reservation_status(first["id"], "completed")
        self.assertEqual("invalid_status_transition", context.exception.code)

        self.service.update_reservation_status(first["id"], "cancelled")
        with self.assertRaises(AppError) as context:
            self.service.update_reservation_status(first["id"], "booked")
        self.assertEqual("invalid_status_transition", context.exception.code)

    def test_equipment_edit_rejects_another_devices_code(self) -> None:
        second = self.service.create_equipment(
            {
                "code": "RULE-002",
                "name": "第二台设备",
                "location": "实验楼 D-102",
                "status": "available",
                "opening_start": "08:00",
                "opening_end": "18:00",
            }
        )
        with self.assertRaises(AppError) as context:
            self.service.update_equipment(
                second["id"],
                {**second, "code": self.equipment["code"]},
            )
        self.assertEqual("equipment_code_exists", context.exception.code)

    def test_equipment_text_limits_are_enforced_by_the_service(self) -> None:
        base_payload = {
            "code": "LIMIT-001",
            "name": "长度测试设备",
            "location": "实验楼 E-101",
            "status": "available",
            "opening_start": "08:00",
            "opening_end": "18:00",
            "notes": "",
        }
        cases = [
            ("code", "X" * 41, 40),
            ("name", "名" * 81, 80),
            ("location", "址" * 121, 120),
            ("notes", "注" * 501, 500),
        ]
        for field, value, max_length in cases:
            with self.subTest(field=field):
                with self.assertRaises(AppError) as context:
                    self.service.create_equipment({**base_payload, field: value})
                self.assertEqual(field, context.exception.details["field"])
                self.assertEqual(
                    max_length,
                    context.exception.details["max_length"],
                )

    def test_reservation_text_limits_are_enforced_by_the_service(self) -> None:
        payload = {
            "equipment_id": self.equipment["id"],
            "requester": "张同学",
            "date": "2026-11-25",
            "start_time": "09:00",
            "end_time": "10:00",
            "notes": "",
        }
        cases = [
            ("requester", "人" * 81, 80),
            ("notes", "注" * 501, 500),
        ]
        for field, value, max_length in cases:
            with self.subTest(field=field):
                with self.assertRaises(AppError) as context:
                    self.service.create_reservation({**payload, field: value})
                self.assertEqual(field, context.exception.details["field"])
                self.assertEqual(
                    max_length,
                    context.exception.details["max_length"],
                )

    def test_concurrent_overlapping_requests_create_only_one_booking(self) -> None:
        barrier = threading.Barrier(2)
        outcomes: list[str] = []
        outcomes_lock = threading.Lock()

        def create(requester: str) -> None:
            barrier.wait(timeout=3)
            try:
                self.book(
                    "14:00",
                    "15:00",
                    requester=requester,
                    date_value="2026-11-24",
                )
                outcome = "created"
            except AppError as error:
                outcome = error.code
            with outcomes_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=create, args=("并发甲",)),
            threading.Thread(target=create, args=("并发乙",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=12)

        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertCountEqual(["created", "reservation_conflict"], outcomes)
        self.assertEqual(
            1,
            len(
                self.service.list_reservations(
                    equipment_id=self.equipment["id"],
                    reservation_date="2026-11-24",
                )
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
