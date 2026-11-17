"""冲突检测单元测试。"""

from __future__ import annotations

import unittest

from app.conflict import find_conflicts, time_overlaps
from app.models import Reservation, ReservationStatus


def make_reservation(
    reservation_id: str = "r1",
    equipment_id: str = "e1",
    date: str = "2026-11-17",
    start: str = "09:00",
    end: str = "10:00",
    status: str = ReservationStatus.BOOKED.value,
) -> Reservation:
    return Reservation(
        id=reservation_id,
        equipment_id=equipment_id,
        requester="张三",
        date=date,
        start_time=start,
        end_time=end,
        status=ReservationStatus(status),
    )


class TimeOverlapsTests(unittest.TestCase):
    def test_identical_intervals_overlap(self) -> None:
        self.assertTrue(time_overlaps("09:00", "10:00", "09:00", "10:00"))

    def test_partial_overlap(self) -> None:
        self.assertTrue(time_overlaps("09:30", "10:30", "09:00", "10:00"))
        self.assertTrue(time_overlaps("09:00", "10:00", "09:30", "10:30"))

    def test_contained(self) -> None:
        self.assertTrue(time_overlaps("09:30", "09:45", "09:00", "10:00"))

    def test_touching_is_not_overlap(self) -> None:
        self.assertFalse(time_overlaps("10:00", "11:00", "09:00", "10:00"))
        self.assertFalse(time_overlaps("09:00", "10:00", "10:00", "11:00"))

    def test_disjoint(self) -> None:
        self.assertFalse(time_overlaps("11:00", "12:00", "09:00", "10:00"))


class FindConflictsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reservations = [
            make_reservation("r1", "e1", "2026-11-17", "09:00", "10:00"),
            make_reservation("r2", "e2", "2026-11-17", "09:00", "10:00"),
            make_reservation("r3", "e1", "2026-11-18", "09:00", "10:00"),
            make_reservation("r4", "e1", "2026-11-17", "14:00", "15:00"),
        ]

    def _find(self, **kwargs):
        params = {
            "equipment_id": "e1",
            "date": "2026-11-17",
            "start_time": "09:30",
            "end_time": "10:30",
            "reservations": self.reservations,
        }
        params.update(kwargs)
        return find_conflicts(**params)

    def test_same_equipment_and_date_overlap(self) -> None:
        conflicts = self._find()
        self.assertEqual([item.id for item in conflicts], ["r1"])

    def test_other_equipment_ignored(self) -> None:
        self.assertEqual(self._find(equipment_id="e3"), [])

    def test_other_date_ignored(self) -> None:
        self.assertEqual(self._find(date="2026-11-19"), [])

    def test_cancelled_not_blocking(self) -> None:
        self.reservations[0].status = ReservationStatus.CANCELLED
        self.assertEqual(self._find(), [])

    def test_completed_not_blocking(self) -> None:
        self.reservations[0].status = ReservationStatus.COMPLETED
        self.assertEqual(self._find(), [])

    def test_in_use_blocks(self) -> None:
        self.reservations[0].status = ReservationStatus.IN_USE
        self.assertEqual([item.id for item in self._find()], ["r1"])

    def test_exclude_id(self) -> None:
        self.assertEqual(self._find(exclude_id="r1"), [])

    def test_touching_allowed(self) -> None:
        self.assertEqual(self._find(start_time="10:00", end_time="11:00"), [])


if __name__ == "__main__":
    unittest.main()
