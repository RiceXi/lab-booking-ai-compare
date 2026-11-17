"""统计与可视化页签（FR6）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..service import LabService
from .widgets import BarChart, MetricCard, format_minutes


class StatsTab(ttk.Frame):
    """指标卡片 + 两张柱状图 + 明细表。"""

    def __init__(self, master, service: LabService, **kwargs) -> None:
        super().__init__(master, padding=10, **kwargs)
        self.service = service

        self.metric_mode = tk.StringVar(value="count")

        self._build_cards()
        self._build_charts()
        self._build_table()
        self.refresh()
        self.service.add_listener(self.refresh)

    # ------------------------------------------------------------- 构建界面
    def _build_cards(self) -> None:
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 10))
        self.cards = {
            "equipment": MetricCard(row, "设备总数", "0"),
            "active": MetricCard(row, "有效预约数", "0"),
            "cancelled": MetricCard(row, "已取消预约数", "0"),
            "completed": MetricCard(row, "已完成预约数", "0"),
            "duration": MetricCard(row, "累计使用时长", "0 分钟"),
        }
        for card in self.cards.values():
            card.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.cards["duration"].pack_configure(padx=(0, 0))

    def _build_charts(self) -> None:
        row = ttk.Frame(self)
        row.pack(fill="both", expand=True, pady=(0, 10))

        left = ttk.LabelFrame(row, text="按设备统计")
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.mode_bar = ttk.Frame(left)
        self.mode_bar.pack(fill="x", padx=8, pady=(6, 0))
        ttk.Radiobutton(
            self.mode_bar,
            text="按预约次数",
            variable=self.metric_mode,
            value="count",
            command=self.refresh,
        ).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(
            self.mode_bar,
            text="按使用时长",
            variable=self.metric_mode,
            value="duration",
            command=self.refresh,
        ).pack(side="left")
        self.equipment_chart = BarChart(left, title="各设备预约统计", unit=" 次")
        self.equipment_chart.pack(fill="both", expand=True, padx=8, pady=8)

        right = ttk.LabelFrame(row, text="预约状态分布")
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.status_chart = BarChart(right, title="预约状态占比", unit=" 条")
        self.status_chart.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_table(self) -> None:
        table_frame = ttk.LabelFrame(self, text="设备明细统计")
        table_frame.pack(fill="both", expand=True)

        columns = ("code", "name", "count", "duration")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        for key, text, width in (
            ("code", "设备编号", 140),
            ("name", "设备名称", 220),
            ("count", "预约次数", 100),
            ("duration", "累计使用时长", 160),
        ):
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # ------------------------------------------------------------- 数据刷新
    def refresh(self) -> None:
        if not hasattr(self, "tree"):
            return
        stats = self.service.statistics()

        self.cards["equipment"].set_value(str(stats.equipment_total))
        self.cards["active"].set_value(str(stats.active_total))
        self.cards["cancelled"].set_value(str(stats.cancelled_total))
        self.cards["completed"].set_value(str(stats.completed_total))
        self.cards["duration"].set_value(format_minutes(stats.total_minutes))

        if self.metric_mode.get() == "duration":
            items = [
                (item.code, float(item.usage_minutes))
                for item in stats.per_equipment
            ]
            self.equipment_chart.set_data(items, title="各设备使用时长统计", unit=" 分钟")
        else:
            items = [
                (item.code, float(item.reservation_count))
                for item in stats.per_equipment
            ]
            self.equipment_chart.set_data(items, title="各设备预约统计", unit=" 次")

        self.status_chart.set_data(
            [(label, float(value)) for label, value in stats.per_status],
            title="预约状态占比",
            unit=" 条",
        )

        self.tree.delete(*self.tree.get_children())
        for item in stats.per_equipment:
            self.tree.insert(
                "",
                "end",
                values=(
                    item.code,
                    item.name,
                    item.reservation_count,
                    format_minutes(item.usage_minutes),
                ),
            )
