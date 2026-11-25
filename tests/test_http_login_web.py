import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import app as app_module
import http_login_web
import inke_tcp_collector
import login_state


class HttpLoginWebTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_module.app)
        self.old_start = http_login_web.start_sms
        self.old_complete = http_login_web.complete_login
        self.old_app_start = app_module.start_sms
        self.old_app_complete = app_module.complete_login

    def tearDown(self):
        http_login_web.start_sms = self.old_start
        http_login_web.complete_login = self.old_complete
        app_module.start_sms = self.old_app_start
        app_module.complete_login = self.old_app_complete

    def test_sms_endpoint_returns_token_only(self):
        app_module.start_sms = lambda phone, area_code="86", region="cn": {
            "ok": True, "token": "TOKEN123", "message": "已发送", "masked_phone": "138****8000"
        }
        r = self.client.post("/api/login/http/sms", json={"phone": "13800138000"})
        data = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(data["token"], "TOKEN123")
        self.assertNotIn("request_id", data)
        self.assertNotIn("13800138000", r.text)

    def test_verify_endpoint(self):
        app_module.complete_login = lambda token, phone, code: {
            "ok": True, "message": "成功", "masked": {"uid": 123, "sid": "ab***cd", "gid": "***abcd"}
        }
        r = self.client.post("/api/login/http/verify", json={
            "token": "TOKEN123", "phone": "13800138000", "code": "123456"
        })
        data = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(data["ok"])
        self.assertNotIn("123456", r.text)

    def test_http_config_clears_gid(self):
        cfg = http_login_web._build_runtime_config({
            "uid": 778965813,
            "session": "TEST_SESSION_VALUE",
        }, "86")
        self.assertEqual(cfg["gid"], "")
        self.assertEqual(cfg["auth"]["gid"], "")
        self.assertEqual(cfg["auth"]["bus_buf"]["gid"], "")
        self.assertEqual(cfg["auth"]["bus_buf"]["sid"], "TEST_SESSION_VALUE")

    def test_pending_token_is_single_use(self):
        http_login_web._pending.clear()
        ok = http_login_web.start_sms("13800138000")
        self.assertTrue(ok["ok"])
        token = ok["token"]
        self.assertIn(token, http_login_web._pending)

        old = http_login_web.probe.login_with_code
        old_validate = http_login_web.probe.validate_login_result
        old_save = login_state.save_login_state
        old_refresh = inke_tcp_collector.refresh_gid_from_adb
        http_login_web.probe.login_with_code = lambda *a, **k: {
            "body": '{"dm_error":0,"uid":123,"session":"s","secret":"x"}'
        }
        http_login_web.probe.validate_login_result = lambda d: True
        inke_tcp_collector.refresh_gid_from_adb = lambda c: c
        login_state.save_login_state = lambda r: "local.json"
        try:
            first = http_login_web.complete_login(token, "13800138000", "123456")
            second = http_login_web.complete_login(token, "13800138000", "123456")
            self.assertTrue(first["ok"])
            self.assertFalse(second["ok"])
            self.assertNotIn(token, http_login_web._pending)
        finally:
            http_login_web.probe.login_with_code = old
            http_login_web.probe.validate_login_result = old_validate
            login_state.save_login_state = old_save
            inke_tcp_collector.refresh_gid_from_adb = old_refresh


if __name__ == "__main__":
    unittest.main()
