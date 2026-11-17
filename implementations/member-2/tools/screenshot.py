"""开发辅助脚本：启动带演示数据的窗口，供截图工具抓取。

用法（在 implementations/member-2 目录下执行）::

    python tools/screenshot.py --tab stats --seconds 12

``--tab`` 可选 ``equipment`` / ``reservation`` / ``stats``，默认 ``equipment``。
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.service import LabService  # noqa: E402
from app.store import JsonStore  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="打开演示窗口")
    parser.add_argument(
        "--tab",
        default="equipment",
        choices=["equipment", "reservation", "stats"],
        help="启动后默认选中的页签",
    )
    parser.add_argument("--seconds", type=float, default=8.0, help="窗口自动关闭前的秒数")
    parser.add_argument("--data", default="", help="数据文件路径，默认使用临时文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_file = Path(args.data) if args.data else Path(tempfile.gettempdir()) / "lab-booking-demo.json"
    service = LabService(JsonStore(data_file))
    service.seed_demo_data()

    window = MainWindow(service)
    window.geometry("1120x760+30+30")
    window.update_idletasks()
    window.update()

    notebook = window.notebook
    tabs = {"equipment": 0, "reservation": 1, "stats": 2}
    notebook.select(tabs[args.tab])
    window.attributes("-topmost", True)
    window.update()
    print(f"READY tab={args.tab} data={data_file}", flush=True)
    window.after(int(args.seconds * 1000), window.destroy)
    window.mainloop()
    print("done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
