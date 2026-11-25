import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX = ROOT / "static" / "index.html"


class UiLayoutTest(unittest.TestCase):
    def setUp(self):
        self.text = INDEX.read_text(encoding="utf-8")

    def test_login_section_has_lock_overlay(self):
        for needle in [
            'id="loginSection"',
            'id="loginLock"',
            "function setLoginLocked",
            "setLoginLocked(true)",
            "setLoginLocked(false)",
        ]:
            self.assertIn(needle, self.text)

    def test_pc_workspace_is_two_columns(self):
        self.assertIn("grid-template-columns: minmax(300px, 38%) minmax(0, 1fr)", self.text)

    def test_video_keeps_portrait_ratio(self):
        self.assertIn("aspect-ratio: 9 / 16", self.text)


if __name__ == "__main__":
    unittest.main()
