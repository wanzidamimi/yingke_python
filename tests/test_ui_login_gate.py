import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX = ROOT / "static" / "index.html"


class UiLoginGateTest(unittest.TestCase):
    def test_login_modal_and_user_panel_exist(self):
        text = INDEX.read_text(encoding="utf-8")
        for needle in [
            'id="loginModal"', 'id="userChip"', 'id="logoutBtn"',
            "fetch('/api/session/current')", "/api/session/logout",
        ]:
            self.assertIn(needle, text)

    def test_login_modal_has_no_password_field(self):
        text = INDEX.read_text(encoding='utf-8')
        m = re.search(r'id="loginModal".*?</div>\s*</div>', text, re.S)
        self.assertIsNotNone(m)
        self.assertNotIn('type="password"', m.group(0))

    def test_gid_sync_event_refreshes_session(self):
        text = INDEX.read_text(encoding='utf-8')
        self.assertIn('已从认证响应同步 gid', text)
        m = re.search(r"es\.onmessage = e => \{.*?\};", text, re.S)
        self.assertIsNotNone(m)
        self.assertIn('refreshSession(false)', m.group(0))


if __name__ == "__main__":
    unittest.main()
