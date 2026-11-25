import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX = ROOT / "static" / "index.html"
PLAYER = ROOT / "static" / "vendor" / "mpegts.min.js"


class UiVideoPlayerTest(unittest.TestCase):
    def test_player_assets_and_hooks_exist(self):
        text = INDEX.read_text(encoding="utf-8")
        for needle in [
            'id="liveVideo"',
            'id="videoPlaceholder"',
            "mpegts.createPlayer",
            "function loadVideo",
            "function destroyVideo",
            "/api/video/check",
            "/api/video/stream",
            "new URL(",
        ]:
            self.assertIn(needle, text)

    def test_local_player_library_exists(self):
        self.assertTrue(PLAYER.exists())
        self.assertGreater(PLAYER.stat().st_size, 10000)


if __name__ == "__main__":
    unittest.main()
