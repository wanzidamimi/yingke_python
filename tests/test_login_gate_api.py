import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import app as app_module
import login_session


class LoginGateApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_module.app)

    def test_current_session_endpoint(self):
        old = app_module.current_session
        app_module.current_session = lambda: {
            "ok": True, "logged_in": False, "reason": "missing_local_config", "user": None
        }
        try:
            r = self.client.get("/api/session/current")
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.json()["logged_in"])
        finally:
            app_module.current_session = old

    def test_logout_endpoint(self):
        old = app_module.logout
        app_module.logout = lambda: {"ok": True, "message": "已退出登录"}
        try:
            r = self.client.post("/api/session/logout")
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json()["ok"])
        finally:
            app_module.logout = old

    def test_start_blocked_when_not_logged_in(self):
        old_current = app_module.current_session
        app_module.current_session = lambda: {
            "ok": True, "logged_in": False, "reason": "missing_local_config", "user": None
        }
        try:
            r = self.client.post("/api/start", json={"room": "1795437498494586"})
            data = r.json()
            self.assertEqual(r.status_code, 200)
            self.assertFalse(data["ok"])
            self.assertEqual(data["reason"], "not_logged_in")
        finally:
            app_module.current_session = old_current

    def test_start_allowed_when_logged_in(self):
        old_current = app_module.current_session
        old_thread = app_module.threading.Thread

        class FakeThread:
            def __init__(self, *args, **kwargs):
                pass
            def start(self):
                pass

        app_module.current_session = lambda: {
            "ok": True, "logged_in": True, "reason": "", "user": {"uid": 778965813}
        }
        app_module.threading.Thread = FakeThread
        try:
            r = self.client.post("/api/start", json={"room": "1795437498494586"})
            self.assertTrue(r.json()["ok"])
        finally:
            app_module.current_session = old_current
            app_module.threading.Thread = old_thread


if __name__ == "__main__":
    unittest.main()
