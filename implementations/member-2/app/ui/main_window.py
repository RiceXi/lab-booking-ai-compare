"""主窗口与页签装配。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..service import LabService
from .equipment_tab import EquipmentTab
from .reservation_tab import ReservationTab
from .stats_tab import StatsTab


class MainWindow(tk.Tk):
    """实验室设备预约管理器主窗口。"""

    def __init__(self, service: LabService) -> None:
        super().__init__()
        self.service = service

        self.title("实验室设备预约管理器")
        self.geometry("1120x760")
        self.minsize(980, 680)

        self._configure_style()

        header = ttk.Frame(self, padding=(12, 10, 12, 0))
        header.pack(fill="x")
        ttk.Label(
            header,
            text="实验室设备预约管理器",
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(side="left")
        self.data_hint = ttk.Label(header, text="", foreground="#666666")
        self.data_hint.pack(side="right")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook = notebook

        self.equipment_tab = EquipmentTab(notebook, service)
        self.reservation_tab = ReservationTab(notebook, service)
        self.stats_tab = StatsTab(notebook, service)

        notebook.add(self.equipment_tab, text="  设备管理  ")
        notebook.add(self.reservation_tab, text="  预约管理  ")
        notebook.add(self.stats_tab, text="  统计与可视化  ")

        self.data_hint.configure(text=f"数据文件：{service.store.path}")

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:  # pragma: no cover - 某些平台缺少 vista 主题
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass
        style.configure("Treeview", rowheight=24)
        style.configure("TLabel", font=("Microsoft YaHei UI", 9))
        style.configure("TButton", font=("Microsoft YaHei UI", 9))
        style.configure("TNotebook.Tab", font=("Microsoft YaHei UI", 10))
