import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import app as app_module
import login_state


class LoginApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_module.app)

    def test_login_status(self):
        old = login_state.check_environment
        login_state.check_environment = lambda: {
            'ok': True, 'adb': True, 'device': True, 'root': True,
            'app_installed': True, 'local_config': False, 'error': '',
        }
        app_module.check_environment = login_state.check_environment
        try:
            r = self.client.get('/api/login/status')
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.json()['ok'])
        finally:
            login_state.check_environment = old
            app_module.check_environment = old

    def test_login_sync_failure(self):
        old = login_state.read_login_state
        login_state.read_login_state = lambda **kwargs: {'ok': False, 'error': 'no root'}
        app_module.read_login_state = login_state.read_login_state
        try:
            r = self.client.post('/api/login/sync', json={})
            self.assertEqual(r.status_code, 200)
            self.assertFalse(r.json()['ok'])
            self.assertEqual(r.json()['error'], 'no root')
        finally:
            login_state.read_login_state = old
            app_module.read_login_state = old

    def test_login_sync_success(self):
        cfg = login_state.load_base_config()
        result = {
            'ok': True,
            'config': cfg,
            'masked': {'uid': 1, 'sid': 'ab***cd'},
            'sid_candidate_count': 2,
        }
        old_read = login_state.read_login_state
        old_save = login_state.save_login_state
        login_state.read_login_state = lambda **kwargs: result
        login_state.save_login_state = lambda r: 'D:/tmp/local.json'
        app_module.read_login_state = login_state.read_login_state
        app_module.save_login_state = login_state.save_login_state
        try:
            r = self.client.post('/api/login/sync', json={})
            data = r.json()
            self.assertEqual(r.status_code, 200)
            self.assertTrue(data['ok'])
            self.assertEqual(data['masked']['sid'], 'ab***cd')
        finally:
            login_state.read_login_state = old_read
            login_state.save_login_state = old_save
            app_module.read_login_state = old_read
            app_module.save_login_state = old_save


if __name__ == '__main__':
    unittest.main()
