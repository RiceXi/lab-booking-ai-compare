"""设备管理页签（FR1）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..errors import AppError
from ..models import EQUIPMENT_STATUS_LABELS, Equipment, EquipmentStatus
from ..service import LabService
from .widgets import time_options

#: 状态下拉框：(显示文本, 枚举值)
STATUS_OPTIONS: list[tuple[str, str]] = [
    (EQUIPMENT_STATUS_LABELS[EquipmentStatus.AVAILABLE.value], EquipmentStatus.AVAILABLE.value),
    (EQUIPMENT_STATUS_LABELS[EquipmentStatus.MAINTENANCE.value], EquipmentStatus.MAINTENANCE.value),
    (EQUIPMENT_STATUS_LABELS[EquipmentStatus.RETIRED.value], EquipmentStatus.RETIRED.value),
]

STATUS_BY_LABEL: dict[str, str] = {label: value for label, value in STATUS_OPTIONS}


class EquipmentTab(ttk.Frame):
    """设备列表 + 设备表单。"""

    def __init__(self, master, service: LabService, **kwargs) -> None:
        super().__init__(master, padding=10, **kwargs)
        self.service = service

        self.code_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.location_var = tk.StringVar()
        self.status_var = tk.StringVar(value=STATUS_OPTIONS[0][0])
        self.opening_start_var = tk.StringVar(value="08:00")
        self.opening_end_var = tk.StringVar(value="18:00")
        self.notes_var = tk.StringVar()

        self._build_form()
        self._build_table()
        self.refresh()
        self.service.add_listener(self.refresh)

    # ------------------------------------------------------------- 构建界面
    def _build_form(self) -> None:
        form = ttk.LabelFrame(self, text="设备信息")
        form.pack(fill="x", pady=(0, 8))

        labels = [
            ("设备编号 *", self.code_var),
            ("设备名称 *", self.name_var),
            ("存放位置 *", self.location_var),
            ("设备状态", None),
            ("可预约开始 *", None),
            ("可预约结束 *", None),
            ("备注", self.notes_var),
        ]
        for column, (text, variable) in enumerate(labels):
            ttk.Label(form, text=text).grid(row=0, column=column, sticky="w", padx=(8, 4), pady=8)

        self.code_entry = ttk.Entry(form, textvariable=self.code_var, width=16)
        self.name_entry = ttk.Entry(form, textvariable=self.name_var, width=16)
        self.location_entry = ttk.Entry(form, textvariable=self.location_var, width=16)
        self.status_combo = ttk.Combobox(
            form,
            textvariable=self.status_var,
            values=[label for label, _ in STATUS_OPTIONS],
            state="readonly",
            width=13,
        )
        time_values = time_options()
        self.opening_start_combo = ttk.Combobox(
            form, textvariable=self.opening_start_var, values=time_values, state="readonly", width=9
        )
        self.opening_end_combo = ttk.Combobox(
            form, textvariable=self.opening_end_var, values=time_values, state="readonly", width=9
        )
        self.notes_entry = ttk.Entry(form, textvariable=self.notes_var, width=20)

        widgets = [
            self.code_entry,
            self.name_entry,
            self.location_entry,
            self.status_combo,
            self.opening_start_combo,
            self.opening_end_combo,
            self.notes_entry,
        ]
        for column, widget in enumerate(widgets):
            widget.grid(row=1, column=column, sticky="ew", padx=(8, 8), pady=(0, 8))

        button_bar = ttk.Frame(form)
        button_bar.grid(row=2, column=0, columnspan=7, sticky="w", padx=8, pady=(0, 8))
        ttk.Button(button_bar, text="添加设备", command=self.on_add).pack(side="left", padx=(0, 6))
        ttk.Button(button_bar, text="更新设备", command=self.on_update).pack(side="left", padx=6)
        ttk.Button(button_bar, text="清空表单", command=self.on_clear).pack(side="left", padx=6)
        ttk.Button(button_bar, text="删除设备", command=self.on_delete).pack(side="left", padx=6)

        for column in range(7):
            form.columnconfigure(column, weight=1)

    def _build_table(self) -> None:
        table_frame = ttk.LabelFrame(self, text="设备列表")
        table_frame.pack(fill="both", expand=True)

        columns = ("code", "name", "location", "status", "hours", "notes", "updated_at")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "code": ("设备编号", 110),
            "name": ("设备名称", 170),
            "location": ("存放位置", 150),
            "status": ("状态", 80),
            "hours": ("可预约时段", 130),
            "notes": ("备注", 180),
            "updated_at": ("更新时间", 170),
        }
        for key, (text, width) in headings.items():
            self.tree.heading(key, text=text)
            self.tree.column(key, width=width, anchor="w")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.status_hint = tk.Label(
            self, text="提示：先在表单中填写设备信息，点击“添加设备”保存。", foreground="#666666"
        )
        self.status_hint.pack(anchor="w", pady=(6, 0))

    # ------------------------------------------------------------- 数据刷新
    def refresh(self) -> None:
        """重新加载设备列表。"""
        if not hasattr(self, "tree"):
            return
        selected = self.tree.selection()
        selected_id = selected[0] if selected else None
        self.tree.delete(*self.tree.get_children())
        for equipment in self.service.list_equipment():
            self.tree.insert(
                "",
                "end",
                iid=equipment.id,
                values=(
                    equipment.code,
                    equipment.name,
                    equipment.location,
                    equipment.status_label,
                    equipment.opening_hours,
                    equipment.notes,
                    equipment.updated_at,
                ),
            )
        if selected_id and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)

    # ------------------------------------------------------------- 表单操作
    def current_equipment(self) -> Equipment | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.service.get_equipment(selection[0])

    def on_select(self, _event=None) -> None:
        equipment = self.current_equipment()
        if equipment is None:
            return
        self.code_var.set(equipment.code)
        self.name_var.set(equipment.name)
        self.location_var.set(equipment.location)
        self.status_var.set(
            EQUIPMENT_STATUS_LABELS.get(equipment.status.value, equipment.status.value)
        )
        self.opening_start_var.set(equipment.opening_start)
        self.opening_end_var.set(equipment.opening_end)
        self.notes_var.set(equipment.notes)
        self.status_hint.configure(text=f"当前选中：{equipment.code} {equipment.name}（点击“更新设备”保存修改）")

    def on_clear(self) -> None:
        self.code_var.set("")
        self.name_var.set("")
        self.location_var.set("")
        self.status_var.set(STATUS_OPTIONS[0][0])
        self.opening_start_var.set("08:00")
        self.opening_end_var.set("18:00")
        self.notes_var.set("")
        self.tree.selection_remove(self.tree.selection())
        self.status_hint.configure(text="提示：先在表单中填写设备信息，点击“添加设备”保存。")

    def _collect(self) -> dict:
        return {
            "code": self.code_var.get(),
            "name": self.name_var.get(),
            "location": self.location_var.get(),
            "status": STATUS_BY_LABEL.get(self.status_var.get(), EquipmentStatus.AVAILABLE.value),
            "opening_start": self.opening_start_var.get(),
            "opening_end": self.opening_end_var.get(),
            "notes": self.notes_var.get(),
        }

    def on_add(self) -> None:
        payload = self._collect()
        try:
            equipment = self.service.add_equipment(**payload)
        except AppError as error:
            messagebox.showerror("添加失败", error.message, parent=self)
            return
        messagebox.showinfo("添加成功", f"设备「{equipment.code} {equipment.name}」已添加。", parent=self)
        self.on_clear()

    def on_update(self) -> None:
        equipment = self.current_equipment()
        if equipment is None:
            messagebox.showwarning("请先选择设备", "请在下方列表中选择要更新的设备，再点击“更新设备”。", parent=self)
            return
        payload = self._collect()
        try:
            updated = self.service.update_equipment(equipment.id, **payload)
        except AppError as error:
            messagebox.showerror("更新失败", error.message, parent=self)
            return
        messagebox.showinfo("更新成功", f"设备「{updated.code}」已更新。", parent=self)
        self.on_clear()

    def on_delete(self) -> None:
        equipment = self.current_equipment()
        if equipment is None:
            messagebox.showwarning("请先选择设备", "请在下方列表中选择要删除的设备。", parent=self)
            return

        history = self.service.history_reservations_of(equipment.id)
        keep_history = True
        if history:
            answer = messagebox.askyesnocancel(
                "删除设备",
                f"设备「{equipment.code} {equipment.name}」有 {len(history)} 条历史预约"
                "（已完成 / 已取消）。\n\n"
                "是否保留这些历史预约？\n"
                "【是】保留历史预约（不影响后续预约冲突）\n"
                "【否】同时删除历史预约\n"
                "【取消】放弃本次删除",
                parent=self,
            )
            if answer is None:
                return
            keep_history = bool(answer)

        try:
            self.service.delete_equipment(equipment.id, keep_history=keep_history)
        except AppError as error:
            messagebox.showerror("删除失败", error.message, parent=self)
            return

        suffix = "（历史预约已保留）" if keep_history and history else ""
        messagebox.showinfo("删除成功", f"设备「{equipment.code}」已删除{suffix}。", parent=self)
        self.on_clear()
