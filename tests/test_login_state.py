import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import login_state


class LoginStateTest(unittest.TestCase):
    def test_parse_prefs_xml(self):
        xml = """<?xml version='1.0'?><map>
        <string name=\"a\">hello</string>
        <int name=\"b\" value=\"10000\" />
        </map>"""
        data = login_state.parse_prefs_xml(xml)
        self.assertEqual(data['a'], 'hello')
        self.assertEqual(data['b'], '10000')

    def test_mask_value(self):
        self.assertEqual(login_state.mask_value('abcdefghijklmnop'), 'abcdef***mnop')
        self.assertEqual(login_state.mask_value('123'), '12***')

    def test_pick_sid_prefers_existing(self):
        candidates = ['AAAaaaaaaaaaaaaaaa', 'BBBbbbbbbbbbbbbbbb', 'AAAaaaaaaaaaaaaaaa']
        self.assertEqual(login_state.pick_sid(candidates), 'AAAaaaaaaaaaaaaaaa')
        self.assertEqual(
            login_state.pick_sid(candidates, preferred='BBBbbbbbbbbbbbbbbb'),
            'BBBbbbbbbbbbbbbbbb',
        )

    def test_build_config_updates_fields(self):
        base = login_state.load_base_config()
        cfg = login_state.build_config(
            uid=12345678,
            gid='abc123',
            session=10000,
            sid='session1234567890',
            smid='smid123',
            devi='devi123',
            cv='IK9.9.05_Android',
            aid='aid123',
            base=base,
        )
        bus = cfg['auth']['bus_buf']
        self.assertEqual(cfg['uid'], 12345678)
        self.assertEqual(cfg['gid'], 'abc123')
        self.assertEqual(bus['uid'], '12345678')
        self.assertEqual(bus['sid'], 'session1234567890')
        self.assertTrue(bus['source_info'])
        self.assertTrue(bus['clientId'])

    def test_save_login_state(self):
        cfg = login_state.load_base_config()
        result = {'config': cfg}
        with tempfile.TemporaryDirectory() as d:
            path = login_state.save_login_state(result, Path(d) / 'local.json')
            self.assertTrue(Path(path).exists())


if __name__ == '__main__':
    unittest.main()
