import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import inke_tcp_collector as mod


class CollectorConfigTest(unittest.TestCase):
    def test_load_runtime_config_default(self):
        cfg = mod.load_runtime_config()
        self.assertIn('auth', cfg)
        self.assertIn('bus_buf', cfg['auth'])

    def test_load_runtime_config_override(self):
        data = {'uid': 42, 'auth': {}, 'enter_room': {}}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'config.json'
            p.write_text('{"uid": 42, "auth": {}, "enter_room": {}}', encoding='utf-8')
            cfg = mod.load_runtime_config(p)
            self.assertEqual(cfg['uid'], 42)

    def test_collector_does_not_bind_default_path_at_init(self):
        c = mod.InkeTcpCollector(liveid='123')
        self.assertIsNone(c.config_path)


if __name__ == '__main__':
    unittest.main()
