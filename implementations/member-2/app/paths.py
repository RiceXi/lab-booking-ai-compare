"""路径常量。

数据文件位置：``implementations/member-2/data/data.json``（运行说明中已注明）。
"""

from __future__ import annotations

from pathlib import Path

#: implementations/member-2 目录
APP_ROOT = Path(__file__).resolve().parent.parent

#: 数据目录
DATA_DIR = APP_ROOT / "data"

#: 默认数据文件
DEFAULT_DATA_FILE = DATA_DIR / "data.json"
