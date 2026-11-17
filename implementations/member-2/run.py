"""启动入口。

用法::

    python run.py                 # 使用默认数据文件 data/data.json
    python run.py --data D:/tmp/x.json
    python run.py --demo          # 数据文件为空时写入一组演示数据

本程序只使用 Python 标准库，无需安装任何第三方依赖。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 允许以任意工作目录运行本脚本。
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.paths import DEFAULT_DATA_FILE  # noqa: E402
from app.service import LabService  # noqa: E402
from app.store import JsonStore  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="实验室设备预约管理器")
    parser.add_argument(
        "--data",
        default=str(DEFAULT_DATA_FILE),
        help="JSON 数据文件路径（默认：implementations/member-2/data/data.json）",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="当数据文件为空时写入演示数据，便于快速查看界面效果",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    service = LabService(JsonStore(args.data))
    if args.demo:
        service.seed_demo_data()
    window = MainWindow(service)
    window.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
