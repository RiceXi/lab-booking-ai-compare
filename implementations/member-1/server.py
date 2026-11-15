"""Dependency-free HTTP server for the lab booking manager."""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from booking import AppError, BookingService


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
DEFAULT_DB_PATH = APP_DIR / "data" / "lab_booking.sqlite"
EQUIPMENT_ITEM = re.compile(r"^/api/equipment/([^/]+)$")
RESERVATION_STATUS = re.compile(r"^/api/reservations/([^/]+)/status$")


class RequestHandler(BaseHTTPRequestHandler):
    service: BookingService

    def log_message(self, format_string: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {format_string % args}")

    def _send_json(
        self,
        payload: Any,
        status: int = HTTPStatus.OK,
    ) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            self._send_json(
                {"error": {"code": "not_found", "message": "页面不存在"}},
                HTTPStatus.NOT_FOUND,
            )
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Cache-Control",
            "no-cache" if path.name == "index.html" else "public, max-age=300",
        )
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self'; script-src 'self'; connect-src 'self'",
        )

    def _read_json(self) -> dict[str, Any]:
        length_header = self.headers.get("Content-Length", "0")
        try:
            content_length = int(length_header)
        except ValueError as exc:
            raise AppError("请求长度不合法") from exc
        if content_length > 1_000_000:
            raise AppError("请求内容过大", status=413)
        raw = self.rfile.read(content_length)
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AppError("请求内容必须是合法 JSON") from exc
        if not isinstance(payload, dict):
            raise AppError("请求内容必须是 JSON 对象")
        return payload

    def _handle_error(self, error: AppError) -> None:
        self._send_json(
            {
                "error": {
                    "code": error.code,
                    "message": error.message,
                    **error.details,
                }
            },
            error.status,
        )

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if method == "GET" and path == "/api/health":
                self._send_json({"status": "ok"})
                return
            if method == "GET" and path == "/api/equipment":
                self._send_json({"items": self.service.list_equipment()})
                return
            if method == "POST" and path == "/api/equipment":
                item = self.service.create_equipment(self._read_json())
                self._send_json({"item": item}, HTTPStatus.CREATED)
                return
            equipment_match = EQUIPMENT_ITEM.fullmatch(path)
            if equipment_match:
                equipment_id = equipment_match.group(1)
                if method == "GET":
                    self._send_json(
                        {"item": self.service.get_equipment(equipment_id)}
                    )
                    return
                if method == "PUT":
                    item = self.service.update_equipment(
                        equipment_id,
                        self._read_json(),
                    )
                    self._send_json({"item": item})
                    return
                if method == "DELETE":
                    self.service.delete_equipment(equipment_id)
                    self._send_json({"deleted": True})
                    return
            if method == "GET" and path == "/api/reservations":
                query = parse_qs(parsed.query)
                items = self.service.list_reservations(
                    equipment_id=query.get("equipment_id", [""])[0],
                    reservation_date=query.get("date", [""])[0],
                    status_value=query.get("status", [""])[0],
                )
                self._send_json({"items": items})
                return
            if method == "POST" and path == "/api/reservations":
                item = self.service.create_reservation(self._read_json())
                self._send_json({"item": item}, HTTPStatus.CREATED)
                return
            status_match = RESERVATION_STATUS.fullmatch(path)
            if method == "PATCH" and status_match:
                payload = self._read_json()
                new_status = payload.get("status")
                if not isinstance(new_status, str):
                    raise AppError(
                        "预约状态不能为空",
                        details={"field": "status"},
                    )
                item = self.service.update_reservation_status(
                    status_match.group(1),
                    new_status,
                )
                self._send_json({"item": item})
                return
            if method == "GET" and path == "/api/stats":
                self._send_json({"item": self.service.stats()})
                return
            raise AppError(
                "接口不存在",
                status=HTTPStatus.NOT_FOUND,
                code="not_found",
            )
        except AppError as error:
            self._handle_error(error)
        except Exception as error:
            print(f"[error] {type(error).__name__}: {error}")
            self._send_json(
                {
                    "error": {
                        "code": "internal_error",
                        "message": "服务器处理请求时发生错误",
                    }
                },
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self._dispatch("GET")
            return
        files = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/icons.js": ("icons.js", "text/javascript; charset=utf-8"),
        }
        if parsed.path not in files:
            self._send_json(
                {"error": {"code": "not_found", "message": "页面不存在"}},
                HTTPStatus.NOT_FOUND,
            )
            return
        filename, content_type = files[parsed.path]
        self._send_file(STATIC_DIR / filename, content_type)

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")


def create_server(
    host: str,
    port: int,
    db_path: str | Path,
) -> ThreadingHTTPServer:
    service = BookingService(db_path)
    handler = type("BoundRequestHandler", (RequestHandler,), {"service": service})
    return ThreadingHTTPServer((host, port), handler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="实验室设备预约管理器")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument(
        "--db",
        default=os.environ.get("LAB_BOOKING_DB", str(DEFAULT_DB_PATH)),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = create_server(args.host, args.port, Path(args.db).resolve())
    url = f"http://{args.host}:{server.server_port}"
    print("实验室设备预约管理器已启动")
    print(f"访问地址: {url}")
    print(f"数据文件: {Path(args.db).resolve()}")
    print("按 Ctrl+C 停止服务")
    if not args.no_browser:
        threading.Timer(0.6, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
