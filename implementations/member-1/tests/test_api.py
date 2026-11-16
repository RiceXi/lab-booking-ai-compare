"""HTTP integration tests for the local JSON API."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import create_server


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "api.sqlite"
        self.server = create_server("127.0.0.1", 0, db_path)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temp_dir.cleanup()

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict | list | None = None,
    ) -> tuple[int, dict]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Content-Type": "application/json"} if body else {},
        )
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            try:
                return error.code, json.loads(error.read())
            finally:
                error.close()

    def test_health_and_static_page(self) -> None:
        status, payload = self.request("/api/health")
        self.assertEqual(200, status)
        self.assertEqual({"status": "ok"}, payload)
        with urlopen(f"{self.base_url}/", timeout=3) as response:
            html = response.read().decode("utf-8")
        self.assertIn("实验室设备预约", html)

    def test_equipment_crud_and_error_shape(self) -> None:
        payload = {
            "code": "API-001",
            "name": "示波器",
            "location": "A-201",
            "status": "available",
            "opening_start": "08:00",
            "opening_end": "18:00",
        }
        status, created = self.request(
            "/api/equipment",
            method="POST",
            payload=payload,
        )
        self.assertEqual(201, status)
        equipment_id = created["item"]["id"]

        status, duplicate = self.request(
            "/api/equipment",
            method="POST",
            payload=payload,
        )
        self.assertEqual(409, status)
        self.assertEqual("equipment_code_exists", duplicate["error"]["code"])

        payload["name"] = "数字示波器"
        status, updated = self.request(
            f"/api/equipment/{equipment_id}",
            method="PUT",
            payload=payload,
        )
        self.assertEqual(200, status)
        self.assertEqual("数字示波器", updated["item"]["name"])

        status, detail = self.request(f"/api/equipment/{equipment_id}")
        self.assertEqual(200, status)
        self.assertEqual("数字示波器", detail["item"]["name"])

        status, malformed = self.request(
            "/api/equipment",
            method="POST",
            payload=[],
        )
        self.assertEqual(400, status)
        self.assertEqual("invalid_request", malformed["error"]["code"])

    def test_reservation_conflict_is_returned_as_409(self) -> None:
        _, created = self.request(
            "/api/equipment",
            method="POST",
            payload={
                "code": "API-002",
                "name": "信号源",
                "location": "A-202",
                "status": "available",
                "opening_start": "08:00",
                "opening_end": "18:00",
            },
        )
        reservation = {
            "equipment_id": created["item"]["id"],
            "requester": "测试人",
            "date": "2026-11-21",
            "start_time": "09:00",
            "end_time": "10:00",
        }
        status, first = self.request(
            "/api/reservations",
            method="POST",
            payload=reservation,
        )
        self.assertEqual(201, status)
        status, conflict = self.request(
            "/api/reservations",
            method="POST",
            payload={**reservation, "start_time": "09:30", "end_time": "10:30"},
        )
        self.assertEqual(409, status)
        self.assertEqual("reservation_conflict", conflict["error"]["code"])

        status, cancelled = self.request(
            f"/api/reservations/{first['item']['id']}/status",
            method="PATCH",
            payload={"status": "cancelled"},
        )
        self.assertEqual(200, status)
        self.assertEqual("cancelled", cancelled["item"]["status"])

    def test_invalid_transition_and_delete_protection_are_returned_as_409(self) -> None:
        _, created = self.request(
            "/api/equipment",
            method="POST",
            payload={
                "code": "API-003",
                "name": "逻辑分析仪",
                "location": "A-203",
                "status": "available",
                "opening_start": "08:00",
                "opening_end": "18:00",
            },
        )
        equipment_id = created["item"]["id"]
        _, reservation = self.request(
            "/api/reservations",
            method="POST",
            payload={
                "equipment_id": equipment_id,
                "requester": "状态测试",
                "date": "2026-11-22",
                "start_time": "09:00",
                "end_time": "10:00",
            },
        )
        reservation_id = reservation["item"]["id"]

        status, invalid = self.request(
            f"/api/reservations/{reservation_id}/status",
            method="PATCH",
            payload={"status": "completed"},
        )
        self.assertEqual(409, status)
        self.assertEqual("invalid_status_transition", invalid["error"]["code"])

        status, blocked = self.request(
            f"/api/equipment/{equipment_id}",
            method="DELETE",
        )
        self.assertEqual(409, status)
        self.assertEqual("equipment_in_use", blocked["error"]["code"])

        self.request(
            f"/api/reservations/{reservation_id}/status",
            method="PATCH",
            payload={"status": "cancelled"},
        )
        status, deleted = self.request(
            f"/api/equipment/{equipment_id}",
            method="DELETE",
        )
        self.assertEqual(200, status)
        self.assertTrue(deleted["deleted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
