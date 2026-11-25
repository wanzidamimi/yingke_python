import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reverse" / "references"))

from app_tcp_client import parse_packet
from inke_tcp_collector import build_auth_packet, build_room_packets


class AuthUidTest(unittest.TestCase):
    def test_auth_ext_uses_config_uid(self):
        cfg = {
            "uid": 778965813,
            "gid": "abc",
            "auth": {"uid": 778965813, "bus_buf": {"uid": "778965813", "gid": "abc"}},
            "enter_room": {"uid": 778965813, "bus_buf": {"b": {"ev": "c.jr"}, "gid": "abc"}},
        }
        packet = build_auth_packet("testkey", cfg)
        q = parse_packet(packet)
        self.assertEqual(json.loads(q["ext"].decode())["long-uid"], 778965813)

    def test_room_ext_uses_config_uid(self):
        cfg = {
            "uid": 778965813,
            "gid": "abc",
            "auth": {"uid": 778965813, "bus_buf": {"uid": "778965813", "gid": "abc"}},
            "enter_room": {
                "uid": 778965813,
                "bus_buf": {"b": {"ev": "c.jr"}, "gid": "abc", "rid": "0", "liveid": "0"},
            },
        }
        packets = build_room_packets("1795437498494586", "testkey", cfg)
        self.assertEqual(len(packets), 3)
        for packet in packets:
            q = parse_packet(packet)
            self.assertEqual(json.loads(q["ext"].decode())["long-uid"], 778965813)


if __name__ == "__main__":
    unittest.main()
