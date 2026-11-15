"""Acceptance tests matching docs/acceptance.md, AC1 through AC12."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from booking import AppError, BookingService


class AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "acceptance.sqlite"
        self.service = BookingService(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def add_equipment(
        self,
        code: str = "LAB-001",
        *,
        status: str = "available",
        opening_start: str = "08:00",
        opening_end: str = "18:00",
    ) -> dict:
        return self.service.create_equipment(
            {
                "code": code,
                "name": f"设备 {code}",
                "location": "实验楼 A-101",
                "status": status,
                "opening_start": opening_start,
                "opening_end": opening_end,
                "notes": "验收测试",
            }
        )

    def add_reservation(
        self,
        equipment_id: str,
        start_time: str = "09:00",
        end_time: str = "10:00",
        *,
        requester: str = "张同学",
        date_value: str = "2026-11-20",
    ) -> dict:
        return self.service.create_reservation(
            {
                "equipment_id": equipment_id,
                "requester": requester,
                "date": date_value,
                "start_time": start_time,
                "end_time": end_time,
            }
        )

    def test_ac1_add_equipment(self) -> None:
        item = self.add_equipment()
        items = self.service.list_equipment()
        self.assertEqual(1, len(items))
        self.assertEqual("LAB-001", item["code"])
        self.assertEqual("available", item["status"])
        self.assertEqual(item["id"], items[0]["id"])
        self.assertEqual(0, items[0]["active_reservations"])

    def test_ac2_duplicate_equipment_code_is_rejected(self) -> None:
        self.add_equipment("LAB-001")
        with self.assertRaises(AppError) as context:
            self.add_equipment("LAB-001")
        self.assertEqual(409, context.exception.status)
        self.assertEqual("equipment_code_exists", context.exception.code)

    def test_ac3_create_valid_reservation(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment["id"])
        items = self.service.list_reservations()
        self.assertEqual(1, len(items))
        self.assertEqual("booked", reservation["status"])
        self.assertEqual("张同学", items[0]["requester"])
        self.assertEqual("LAB-001", items[0]["equipment_code"])

    def test_ac4_overlapping_reservation_is_rejected(self) -> None:
        equipment = self.add_equipment()
        self.add_reservation(equipment["id"], "09:00", "10:00")
        with self.assertRaises(AppError) as context:
            self.add_reservation(
                equipment["id"],
                "09:30",
                "10:30",
                requester="李同学",
            )
        self.assertEqual(409, context.exception.status)
        self.assertEqual("reservation_conflict", context.exception.code)
        self.assertIn("预约时间冲突", context.exception.message)

    def test_ac5_adjacent_reservations_are_allowed(self) -> None:
        equipment = self.add_equipment()
        first = self.add_reservation(equipment["id"], "09:00", "10:00")
        second = self.add_reservation(
            equipment["id"],
            "10:00",
            "11:00",
            requester="李同学",
        )
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(2, len(self.service.list_reservations()))

    def test_ac6_invalid_time_range_is_rejected(self) -> None:
        equipment = self.add_equipment()
        for start, end in [("10:00", "10:00"), ("11:00", "10:00")]:
            with self.subTest(start=start, end=end):
                with self.assertRaises(AppError) as context:
                    self.add_reservation(equipment["id"], start, end)
                self.assertIn("开始时间必须早于结束时间", context.exception.message)

    def test_ac7_cancelled_reservation_frees_the_time(self) -> None:
        equipment = self.add_equipment()
        original = self.add_reservation(equipment["id"], "09:00", "10:00")
        cancelled = self.service.update_reservation_status(original["id"], "cancelled")
        self.assertEqual("cancelled", cancelled["status"])
        replacement = self.add_reservation(
            equipment["id"],
            "09:00",
            "10:00",
            requester="王同学",
        )
        self.assertEqual("booked", replacement["status"])

    def test_ac8_combined_filters(self) -> None:
        equipment_a = self.add_equipment("LAB-A")
        equipment_b = self.add_equipment("LAB-B")
        target = self.add_reservation(
            equipment_a["id"],
            "09:00",
            "10:00",
            requester="目标预约",
            date_value="2026-11-20",
        )
        self.service.update_reservation_status(target["id"], "cancelled")
        self.add_reservation(
            equipment_a["id"],
            "11:00",
            "12:00",
            requester="同日其他预约",
            date_value="2026-11-20",
        )
        self.add_reservation(
            equipment_b["id"],
            "09:00",
            "10:00",
            requester="其他设备",
            date_value="2026-11-20",
        )
        filtered = self.service.list_reservations(
            equipment_id=equipment_a["id"],
            reservation_date="2026-11-20",
            status_value="cancelled",
        )
        self.assertEqual(1, len(filtered))
        self.assertEqual(target["id"], filtered[0]["id"])

    def test_ac9_delete_is_blocked_until_reservation_is_inactive(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment["id"])
        with self.assertRaises(AppError) as context:
            self.service.delete_equipment(equipment["id"])
        self.assertEqual("equipment_in_use", context.exception.code)
        self.service.update_reservation_status(reservation["id"], "cancelled")
        self.service.delete_equipment(equipment["id"])
        self.assertEqual([], self.service.list_equipment())

    def test_ac10_data_survives_service_restart(self) -> None:
        equipment = self.add_equipment()
        self.add_reservation(equipment["id"])
        restarted = BookingService(self.db_path)
        self.assertEqual(1, len(restarted.list_equipment()))
        self.assertEqual(1, len(restarted.list_reservations()))

    def test_ac11_statistics_are_correct(self) -> None:
        equipment_a = self.add_equipment("LAB-A")
        equipment_b = self.add_equipment("LAB-B")
        equipment_c = self.add_equipment("LAB-C")
        booked = self.add_reservation(equipment_a["id"], "09:00", "10:00")
        in_use = self.add_reservation(equipment_b["id"], "10:00", "11:00")
        cancelled = self.add_reservation(equipment_c["id"], "11:00", "12:00")
        completed = self.add_reservation(equipment_c["id"], "13:00", "14:00")
        self.service.update_reservation_status(in_use["id"], "in_use")
        self.service.update_reservation_status(cancelled["id"], "cancelled")
        self.service.update_reservation_status(completed["id"], "in_use")
        self.service.update_reservation_status(completed["id"], "completed")
        stats = self.service.stats()
        self.assertEqual(3, stats["equipment_count"])
        self.assertEqual(2, stats["active_count"])
        self.assertEqual(1, stats["cancelled_count"])
        self.assertEqual(1, stats["completed_count"])
        self.assertEqual(
            3,
            sum(row["reservation_count"] for row in stats["by_equipment"]),
        )
        self.assertEqual(
            1,
            next(
                row["reservation_count"]
                for row in stats["by_equipment"]
                if row["id"] == equipment_c["id"]
            ),
        )
        self.assertEqual("booked", booked["status"])

    def test_ac12_unavailable_equipment_cannot_be_booked(self) -> None:
        for status in ("maintenance", "retired"):
            with self.subTest(status=status):
                equipment = self.add_equipment(f"LAB-{status}", status=status)
                with self.assertRaises(AppError) as context:
                    self.add_reservation(equipment["id"])
                self.assertEqual("equipment_unavailable", context.exception.code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
