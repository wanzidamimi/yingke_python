import gzip
import json
import sys

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PATH = sys.argv[1]
TARGET = sys.argv[2] if len(sys.argv) > 2 else 'float_public_chat_v2'
KEY = '0c2a616bfd8442aec0495d04d3ae3599'


def body_of(p):
    n = int.from_bytes(p[18:22], 'big')
    return p[22:22 + n]


for s, d, p in payloads(PATH):
    if s != 1300 or len(p) < 26:
        continue
    body = body_of(p)
    if not body:
        continue
    variants = []
    if body[:2] == b'\x1f\x8b':
        variants.append(body)
    else:
        variants.append(rc4(body, KEY))
    for data in variants:
        try:
            obj = json.loads(gzip.decompress(data).decode('utf-8'))
        except Exception:
            continue
        items = list(obj.get('ms', []))
        if isinstance(obj.get('bus_buf'), list):
            for inner in obj['bus_buf']:
                if isinstance(inner, dict):
                    items.extend(inner.get('ms', []))
        for item in items:
            if TARGET in str(item.get('tp', '')) or TARGET in json.dumps(item, ensure_ascii=False):
                print(json.dumps(obj, ensure_ascii=False, indent=2))
                raise SystemExit
print('not found')
