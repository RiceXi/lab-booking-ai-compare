"""界面流程测试。

这些用例通过真实的 Tk 控件与按钮回调走一遍完整路径：
填表单 → 触发按钮 → 业务校验 → 弹窗提示。
弹窗（messagebox）在本文件中被替换为"记录器"，因此测试可以无人值守运行，
同时仍然能断言提示文案是否正确传达给用户。
"""

from __future__ import annotations

import unittest

from app.ui import equipment_tab, reservation_tab
from app.ui.main_window import MainWindow
from tests.base import ServiceTestCase


class DialogRecorder:
    """替换 messagebox，记录弹窗类型与文案。"""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.answers: bool | None = None

    # 弹窗接口
    def showerror(self, title, message, **_kwargs):
        self.errors.append(str(message))

    def showinfo(self, title, message, **_kwargs):
        self.infos.append(str(message))

    def showwarning(self, title, message, **_kwargs):
        self.warnings.append(str(message))

    def askyesnocancel(self, title, message, **_kwargs):
        if self.answers is None:
            return True
        return self.answers


class UIFlowTestCase(ServiceTestCase):
    """在真实窗口上执行界面流程。"""

    def setUp(self) -> None:
        super().setUp()
        self.recorder = DialogRecorder()

        self._original_equipment_box = equipment_tab.messagebox
        self._original_reservation_box = reservation_tab.messagebox
        equipment_tab.messagebox = self.recorder
        reservation_tab.messagebox = self.recorder

        self.window = MainWindow(self.service)
        self.window.update_idletasks()
        self.equipment_tab = self.window.equipment_tab
        self.reservation_tab = self.window.reservation_tab
        self.stats_tab = self.window.stats_tab

    def tearDown(self) -> None:
        self.window.destroy()
        equipment_tab.messagebox = self._original_equipment_box
        reservation_tab.messagebox = self._original_reservation_box
        super().tearDown()

    # ------------------------------------------------------------ 辅助方法
    def tree_values(self, tree) -> list[tuple]:
        return [tuple(tree.item(item, "values")) for item in tree.get_children()]

    def select_first_equipment(self) -> None:
        items = self.equipment_tab.tree.get_children()
        self.equipment_tab.tree.selection_set(items[0])

    def select_first_reservation(self) -> None:
        items = self.reservation_tab.tree.get_children()
        self.reservation_tab.tree.selection_set(items[0])


