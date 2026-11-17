"""业务服务层单元测试。"""

from __future__ import annotations

import unittest

from app.errors import ConflictError, ValidationError
from app.models import EquipmentStatus, ReservationStatus
from app.service import ReservationFilter
from tests.base import ServiceTestCase


class EquipmentServiceTests(ServiceTestCase):
    def test_add_equipment(self) -> None:
        equipment = self.add_equipment()
        self.assertIn(equipment.id, [item.id for item in self.service.list_equipment()])
        self.assertEqual(equipment.status, EquipmentStatus.AVAILABLE)

    def test_duplicate_code_rejected(self) -> None:
        self.add_equipment(code="EQ-001")
        with self.assertRaises(ValidationError) as context:
            self.add_equipment(code="EQ-001", name="另一台设备")
        self.assertIn("已存在", context.exception.message)

    def test_duplicate_code_case_insensitive(self) -> None:
        self.add_equipment(code="EQ-001")
        with self.assertRaises(ValidationError):
            self.add_equipment(code="eq-001", name="另一台设备")

    def test_missing_required_fields(self) -> None:
        for payload in (
            {"code": "", "name": "n", "location": "l"},
            {"code": "c", "name": " ", "location": "l"},
            {"code": "c", "name": "n", "location": ""},
        ):
            with self.assertRaises(ValidationError):
                self.service.add_equipment(
                    opening_start="08:00", opening_end="09:00", **payload
                )

    def test_update_equipment(self) -> None:
        equipment = self.add_equipment()
        updated = self.service.update_equipment(
            equipment.id,
            code="EQ-002",
            name="新名称",
            location="新位置",
            status="maintenance",
            opening_start="09:00",
            opening_end="18:00",
            notes="改过了",
        )
        self.assertEqual(updated.code, "EQ-002")
        self.assertEqual(updated.status, EquipmentStatus.MAINTENANCE)
        self.assertEqual(updated.opening_start, "09:00")
        self.assertEqual(updated.notes, "改过了")

    def test_update_to_duplicate_code_rejected(self) -> None:
        first = self.add_equipment(code="EQ-001")
        second = self.add_equipment(code="EQ-002", name="设备2")
        with self.assertRaises(ValidationError):
            self.service.update_equipment(
                second.id,
                code="EQ-001",
                name="设备2",
                location="l",
                status="available",
                opening_start="08:00",
                opening_end="09:00",
            )
        self.assertEqual(self.service.get_equipment(first.id).code, "EQ-001")

    def test_update_self_with_same_code_allowed(self) -> None:
        equipment = self.add_equipment(code="EQ-001")
        updated = self.service.update_equipment(
            equipment.id,
            code="EQ-001",
            name="改名",
            location="l",
            status="available",
            opening_start="08:00",
            opening_end="09:00",
        )
        self.assertEqual(updated.name, "改名")

    def test_update_unknown_equipment(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.update_equipment(
                "not-exist",
                code="c",
                name="n",
                location="l",
                status="available",
                opening_start="08:00",
                opening_end="09:00",
            )

    def test_delete_equipment(self) -> None:
        equipment = self.add_equipment()
        self.service.delete_equipment(equipment.id)
        self.assertEqual(self.service.list_equipment(), [])

    def test_delete_blocked_by_active_reservation(self) -> None:
        equipment = self.add_equipment()
        self.add_reservation(equipment)
        with self.assertRaises(ValidationError) as context:
            self.service.delete_equipment(equipment.id)
        self.assertIn("有效预约", context.exception.message)

    def test_delete_allowed_after_cancel(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment)
        self.service.cancel_reservation(reservation.id)
        self.service.delete_equipment(equipment.id)
        self.assertEqual(self.service.list_equipment(), [])

    def test_delete_keeps_history_when_requested(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment)
        self.service.cancel_reservation(reservation.id)
        self.service.delete_equipment(equipment.id, keep_history=True)
        self.assertEqual(len(self.service.list_reservations()), 1)

    def test_delete_removes_history_when_not_requested(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment)
        self.service.cancel_reservation(reservation.id)
        self.service.delete_equipment(equipment.id, keep_history=False)
        self.assertEqual(self.service.list_reservations(), [])

    def test_bookable_equipment_filters_status(self) -> None:
        self.add_equipment(code="EQ-001")
        self.add_equipment(code="EQ-002", status="maintenance")
        self.add_equipment(code="EQ-003", status="retired")
        self.assertEqual([item.code for item in self.service.bookable_equipment()], ["EQ-001"])


class ReservationServiceTests(ServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.equipment = self.add_equipment()

    def test_create_reservation(self) -> None:
        reservation = self.add_reservation(self.equipment)
        self.assertEqual(reservation.status, ReservationStatus.BOOKED)
        self.assertEqual(len(self.service.list_reservations()), 1)

    def test_requester_required(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.add_reservation(self.equipment, requester="  ")
        self.assertIn("预约人", context.exception.message)

    def test_invalid_date_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.add_reservation(self.equipment, date="2026-02-30")

    def test_end_before_start_rejected(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.add_reservation(self.equipment, start="11:00", end="09:00")
        self.assertIn("早于", context.exception.message)

    def test_equal_start_end_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.add_reservation(self.equipment, start="09:00", end="09:00")

    def test_outside_opening_hours_rejected(self) -> None:
        with self.assertRaises(ValidationError) as context:
            self.add_reservation(self.equipment, start="07:00", end="08:30")
        self.assertIn("可预约时段", context.exception.message)

    def test_after_opening_hours_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.add_reservation(self.equipment, start="19:30", end="21:00")

    def test_conflict_rejected(self) -> None:
        self.add_reservation(self.equipment, start="09:00", end="10:00")
        with self.assertRaises(ConflictError) as context:
            self.add_reservation(self.equipment, requester="李四", start="09:30", end="10:30")
        self.assertIn("冲突", context.exception.message)
        self.assertEqual(len(self.service.list_reservations()), 1)

    def test_touching_reservations_allowed(self) -> None:
        self.add_reservation(self.equipment, start="09:00", end="10:00")
        self.add_reservation(self.equipment, requester="李四", start="10:00", end="11:00")
        self.assertEqual(len(self.service.list_reservations()), 2)

    def test_same_time_other_equipment_allowed(self) -> None:
        other = self.add_equipment(code="EQ-002", name="设备2")
        self.add_reservation(self.equipment, start="09:00", end="10:00")
        self.add_reservation(other, requester="李四", start="09:00", end="10:00")
        self.assertEqual(len(self.service.list_reservations()), 2)

    def test_same_time_other_date_allowed(self) -> None:
        self.add_reservation(self.equipment, date="2026-11-17", start="09:00", end="10:00")
        self.add_reservation(self.equipment, requester="李四", date="2026-11-18", start="09:00", end="10:00")
        self.assertEqual(len(self.service.list_reservations()), 2)

    def test_maintenance_equipment_rejects_new_reservation(self) -> None:
        equipment = self.add_equipment(code="EQ-009", status="maintenance")
        with self.assertRaises(ValidationError) as context:
            self.add_reservation(equipment)
        self.assertIn("维护中", context.exception.message)

    def test_retired_equipment_rejects_new_reservation(self) -> None:
        equipment = self.add_equipment(code="EQ-010", status="retired")
        with self.assertRaises(ValidationError):
            self.add_reservation(equipment)


class StatusTransitionTests(ServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.equipment = self.add_equipment()
        self.reservation = self.add_reservation(self.equipment)

    def test_booked_to_in_use(self) -> None:
        updated = self.service.start_use(self.reservation.id)
        self.assertEqual(updated.status, ReservationStatus.IN_USE)

    def test_booked_to_cancelled(self) -> None:
        updated = self.service.cancel_reservation(self.reservation.id)
        self.assertEqual(updated.status, ReservationStatus.CANCELLED)

    def test_in_use_to_completed(self) -> None:
        self.service.start_use(self.reservation.id)
        updated = self.service.complete_reservation(self.reservation.id)
        self.assertEqual(updated.status, ReservationStatus.COMPLETED)

    def test_completed_to_cancelled_forbidden(self) -> None:
        self.service.start_use(self.reservation.id)
        self.service.complete_reservation(self.reservation.id)
        with self.assertRaises(ValidationError) as context:
            self.service.cancel_reservation(self.reservation.id)
        self.assertIn("不允许", context.exception.message)

    def test_cancelled_to_booked_forbidden(self) -> None:
        self.service.cancel_reservation(self.reservation.id)
        with self.assertRaises(ValidationError):
            self.service.transition(self.reservation.id, ReservationStatus.BOOKED)

    def test_completed_to_in_use_forbidden(self) -> None:
        self.service.start_use(self.reservation.id)
        self.service.complete_reservation(self.reservation.id)
        with self.assertRaises(ValidationError):
            self.service.start_use(self.reservation.id)

    def test_cancelled_reservation_frees_the_slot(self) -> None:
        self.service.cancel_reservation(self.reservation.id)
        again = self.add_reservation(self.equipment, requester="李四", start="09:00", end="10:00")
        self.assertEqual(again.status, ReservationStatus.BOOKED)

    def test_completed_reservation_frees_the_slot(self) -> None:
        self.service.start_use(self.reservation.id)
        self.service.complete_reservation(self.reservation.id)
        again = self.add_reservation(self.equipment, requester="李四", start="09:00", end="10:00")
        self.assertEqual(again.status, ReservationStatus.BOOKED)


class FilterTests(ServiceTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.eq1 = self.add_equipment(code="EQ-001")
        self.eq2 = self.add_equipment(code="EQ-002", name="设备2")
        self.r1 = self.add_reservation(self.eq1, requester="张三", date="2026-11-17", start="09:00", end="10:00")
        self.r2 = self.add_reservation(self.eq1, requester="李四", date="2026-11-18", start="09:00", end="10:00")
        self.r3 = self.add_reservation(self.eq2, requester="王五", date="2026-11-17", start="14:00", end="15:00")
        self.service.cancel_reservation(self.r3.id)

    def test_filter_by_equipment(self) -> None:
        result = self.service.list_reservations(ReservationFilter(equipment_id=self.eq1.id))
        self.assertEqual({item.id for item in result}, {self.r1.id, self.r2.id})

    def test_filter_by_date(self) -> None:
        result = self.service.list_reservations(ReservationFilter(date="2026-11-17"))
        self.assertEqual({item.id for item in result}, {self.r1.id, self.r3.id})

    def test_filter_by_status(self) -> None:
        result = self.service.list_reservations(ReservationFilter(status="cancelled"))
        self.assertEqual([item.id for item in result], [self.r3.id])

    def test_combined_filters(self) -> None:
        result = self.service.list_reservations(
            ReservationFilter(equipment_id=self.eq1.id, date="2026-11-17", status="booked")
        )
        self.assertEqual([item.id for item in result], [self.r1.id])

    def test_no_filter_returns_all(self) -> None:
        self.assertEqual(len(self.service.list_reservations()), 3)


class StatisticsTests(ServiceTestCase):
    def test_counts(self) -> None:
        eq1 = self.add_equipment(code="EQ-001")
        eq2 = self.add_equipment(code="EQ-002", name="设备2")
        eq3 = self.add_equipment(code="EQ-003", name="设备3")
        first = self.add_reservation(eq1, date="2026-11-17", start="09:00", end="10:00")
        self.add_reservation(eq1, requester="李四", date="2026-11-17", start="10:00", end="11:30")
        cancelled = self.add_reservation(eq2, date="2026-11-17", start="09:00", end="10:00")
        self.service.cancel_reservation(cancelled.id)
        self.add_reservation(eq3, date="2026-11-17", start="09:00", end="10:00")

        stats = self.service.statistics()
        self.assertEqual(stats.equipment_total, 3)
        self.assertEqual(stats.active_total, 3)
        self.assertEqual(stats.cancelled_total, 1)
        self.assertEqual(stats.completed_total, 0)
        # 已取消的 60 分钟不计入使用时长
        self.assertEqual(stats.total_minutes, 60 + 90 + 60)
        self.assertEqual(len(stats.per_equipment), 3)
        self.assertEqual(len(stats.per_status), 4)

    def test_per_equipment_usage(self) -> None:
        equipment = self.add_equipment()
        self.add_reservation(equipment, start="09:00", end="10:00")
        self.add_reservation(equipment, requester="李四", start="11:00", end="12:30")
        stats = self.service.statistics()
        self.assertEqual(stats.per_equipment[0].reservation_count, 2)
        self.assertEqual(stats.per_equipment[0].usage_minutes, 150)


if __name__ == "__main__":
    unittest.main()
