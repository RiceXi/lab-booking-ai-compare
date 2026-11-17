"""预约管理页签（FR2、FR3、FR4、FR5）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..errors import AppError
from ..models import RESERVATION_STATUS_LABELS, Reservation, ReservationStatus
from ..service import LabService, ReservationFilter
from .widgets import time_options, today_iso

#: 状态下拉框：(显示文本, 枚举值)
STATUS_OPTIONS: list[tuple[str, str]] = [
    (RESERVATION_STATUS_LABELS[ReservationStatus.BOOKED.value], ReservationStatus.BOOKED.value),
    (RESERVATION_STATUS_LABELS[ReservationStatus.IN_USE.value], ReservationStatus.IN_USE.value),
    (RESERVATION_STATUS_LABELS[ReservationStatus.COMPLETED.value], ReservationStatus.COMPLETED.value),
    (RESERVATION_STATUS_LABELS[ReservationStatus.CANCELLED.value], ReservationStatus.CANCELLED.value),
]

ALL_LABEL = "全部"


class ReservationTab(ttk.Frame):
    """预约表单 + 筛选 + 预约列表 + 状态流转按钮。"""

    def __init__(self, master, service: LabService, **kwargs) -> None:
        super().__init__(master, padding=10, **kwargs)
        self.service = service

        self.equipment_var = tk.StringVar()
        self.requester_var = tk.StringVar()
        self.date_var = tk.StringVar(value=today_iso())
        self.start_time_var = tk.StringVar(value="09:00")
        self.end_time_var = tk.StringVar(value="10:00")
        self.notes_var = tk.StringVar()

        self.filter_equipment_var = tk.StringVar(value=ALL_LABEL)
        self.filter_status_var = tk.StringVar(value=ALL_LABEL)
        self.filter_date_var = tk.StringVar()

        self._equipment_ids: list[str] = []
        self._filter_equipment_ids: list[str | None] = [None]

        self._build_form()
        self._build_filter()
        self._build_table()
        self.refresh()
        self.service.add_listener(self.refresh)

    # ------------------------------------------------------------- 构建界面
    def _build_form(self) -> None:
        form = ttk.LabelFrame(self, text="新建预约")
        form.pack(fill="x", pady=(0, 8))

        labels = [
            "设备 *",
            "预约人 *",
            "日期 *",
            "开始时间 *",
            "结束时间 *",
            "备注",
        ]
        for column, text in enumerate(labels):
            ttk.Label(form, text=text).grid(row=0, column=column, sticky="w", padx=(8, 4), pady=6)

        self.equipment_combo = ttk.Combobox(
            form, textvariable=self.equipment_var, state="readonly", width=26
        )
        self.requester_entry = ttk.Entry(form, textvariable=self.requester_var, width=14)
        self.date_entry = ttk.Entry(form, textvariable=self.date_var, width=12)
        time_values = time_options()
        self.start_combo = ttk.Combobox(
            form, textvariable=self.start_time_var, values=time_values, state="readonly", width=8
        )
        self.end_combo = ttk.Combobox(
            form, textvariable=self.end_time_var, values=time_values, state="readonly", width=8
        )
        self.notes_entry = ttk.Entry(form, textvariable=self.notes_var, width=16)

        widgets = [
            self.equipment_combo,
            self.requester_entry,
            self.date_entry,
            self.start_combo,
            self.end_combo,
            self.notes_entry,
        ]
        for column, widget in enumerate(widgets):
            widget.grid(row=1, column=column, sticky="ew", padx=(8, 8), pady=(0, 6))

        ttk.Button(form, text="创建预约", command=self.on_create).grid(
            row=1, column=6, sticky="w", padx=(4, 8), pady=(0, 6)
        )
        ttk.Button(form, text="清空表单", command=self.on_clear).grid(
            row=1, column=7, sticky="w", padx=(0, 8), pady=(0, 6)
        )

        for column in range(6):
            form.columnconfigure(column, weight=1)

    def _build_filter(self) -> None:
        frame = ttk.LabelFrame(self, text="筛选预约（多个条件可组合，条件之间为“与”关系）")
        frame.pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text="设备").pack(side="left", padx=(8, 4), pady=6)
        self.filter_equipment_combo = ttk.Combobox(
            frame, textvariable=self.filter_equipment_var, state="readonly", width=22
        )
        self.filter_equipment_combo.pack(side="left", padx=(0, 10))

        ttk.Label(frame, text="状态").pack(side="left", padx=(0, 4))
        self.filter_status_combo = ttk.Combobox(
            frame,
            textvariable=self.filter_status_var,
            values=[ALL_LABEL] + [label for label, _ in STATUS_OPTIONS],
            state="readonly",
            width=10,
        )
        self.filter_status_combo.pack(side="left", padx=(0, 10))

        ttk.Label(frame, text="日期").pack(side="left", padx=(0, 4))
        self.filter_date_entry = ttk.Entry(frame, textvariable=self.filter_date_var, width=12)
        self.filter_date_entry.pack(side="left", padx=(0, 10))

        ttk.Button(frame, text="筛选", command=self.on_filter).pack(side="left", padx=4)
        ttk.Button(frame, text="重置", command=self.on_reset_filter).pack(side="left", padx=4)

    def _build_table(self) -> None:
        table_frame = ttk.LabelFrame(self, text="预约列表")
        table_frame.pack(fill="both", expand=True)

        columns = ("code", "name", "requester", "date", "start", "end", "status", "notes")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "code": ("设备编号", 110),
            "name": ("设备名称", 160),
            "requester": ("预约人", 100),
            "date": ("日期", 110),
            "start": ("开始时间", 90),
            "end": ("结束时间", 90),
            "status": ("状态", 80),
            "notes": ("备注", 200),
        }
        for key, (text, width) in headings.items():
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="开始使用", command=lambda: self.on_transition("start")).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(actions, text="标记完成", command=lambda: self.on_transition("complete")).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="取消预约", command=lambda: self.on_transition("cancel")).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="刷新列表", command=self.refresh).pack(side="left", padx=6)

        self.summary = tk.Label(self, text="", foreground="#666666")
        self.summary.pack(anchor="w", pady=(6, 0))

    # ------------------------------------------------------------- 数据刷新
    def refresh(self) -> None:
        """刷新设备下拉框、筛选下拉框和预约列表。"""
        if not hasattr(self, "tree"):
            return

        equipment_list = self.service.list_equipment()
        display_values = []
        self._equipment_ids = []
        for equipment in equipment_list:
            suffix = "" if equipment.status.value == "available" else f"（{equipment.status_label}）"
            display_values.append(f"{equipment.code} {equipment.name}{suffix}")
            self._equipment_ids.append(equipment.id)
        self.equipment_combo["values"] = display_values
        if display_values and self.equipment_var.get() not in display_values:
            self.equipment_var.set(display_values[0])

        filter_values = [ALL_LABEL]
        self._filter_equipment_ids = [None]
        for equipment in equipment_list:
            filter_values.append(f"{equipment.code} {equipment.name}")
            self._filter_equipment_ids.append(equipment.id)
        self.filter_equipment_combo["values"] = filter_values
        if self.filter_equipment_var.get() not in filter_values:
            self.filter_equipment_var.set(ALL_LABEL)

        self._refresh_tree()

    def _refresh_tree(self) -> None:
        selected = self.tree.selection()
        selected_id = selected[0] if selected else None
        self.tree.delete(*self.tree.get_children())

        filters = self._current_filters()
        reservations = self.service.list_reservations(filters)
        for reservation in reservations:
            equipment = self.service.get_equipment(reservation.equipment_id)
            code = equipment.code if equipment else "(已删除)"
            name = equipment.name if equipment else "已删除设备"
            self.tree.insert(
                "",
                "end",
                iid=reservation.id,
                values=(
                    code,
                    name,
                    reservation.requester,
                    reservation.date,
                    reservation.start_time,
                    reservation.end_time,
                    reservation.status_label,
                    reservation.notes,
                ),
            )
        if selected_id and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)
        self.summary.configure(text=f"共 {len(reservations)} 条预约记录。")

    def _current_filters(self) -> ReservationFilter:
        equipment_id = None
        index = self.filter_equipment_combo.current()
        if index >= 0 and index < len(self._filter_equipment_ids):
            equipment_id = self._filter_equipment_ids[index]
        status = None
        label = self.filter_status_var.get()
        if label and label != ALL_LABEL:
            status = next((value for text, value in STATUS_OPTIONS if text == label), None)
        date = self.filter_date_var.get().strip()
        return ReservationFilter(equipment_id=equipment_id, date=date or None, status=status)

    # ------------------------------------------------------------- 表单操作
    def on_clear(self) -> None:
        self.requester_var.set("")
        self.date_var.set(today_iso())
        self.start_time_var.set("09:00")
        self.end_time_var.set("10:00")
        self.notes_var.set("")

    def on_create(self) -> None:
        index = self.equipment_combo.current()
        if index < 0 or index >= len(self._equipment_ids):
            messagebox.showerror("创建失败", "请选择一个设备。", parent=self)
            return
        equipment_id = self._equipment_ids[index]
        try:
            reservation = self.service.add_reservation(
                equipment_id=equipment_id,
                requester=self.requester_var.get(),
                date=self.date_var.get(),
                start_time=self.start_time_var.get(),
                end_time=self.end_time_var.get(),
                notes=self.notes_var.get(),
            )
        except AppError as error:
            messagebox.showerror("创建失败", error.message, parent=self)
            return
        messagebox.showinfo(
            "创建成功",
            f"预约创建成功：{reservation.date} {reservation.time_range}（{reservation.requester}）。",
            parent=self,
        )
        self.on_clear()

    def on_filter(self) -> None:
        self._refresh_tree()

    def on_reset_filter(self) -> None:
        self.filter_equipment_var.set(ALL_LABEL)
        self.filter_status_var.set(ALL_LABEL)
        self.filter_date_var.set("")
        self._refresh_tree()

    def current_reservation(self) -> Reservation | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.service.get_reservation(selection[0])

    def on_transition(self, action: str) -> None:
        reservation = self.current_reservation()
        if reservation is None:
            messagebox.showwarning("请先选择预约", "请在列表中选择一条预约记录。", parent=self)
            return

        try:
            if action == "start":
                updated = self.service.start_use(reservation.id)
            elif action == "complete":
                updated = self.service.complete_reservation(reservation.id)
            else:
                updated = self.service.cancel_reservation(reservation.id)
        except AppError as error:
            messagebox.showerror("状态流转失败", error.message, parent=self)
            return
        messagebox.showinfo(
            "操作成功", f"预约状态已更新为「{updated.status_label}」。", parent=self
        )