class UIAcceptanceTests(UIFlowTestCase):
    """界面层的 AC1~AC12 验证。"""

    # -------------------------------------------------------------- 设备管理
    def test_ac1_add_equipment_through_form(self) -> None:
        self.equipment_tab.code_var.set("EQ-001")
        self.equipment_tab.name_var.set("高速离心机")
        self.equipment_tab.location_var.set("生化楼 A-201")
        self.equipment_tab.opening_start_var.set("08:00")
        self.equipment_tab.opening_end_var.set("20:00")
        self.equipment_tab.on_add()

        rows = self.tree_values(self.equipment_tab.tree)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "EQ-001")
        self.assertEqual(rows[0][1], "高速离心机")
        self.assertEqual(rows[0][4], "08:00-20:00")

    def test_ac2_duplicate_code_shows_message(self) -> None:
        self.equipment_tab.code_var.set("EQ-001")
        self.equipment_tab.name_var.set("设备一")
        self.equipment_tab.location_var.set("A")
        self.equipment_tab.on_add()

        self.equipment_tab.code_var.set("EQ-001")
        self.equipment_tab.name_var.set("设备一重复")
        self.equipment_tab.location_var.set("B")
        self.equipment_tab.on_add()

        self.assertTrue(self.recorder.errors)
        self.assertIn("已存在", self.recorder.errors[-1])
        self.assertEqual(len(self.tree_values(self.equipment_tab.tree)), 1)

    def test_ac9_delete_blocked_then_allowed(self) -> None:
        # 先建立设备
        self.equipment_tab.code_var.set("EQ-001")
        self.equipment_tab.name_var.set("设备一")
        self.equipment_tab.location_var.set("A")
        self.equipment_tab.on_add()
        self.select_first_equipment()

        # 建立一条有效预约
        self.reservation_tab.requester_var.set("张三")
        self.reservation_tab.date_var.set("2026-11-17")
        self.reservation_tab.start_time_var.set("09:00")
        self.reservation_tab.end_time_var.set("10:00")
        self.reservation_tab.on_create()

        # 删除应被阻止
        self.equipment_tab.on_delete()
        self.assertTrue(self.recorder.errors)
        self.assertIn("有效预约", self.recorder.errors[-1])
        self.assertEqual(len(self.tree_values(self.equipment_tab.tree)), 1)

        # 取消预约后可以删除
        self.select_first_reservation()
        self.reservation_tab.on_transition("cancel")
        self.equipment_tab.tree.selection_set(self.equipment_tab.tree.get_children()[0])
        self.equipment_tab.on_delete()
        self.assertEqual(len(self.tree_values(self.equipment_tab.tree)), 0)

    # -------------------------------------------------------------- 预约管理
    def _prepare_equipment(self, code="EQ-001", status="available"):
        equipment = self.add_equipment(code=code, status=status)
        self.window.update_idletasks()
        self.reservation_tab.refresh()
        return equipment

    def test_ac3_create_reservation_through_form(self) -> None:
        self._prepare_equipment()
        self.reservation_tab.requester_var.set("张三")
        self.reservation_tab.date_var.set("2026-11-17")
        self.reservation_tab.start_time_var.set("09:00")
        self.reservation_tab.end_time_var.set("10:00")
        self.reservation_tab.on_create()

        rows = self.tree_values(self.reservation_tab.tree)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2], "张三")
        self.assertEqual(rows[0][3], "2026-11-17")
        self.assertEqual(rows[0][6], "已预约")

    def test_ac4_conflict_shows_message(self) -> None:
        self._prepare_equipment()
        self.reservation_tab.requester_var.set("张三")
        self.reservation_tab.date_var.set("2026-11-17")
        self.reservation_tab.start_time_var.set("09:00")
        self.reservation_tab.end_time_var.set("10:00")
        self.reservation_tab.on_create()

        self.reservation_tab.requester_var.set("李四")
        self.reservation_tab.start_time_var.set("09:30")
        self.reservation_tab.end_time_var.set("10:30")
        self.reservation_tab.on_create()

        self.assertTrue(self.recorder.errors)
        self.assertIn("冲突", self.recorder.errors[-1])
        self.assertEqual(len(self.tree_values(self.reservation_tab.tree)), 1)

    def test_ac5_touching_reservations_allowed(self) -> None:
        self._prepare_equipment()
        self.reservation_tab.requester_var.set("张三")
        self.reservation_tab.date_var.set("2026-11-17")
        self.reservation_tab.start_time_var.set("09:00")
        self.reservation_tab.end_time_var.set("10:00")
        self.reservation_tab.on_create()

        self.reservation_tab.requester_var.set("李四")
        self.reservation_tab.start_time_var.set("10:00")
        self.reservation_tab.end_time_var.set("11:00")
        self.reservation_tab.on_create()

        self.assertEqual(self.recorder.errors, [])
        self.assertEqual(len(self.tree_values(self.reservation_tab.tree)), 2)

    def test_ac6_invalid_time_shows_message(self) -> None:
        self._prepare_equipment()
        self.reservation_tab.requester_var.set("张三")
        self.reservation_tab.date_var.set("2026-11-17")
        self.reservation_tab.start_time_var.set("11:00")
        self.reservation_tab.end_time_var.set("09:00")
        self.reservation_tab.on_create()

        self.assertTrue(self.recorder.errors)
        self.assertIn("早于", self.recorder.errors[-1])
        self.assertEqual(len(self.tree_values(self.reservation_tab.tree)), 0)

    def test_ac7_cancel_frees_slot(self) -> None:
        self._prepare_equipment()
        self.reservation_tab.requester_var.set("张三")
        self.reservation_tab.date_var.set("2026-11-17")
        self.reservation_tab.start_time_var.set("09:00")
        self.reservation_tab.end_time_var.set("10:00")
        self.reservation_tab.on_create()

        self.select_first_reservation()
        self.reservation_tab.on_transition("cancel")
        self.assertEqual(self.tree_values(self.reservation_tab.tree)[0][6], "已取消")

        # 同一时间段可以重新预约
        self.reservation_tab.requester_var.set("李四")
        self.reservation_tab.on_create()
        self.assertEqual(self.recorder.errors, [])
        rows = self.tree_values(self.reservation_tab.tree)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][6], "已预约")

    def test_ac8_filters(self) -> None:
        self._prepare_equipment(code="EQ-001")
        second = self.add_equipment(code="EQ-002", name="设备2")
        self.reservation_tab.refresh()

        self.reservation_tab.requester_var.set("张三")
        self.reservation_tab.date_var.set("2026-11-17")
        self.reservation_tab.start_time_var.set("09:00")
        self.reservation_tab.end_time_var.set("10:00")
        self.reservation_tab.on_create()

        # 切换到第二台设备
        index = [
            item
            for item in self.reservation_tab.equipment_combo["values"]
            if item.startswith("EQ-002")
        ]
        self.assertTrue(index)
        self.reservation_tab.equipment_combo.current(
            list(self.reservation_tab.equipment_combo["values"]).index(index[0])
        )
        self.reservation_tab.requester_var.set("李四")
        self.reservation_tab.date_var.set("2026-11-18")
        self.reservation_tab.start_time_var.set("09:00")
        self.reservation_tab.end_time_var.set("10:00")
        self.reservation_tab.on_create()

        self.assertEqual(len(self.tree_values(self.reservation_tab.tree)), 2)

        # 按设备筛选
        self.reservation_tab.filter_equipment_var.set("EQ-001 高速离心机")
        self.reservation_tab.on_filter()
        rows = self.tree_values(self.reservation_tab.tree)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "EQ-001")

        # 按日期筛选
        self.reservation_tab.on_reset_filter()
        self.reservation_tab.filter_date_var.set("2026-11-18")
        self.reservation_tab.on_filter()
        rows = self.tree_values(self.reservation_tab.tree)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][3], "2026-11-18")

        # 按状态筛选
        self.reservation_tab.on_reset_filter()
        self.reservation_tab.filter_status_var.set("已取消")
        self.reservation_tab.on_filter()
        self.assertEqual(len(self.tree_values(self.reservation_tab.tree)), 0)

    def test_ac12_unavailable_equipment_shows_message(self) -> None:
        self._prepare_equipment(code="EQ-003", status="maintenance")
        self.reservation_tab.requester_var.set("张三")
        self.reservation_tab.date_var.set("2026-11-17")
        self.reservation_tab.start_time_var.set("09:00")
        self.reservation_tab.end_time_var.set("10:00")
        self.reservation_tab.on_create()

        self.assertTrue(self.recorder.errors)
        self.assertIn("维护中", self.recorder.errors[-1])
        self.assertEqual(len(self.tree_values(self.reservation_tab.tree)), 0)

    # -------------------------------------------------------------- 统计页签
    def test_ac11_statistics_cards(self) -> None:
        for index in range(1, 4):
            self.add_equipment(code=f"EQ-{index:03d}")
        first = self.service.list_equipment()[0]
        self.add_reservation(first, date="2026-11-17", start="09:00", end="10:00")
        cancelled = self.add_reservation(
            self.service.list_equipment()[1], requester="李四", date="2026-11-17", start="09:00", end="10:00"
        )
        self.service.cancel_reservation(cancelled.id)
        self.window.update_idletasks()
        self.stats_tab.refresh()

        cards = self.stats_tab.cards
        self.assertEqual(cards["equipment"]._value_label.cget("text"), "3")
        self.assertEqual(cards["active"]._value_label.cget("text"), "1")
        self.assertEqual(cards["cancelled"]._value_label.cget("text"), "1")

    def test_ac10_statistics_survive_restart(self) -> None:
        self.add_equipment(code="EQ-001")
        first = self.service.list_equipment()[0]
        self.add_reservation(first, date="2026-11-17", start="09:00", end="10:00")

        self.service.reload()
        self.window.update_idletasks()
        self.stats_tab.refresh()
        self.assertEqual(self.stats_tab.cards["equipment"]._value_label.cget("text"), "1")
        self.assertEqual(self.stats_tab.cards["active"]._value_label.cget("text"), "1")
        self.assertEqual(len(self.tree_values(self.reservation_tab.tree)), 1)


if __name__ == "__main__":
    unittest.main()
