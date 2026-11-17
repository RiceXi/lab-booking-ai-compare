"""验收用例自动化测试。

本文件与 ``docs/acceptance.md`` 的 AC1~AC12 一一对应，
用于给出可重复执行的功能验证证据；界面交互部分另见人工验收记录。
"""

from __future__ import annotations

import unittest

from app.errors import ConflictError, ValidationError
from app.models import EquipmentStatus, ReservationStatus
from app.service import ReservationFilter
from app.store import JsonStore
from tests.base import ServiceTestCase


class AC1AddEquipmentTests(ServiceTestCase):
    """AC1 添加设备：唯一编号、名称、位置和可用时间保存后出现在列表中。"""

    def test_ac1_equipment_appears_in_list(self) -> None:
        equipment = self.add_equipment(code="EQ-001", name="高速离心机", location="生化楼 A-201")
        listed = self.service.list_equipment()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].id, equipment.id)
        self.assertEqual(listed[0].code, "EQ-001")
        self.assertEqual(listed[0].name, "高速离心机")
        self.assertEqual(listed[0].location, "生化楼 A-201")
        self.assertEqual(listed[0].opening_start, "08:00")
        self.assertEqual(listed[0].opening_end, "20:00")


class AC2DuplicateCodeTests(ServiceTestCase):
    """AC2 重复设备编号：必须阻止保存并显示提示。"""

    def test_ac2_duplicate_code_is_blocked_with_message(self) -> None:
        self.add_equipment(code="EQ-001")
        with self.assertRaises(ValidationError) as context:
            self.add_equipment(code="EQ-001", name="重复设备")
        self.assertIn("EQ-001", context.exception.message)
        self.assertIn("已存在", context.exception.message)
        self.assertEqual(len(self.service.list_equipment()), 1)


class AC3CreateReservationTests(ServiceTestCase):
    """AC3 创建有效预约：保存后预约出现在列表中。"""

    def test_ac3_valid_reservation_appears_in_list(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment, requester="张三", date="2026-11-17")
        listed = self.service.list_reservations()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].id, reservation.id)
        self.assertEqual(listed[0].requester, "张三")
        self.assertEqual(listed[0].date, "2026-11-17")
        self.assertEqual(listed[0].start_time, "09:00")
        self.assertEqual(listed[0].end_time, "10:00")
        self.assertEqual(listed[0].status, ReservationStatus.BOOKED)


class AC4ConflictTests(ServiceTestCase):
    """AC4 冲突预约：阻止保存并说明冲突。"""

    def test_ac4_overlapping_reservation_is_blocked(self) -> None:
        equipment = self.add_equipment()
        self.add_reservation(equipment, requester="张三", start="09:00", end="10:00")
        with self.assertRaises(ConflictError) as context:
            self.add_reservation(equipment, requester="李四", start="09:30", end="10:30")
        message = context.exception.message
        self.assertIn("冲突", message)
        self.assertIn("09:00-10:00", message)
        self.assertEqual(len(self.service.list_reservations()), 1)


class AC5TouchingTests(ServiceTestCase):
    """AC5 首尾相接：09:00-10:00 与 10:00-11:00 都可以保存。"""

    def test_ac5_touching_reservations_are_allowed(self) -> None:
        equipment = self.add_equipment()
        first = self.add_reservation(equipment, requester="张三", start="09:00", end="10:00")
        second = self.add_reservation(equipment, requester="李四", start="10:00", end="11:00")
        self.assertEqual(len(self.service.list_reservations()), 2)
        self.assertNotEqual(first.id, second.id)


class AC6InvalidTimeTests(ServiceTestCase):
    """AC6 非法时间：结束时间早于或等于开始时间时必须阻止保存。"""

    def test_ac6_end_before_start_is_blocked(self) -> None:
        equipment = self.add_equipment()
        with self.assertRaises(ValidationError):
            self.add_reservation(equipment, start="11:00", end="09:00")
        self.assertEqual(len(self.service.list_reservations()), 0)

    def test_ac6_end_equal_start_is_blocked(self) -> None:
        equipment = self.add_equipment()
        with self.assertRaises(ValidationError):
            self.add_reservation(equipment, start="09:00", end="09:00")
        self.assertEqual(len(self.service.list_reservations()), 0)


