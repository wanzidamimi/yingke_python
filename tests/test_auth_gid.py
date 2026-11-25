import gzip
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reverse" / "references"))

from app_tcp_client import build_packet, rc4


class AuthGidTest(unittest.TestCase):
    def test_decode_auth_response(self):
        from inke_tcp_collector import decode_body

        key = "testkey"
        obj = {"bus_buf": [{"gid": "abc123", "retcode": 0}]}
        body = rc4(gzip.compress(json.dumps(obj, separators=(",", ":")).encode()), key)
        packet = build_packet(0x4004, body, 0, 0, 10000, msg_id=5)
        plain = decode_body(0x4004, packet[22:22 + len(body)], key)
        self.assertEqual(json.loads(plain.decode()), obj)

    def test_extract_gid(self):
        from inke_tcp_collector import extract_gid_from_auth

        obj = {"bus_buf": [{"gid": "abc123", "retcode": 0}]}
        self.assertEqual(extract_gid_from_auth(obj), "abc123")
        self.assertEqual(extract_gid_from_auth({"bus_buf": [{"retcode": 1}]}), "")


if __name__ == "__main__":
    unittest.main()
