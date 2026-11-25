import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import login_session


class LoginSessionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = self.root / "local.json"
        self.meta = self.root / "session.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write_config(self, uid=778965813, sid="TEST_SESSION_VALUE", gid="abc123"):
        data = {
            "uid": uid,
            "gid": gid,
            "auth": {"uid": uid, "gid": gid, "bus_buf": {"uid": str(uid), "sid": sid, "gid": gid}},
            "enter_room": {"uid": uid, "gid": gid, "bus_buf": {"uid": uid, "gid": gid}},
        }
        self.config.write_text(json.dumps(data), encoding="utf-8")
        return data

    def test_missing_config_is_not_logged_in(self):
        r = login_session.current_session(self.config, self.meta)
        self.assertFalse(r["logged_in"])
        self.assertEqual(r["reason"], "missing_local_config")
        self.assertIsNone(r["user"])

    def test_incomplete_config_is_not_logged_in(self):
        self.write_config(uid=0, sid="")
        r = login_session.current_session(self.config, self.meta)
        self.assertFalse(r["logged_in"])
        self.assertEqual(r["reason"], "incomplete_credentials")

    def test_empty_gid_is_still_logged_in(self):
        self.write_config(gid="")
        r = login_session.current_session(self.config, self.meta)
        self.assertTrue(r["logged_in"])
        self.assertEqual(r["user"]["gid_status"], "pending")

    def test_mark_logged_in_writes_masked_metadata(self):
        self.write_config()
        login_session.mark_logged_in(
            "http_sms", 778965813, masked_phone="176****9175",
            meta_path=self.meta,
        )
        r = login_session.current_session(self.config, self.meta)
        self.assertEqual(r["user"]["login_method"], "http_sms")
        self.assertEqual(r["user"]["phone_masked"], "176****9175")
        self.assertNotIn("TEST_SESSION_VALUE", json.dumps(r, ensure_ascii=False))

    def test_logout_removes_local_credential_and_metadata(self):
        self.write_config()
        self.meta.write_text("{}", encoding="utf-8")
        r = login_session.logout(self.config, self.meta)
        self.assertTrue(r["ok"])
        self.assertFalse(self.config.exists())
        self.assertFalse(self.meta.exists())


if __name__ == "__main__":
    unittest.main()
