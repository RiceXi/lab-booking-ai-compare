"""JSON 持久化单元测试。"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.errors import DataFileError
from app.models import Equipment, EquipmentStatus, Reservation, ReservationStatus
from app.store import JsonStore


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="lab-booking-store-"))
        self.path = self.temp_dir / "data.json"
        self.store = JsonStore(self.path)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _sample(self) -> tuple[Equipment, Reservation]:
        equipment = Equipment(
            id="e1",
            code="EQ-001",
            name="高速离心机",
            location="生化楼 A-201",
            status=EquipmentStatus.AVAILABLE,
            opening_start="08:00",
            opening_end="20:00",
            notes="测试设备",
        )
        reservation = Reservation(
            id="r1",
            equipment_id="e1",
            requester="张三",
            date="2026-11-17",
            start_time="09:00",
            end_time="10:00",
            status=ReservationStatus.BOOKED,
            notes="测试预约",
        )
        return equipment, reservation

    def test_missing_file_returns_empty(self) -> None:
        equipment, reservations = self.store.load()
        self.assertEqual(equipment, [])
        self.assertEqual(reservations, [])

    def test_roundtrip(self) -> None:
        equipment, reservation = self._sample()
        self.store.save([equipment], [reservation])
        loaded_equipment, loaded_reservations = self.store.load()
        self.assertEqual(len(loaded_equipment), 1)
        self.assertEqual(len(loaded_reservations), 1)
        self.assertEqual(loaded_equipment[0].code, "EQ-001")
        self.assertEqual(loaded_equipment[0].status, EquipmentStatus.AVAILABLE)
        self.assertEqual(loaded_equipment[0].notes, "测试设备")
        self.assertEqual(loaded_reservations[0].requester, "张三")
        self.assertEqual(loaded_reservations[0].status, ReservationStatus.BOOKED)

    def test_file_is_human_readable_utf8(self) -> None:
        equipment, reservation = self._sample()
        self.store.save([equipment], [reservation])
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("高速离心机", text)
        self.assertIn("张三", text)
        payload = json.loads(text)
        self.assertEqual(payload["equipment"][0]["code"], "EQ-001")
        self.assertEqual(payload["reservations"][0]["date"], "2026-11-17")

    def test_creates_parent_directory(self) -> None:
        nested = self.temp_dir / "sub" / "dir" / "data.json"
        store = JsonStore(nested)
        equipment, _ = self._sample()
        store.save([equipment], [])
        self.assertTrue(nested.exists())

    def test_no_temp_file_left_behind(self) -> None:
        equipment, reservation = self._sample()
        self.store.save([equipment], [reservation])
        leftovers = [item.name for item in self.path.parent.iterdir() if item.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    def test_corrupt_file_raises_friendly_error(self) -> None:
        self.path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(DataFileError) as context:
            self.store.load()
        self.assertIn("解析失败", context.exception.message)

    def test_unknown_status_falls_back(self) -> None:
        self.path.write_text(
            json.dumps(
                {
                    "equipment": [
                        {
                            "id": "e1",
                            "code": "EQ-001",
                            "name": "n",
                            "location": "l",
                            "status": "unknown-status",
                            "opening_start": "08:00",
                            "opening_end": "09:00",
                        }
                    ],
                    "reservations": [],
                }
            ),
            encoding="utf-8",
        )
        equipment, _ = self.store.load()
        self.assertEqual(equipment[0].status, EquipmentStatus.AVAILABLE)


if __name__ == "__main__":
    unittest.main()