class AC7CancelTests(ServiceTestCase):
    """AC7 取消预约：状态变为 cancelled，且不再阻止同时间段的新预约。"""

    def test_ac7_cancel_changes_status_and_frees_slot(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment, start="09:00", end="10:00")
        cancelled = self.service.cancel_reservation(reservation.id)
        self.assertEqual(cancelled.status, ReservationStatus.CANCELLED)

        again = self.add_reservation(equipment, requester="李四", start="09:00", end="10:00")
        self.assertEqual(again.status, ReservationStatus.BOOKED)
        self.assertEqual(len(self.service.list_reservations()), 2)


class AC8FilterTests(ServiceTestCase):
    """AC8 筛选：按设备、日期、状态筛选，且支持组合。"""

    def setUp(self) -> None:
        super().setUp()
        self.eq1 = self.add_equipment(code="EQ-001")
        self.eq2 = self.add_equipment(code="EQ-002", name="设备2")
        self.r1 = self.add_reservation(self.eq1, requester="张三", date="2026-11-17", start="09:00", end="10:00")
        self.r2 = self.add_reservation(self.eq1, requester="李四", date="2026-11-18", start="09:00", end="10:00")
        self.r3 = self.add_reservation(self.eq2, requester="王五", date="2026-11-17", start="14:00", end="15:00")
        self.service.cancel_reservation(self.r3.id)

    def test_ac8_filter_by_equipment(self) -> None:
        result = self.service.list_reservations(ReservationFilter(equipment_id=self.eq1.id))
        self.assertEqual({item.id for item in result}, {self.r1.id, self.r2.id})

    def test_ac8_filter_by_date(self) -> None:
        result = self.service.list_reservations(ReservationFilter(date="2026-11-18"))
        self.assertEqual([item.id for item in result], [self.r2.id])

    def test_ac8_filter_by_status(self) -> None:
        result = self.service.list_reservations(ReservationFilter(status="cancelled"))
        self.assertEqual([item.id for item in result], [self.r3.id])

    def test_ac8_combined_filter(self) -> None:
        result = self.service.list_reservations(
            ReservationFilter(equipment_id=self.eq2.id, date="2026-11-17", status="cancelled")
        )
        self.assertEqual([item.id for item in result], [self.r3.id])

    def test_ac8_filter_result_matches_conditions(self) -> None:
        result = self.service.list_reservations(ReservationFilter(date="2026-11-17"))
        for item in result:
            self.assertEqual(item.date, "2026-11-17")


class AC9DeleteEquipmentTests(ServiceTestCase):
    """AC9 删除设备：存在有效预约时阻止；取消或完成后允许删除。"""

    def test_ac9_delete_blocked_while_active_reservation_exists(self) -> None:
        equipment = self.add_equipment()
        self.add_reservation(equipment)
        with self.assertRaises(ValidationError) as context:
            self.service.delete_equipment(equipment.id)
        self.assertIn("有效预约", context.exception.message)
        self.assertEqual(len(self.service.list_equipment()), 1)

    def test_ac9_delete_allowed_after_cancel(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment)
        self.service.cancel_reservation(reservation.id)
        self.service.delete_equipment(equipment.id)
        self.assertEqual(len(self.service.list_equipment()), 0)

    def test_ac9_delete_allowed_after_complete(self) -> None:
        equipment = self.add_equipment()
        reservation = self.add_reservation(equipment)
        self.service.start_use(reservation.id)
        self.service.complete_reservation(reservation.id)
        self.service.delete_equipment(equipment.id)
        self.assertEqual(len(self.service.list_equipment()), 0)


