import gzip
import json
import os
import sys

from app_tcp_client import parse_packet, rc4
from parse_pktmon_pcap import payloads

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
AUTH_PCAP = r'd:/Scrapy-project/yingke_python/reverse/logs/inke_room2.pcapng'
ROOM_PCAP = r'd:/Scrapy-project/yingke_python/reverse/logs/danmu_long.pcapng'
OUT = r'd:/Scrapy-project/yingke_python/reverse/references/inke_runtime_config.json'
KEY = '0c2a616bfd8442aec0495d04d3ae3599'


def client_frame(path, cmd):
    for s, d, p in payloads(path):
        if s == 1300 or len(p) < 22 or p[4:6] != cmd:
            continue
        q = parse_packet(p)
        return q
    return None


auth = client_frame(AUTH_PCAP, bytes.fromhex('4004'))
enter = client_frame(ROOM_PCAP, bytes.fromhex('0002'))
auth_obj = json.loads(rc4(auth['body'], KEY).decode('utf-8'))
enter_obj = json.loads(rc4(enter['body'], KEY).decode('utf-8'))

# pass-through 已在实测中确认不是进房必要条件，避免把旧房间卡片信息带入新配置。
try:
    enter_obj['bus_buf']['b'].pop('pass-through', None)
except Exception:
    pass

cfg = {
    'uid': auth_obj.get('uid'),
    'gid': auth_obj.get('gid'),
    'session': 10000,
    'auth': auth_obj,
    'enter_room': enter_obj,
}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print('saved', OUT, os.path.getsize(OUT))
print('uid', cfg['uid'], 'gid', cfg['gid'])
