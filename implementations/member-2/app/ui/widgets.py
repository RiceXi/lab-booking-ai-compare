"""界面通用小组件。

只依赖标准库 tkinter，不引入任何第三方图形库，
保证在没有网络的环境下也能直接运行。
"""

from __future__ import annotations

import math
import tkinter as tk
from datetime import date
from tkinter import ttk

#: 预约时间粒度：30 分钟。
GRID_MINUTES = 30

#: 柱状图配色
BAR_COLORS = ("#3b7dd8", "#f2a33c", "#4caf7d", "#e2686d", "#8f7fd8", "#5aa9c9")


def time_options(start_minutes: int = 0, end_minutes: int = 24 * 60) -> list[str]:
    """生成 30 分钟粒度的时间选项，例如 ``['00:00', '00:30', ...]``。"""
    options: list[str] = []
    for minutes in range(start_minutes, end_minutes, GRID_MINUTES):
        options.append(f"{minutes // 60:02d}:{minutes % 60:02d}")
    return options


def today_iso() -> str:
    """今天的日期字符串（YYYY-MM-DD）。"""
    return date.today().isoformat()


def format_minutes(minutes: int) -> str:
    """把分钟数格式化成 ``2 小时 30 分钟`` 这样的可读文本。"""
    minutes = max(int(minutes), 0)
    hours, rest = divmod(minutes, 60)
    if hours and rest:
        return f"{hours} 小时 {rest} 分钟"
    if hours:
        return f"{hours} 小时"
    return f"{rest} 分钟"


def _nice_scale(max_value: float) -> tuple[float, float]:
    """计算坐标轴上限与刻度步长，保证刻度都是整数。

    例如最大值为 7 时返回 ``(8, 2)``，刻度为 0、2、4、6、8。
    """
    if max_value <= 0:
        return 1.0, 1.0
    axis_max = float(math.ceil(max_value))
    step = max(1.0, float(math.ceil(axis_max / 4)))
    axis_max = float(math.ceil(max_value / step) * step)
    return axis_max, step


class MetricCard(ttk.Frame):
    """统计页顶部的指标卡片。"""

    def __init__(self, master, caption: str, value: str = "0", **kwargs) -> None:
        super().__init__(master, padding=(14, 10), relief="raised", borderwidth=1, **kwargs)
        self.caption = caption
        self._value_label = tk.Label(
            self,
            text=value,
            font=("Microsoft YaHei UI", 20, "bold"),
            foreground="#1f4e79",
            background="#fdfdfd",
        )
        self._value_label.pack(anchor="center")
        self._caption_label = tk.Label(
            self,
            text=caption,
            font=("Microsoft YaHei UI", 9),
            foreground="#555555",
            background="#fdfdfd",
        )
        self._caption_label.pack(anchor="center")

    def set_value(self, value: str) -> None:
        self._value_label.configure(text=value)


class BarChart(ttk.Frame):
    """基于 Canvas 的简易柱状图，用于满足 FR6 的可视化要求。"""

    def __init__(
        self,
        master,
        title: str = "",
        unit: str = "",
        empty_text: str = "暂无数据",
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._title = title
        self._unit = unit
        self._empty_text = empty_text
        self._items: list[tuple[str, float]] = []

        self.canvas = tk.Canvas(
            self, background="#ffffff", highlightthickness=1, highlightbackground="#d5d5d5"
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())

    def set_data(
        self,
        items: list[tuple[str, float]],
        title: str | None = None,
        unit: str | None = None,
    ) -> None:
        """更新图表数据。``items`` 为 ``[(名称, 数值), ...]``。"""
        self._items = [(str(name), float(value)) for name, value in items]
        if title is not None:
            self._title = title
        if unit is not None:
            self._unit = unit
        self._draw()

    def _draw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        pad_left, pad_right, pad_top, pad_bottom = 56, 18, 46, 46
        plot_left = pad_left
        plot_right = max(width - pad_right, plot_left + 40)
        plot_top = pad_top
        plot_bottom = max(height - pad_bottom, plot_top + 40)

        if self._title:
            canvas.create_text(
                12, 16, text=self._title, anchor="w", fill="#1f4e79",
                font=("Microsoft YaHei UI", 10, "bold"),
            )
        if self._unit:
            canvas.create_text(
                plot_right, 16, text=f"单位：{self._unit.lstrip()}", anchor="e", fill="#666666",
                font=("Microsoft YaHei UI", 8),
            )

        if not self._items:
            canvas.create_text(
                width / 2, height / 2, text=self._empty_text, fill="#888888",
                font=("Microsoft YaHei UI", 10),
            )
            return

        axis_max, step = _nice_scale(max(value for _, value in self._items))

        # 网格线与刻度（保证刻度都是整数，避免出现 0.5 这种读数）
        tick = 0
        while tick <= axis_max + 1e-9:
            ratio = tick / axis_max
            y = plot_bottom - ratio * (plot_bottom - plot_top)
            canvas.create_line(plot_left, y, plot_right, y, fill="#e8e8e8")
            canvas.create_text(
                plot_left - 8, y, text=f"{tick:g}", anchor="e", fill="#666666",
                font=("Microsoft YaHei UI", 8),
            )
            tick += step

        canvas.create_line(plot_left, plot_top, plot_left, plot_bottom, fill="#999999")
        canvas.create_line(plot_left, plot_bottom, plot_right, plot_bottom, fill="#999999")

        count = len(self._items)
        slot = (plot_right - plot_left) / count
        bar_width = max(slot * 0.55, 6)

        for index, (name, value) in enumerate(self._items):
            center = plot_left + slot * (index + 0.5)
            bar_height = (value / axis_max) * (plot_bottom - plot_top)
            top = plot_bottom - bar_height
            color = BAR_COLORS[index % len(BAR_COLORS)]
            canvas.create_rectangle(
                center - bar_width / 2,
                top,
                center + bar_width / 2,
                plot_bottom,
                fill=color,
                outline="",
            )
            value_text = f"{value:g}"
            if self._unit:
                value_text = f"{value_text} {self._unit.lstrip()}"
            canvas.create_text(
                center, top - 8, text=value_text, fill="#333333",
                font=("Microsoft YaHei UI", 8),
            )
            label = name if len(name) <= 9 else name[:8] + "…"
            canvas.create_text(
                center, plot_bottom + 14, text=label, fill="#444444",
                font=("Microsoft YaHei UI", 8),
            )
