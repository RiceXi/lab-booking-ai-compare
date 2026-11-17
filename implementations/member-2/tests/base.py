"""测试公共工具：构造运行在临时目录中的服务实例。"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from app.service import LabService
from app.store import JsonStore


class ServiceTestCase(unittest.TestCase):
    """在临时目录里创建服务，测试结束后自动清理。"""

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="lab-booking-test-"))
        self.data_file = self.temp_dir / "data.json"
        self.service = LabService(JsonStore(self.data_file))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ------------------------------------------------------------ 快捷方法
    def add_equipment(
        self,
        code: str = "EQ-001",
        name: str = "高速离心机",
        location: str = "生化楼 A-201",
        status: str = "available",
        opening_start: str = "08:00",
        opening_end: str = "20:00",
        notes: str = "",
    ):
        return self.service.add_equipment(
            code=code,
            name=name,
            location=location,
            status=status,
            opening_start=opening_start,
            opening_end=opening_end,
            notes=notes,
        )

    def add_reservation(self, equipment, requester="张三", date="2026-11-17", start="09:00", end="10:00", notes=""):
        return self.service.add_reservation(
            equipment_id=equipment.id,
            requester=requester,
            date=date,
            start_time=start,
            end_time=end,
            notes=notes,
        )