class AC10PersistenceTests(ServiceTestCase):
    """AC10 持久化：关闭程序后再次启动，数据仍然存在。"""

    def test_ac10_data_survives_restart(self) -> None:
        equipment = self.add_equipment(code="EQ-001", name="高速离心机", location="生化楼 A-201")
        reservation = self.add_reservation(equipment, requester="张三", date="2026-11-17")

        # 模拟关闭并重新启动程序：新建服务实例从同一个数据文件加载
        restarted = type(self.service)(JsonStore(self.data_file))
        self.assertEqual(len(restarted.list_equipment()), 1)
        self.assertEqual(len(restarted.list_reservations()), 1)
        self.assertEqual(restarted.list_equipment()[0].name, "高速离心机")
        self.assertEqual(restarted.list_reservations()[0].requester, "张三")
        self.assertEqual(restarted.list_reservations()[0].id, reservation.id)
        self.assertEqual(restarted.get_equipment(equipment.id).code, "EQ-001")

    def test_ac10_data_file_exists_on_disk(self) -> None:
        self.add_equipment()
        self.assertTrue(self.data_file.exists())
        self.assertIn("EQ-001", self.data_file.read_text(encoding="utf-8"))


class AC11StatisticsTests(ServiceTestCase):
    """AC11 统计：设备数、有效预约数和取消数必须正确。"""

    def test_ac11_statistics_are_correct(self) -> None:
        eq1 = self.add_equipment(code="EQ-001")
        eq2 = self.add_equipment(code="EQ-002", name="设备2")
        eq3 = self.add_equipment(code="EQ-003", name="设备3")
        self.add_reservation(eq1, date="2026-11-17", start="09:00", end="10:00")
        self.add_reservation(eq1, requester="李四", date="2026-11-18", start="09:00", end="10:00")
        cancelled = self.add_reservation(eq2, date="2026-11-17", start="14:00", end="15:00")
        self.service.cancel_reservation(cancelled.id)
        self.add_reservation(eq3, date="2026-11-17", start="09:00", end="10:00")

        stats = self.service.statistics()
        self.assertEqual(stats.equipment_total, 3)
        self.assertEqual(stats.active_total, 3)
        self.assertEqual(stats.cancelled_total, 1)
        self.assertEqual(len(stats.per_equipment), 3)
        self.assertEqual(sum(value for _label, value in stats.per_status), 4)

    def test_ac11_per_equipment_breakdown(self) -> None:
        eq1 = self.add_equipment(code="EQ-001")
        eq2 = self.add_equipment(code="EQ-002", name="设备2")
        self.add_reservation(eq1, start="09:00", end="10:00")
        self.add_reservation(eq1, requester="李四", start="10:00", end="11:00")
        self.add_reservation(eq2, requester="王五", start="09:00", end="10:00")
        stats = self.service.statistics()
        mapping = {item.code: item for item in stats.per_equipment}
        self.assertEqual(mapping["EQ-001"].reservation_count, 2)
        self.assertEqual(mapping["EQ-002"].reservation_count, 1)


class AC12UnavailableEquipmentTests(ServiceTestCase):
    """AC12 设备不可用：维护中或已停用的设备不能创建新预约。"""

    def test_ac12_maintenance_equipment_cannot_be_booked(self) -> None:
        equipment = self.add_equipment(code="EQ-001", status="maintenance")
        with self.assertRaises(ValidationError) as context:
            self.add_reservation(equipment)
        self.assertIn("维护中", context.exception.message)
        self.assertEqual(len(self.service.list_reservations()), 0)

    def test_ac12_retired_equipment_cannot_be_booked(self) -> None:
        equipment = self.add_equipment(code="EQ-001", status="retired")
        with self.assertRaises(ValidationError) as context:
            self.add_reservation(equipment)
        self.assertIn("已停用", context.exception.message)
        self.assertEqual(len(self.service.list_reservations()), 0)

    def test_ac12_available_equipment_can_be_booked(self) -> None:
        equipment = self.add_equipment(code="EQ-001", status="available")
        self.assertEqual(equipment.status, EquipmentStatus.AVAILABLE)
        self.add_reservation(equipment)
        self.assertEqual(len(self.service.list_reservations()), 1)


if __name__ == "__main__":
    unittest.main()
