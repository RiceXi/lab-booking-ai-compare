"""JSON 持久化层。

数据文件默认位于 ``implementations/member-2/data/data.json``（已被 .gitignore 忽略）。
写入采用"临时文件 + 原子替换"，避免程序意外中断导致数据文件损坏。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import DataFileError
from .models import Equipment, Reservation

SCHEMA_VERSION = 1


class JsonStore:
    """把设备和预约读写到单个 JSON 文件。"""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    # ------------------------------------------------------------------ 读
    def load(self) -> tuple[list[Equipment], list[Reservation]]:
        """读取数据文件。文件不存在时返回空列表。"""
        if not self.path.exists():
            return [], []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DataFileError(
                f"数据文件解析失败：{self.path}\n原因：{exc}\n"
                "请检查文件内容或删除该文件后重新启动程序。"
            ) from exc
        except OSError as exc:  # pragma: no cover - 依赖文件系统状态
            raise DataFileError(f"数据文件读取失败：{self.path}\n原因：{exc}") from exc

        if not isinstance(raw, dict):
            raise DataFileError(f"数据文件格式非法（顶层应为对象）：{self.path}")

        equipment = [Equipment.from_dict(item) for item in raw.get("equipment", []) or []]
        reservations = [
            Reservation.from_dict(item) for item in raw.get("reservations", []) or []
        ]
        return equipment, reservations

    # ------------------------------------------------------------------ 写
    def save(self, equipment: list[Equipment], reservations: list[Reservation]) -> None:
        """原子地把数据写入文件。"""
        payload: dict[str, Any] = {
            "version": SCHEMA_VERSION,
            "equipment": [item.to_dict() for item in equipment],
            "reservations": [item.to_dict() for item in reservations],
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(payload, ensure_ascii=False, indent=2)
            # 先写同目录临时文件，再原子替换，避免写出半截文件。
            handle = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(self.path.parent),
                prefix=self.path.name,
                suffix=".tmp",
                delete=False,
            )
            try:
                with handle:
                    handle.write(text)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(handle.name, self.path)
            except BaseException:
                # 替换失败时清理临时文件，避免残留垃圾。
                try:
                    os.unlink(handle.name)
                except OSError:  # pragma: no cover
                    pass
                raise
        except OSError as exc:
            raise DataFileError(f"数据文件写入失败：{self.path}\n原因：{exc}") from exc
