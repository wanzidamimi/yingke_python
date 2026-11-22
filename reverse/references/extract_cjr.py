import gzip
import json
import sys

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

PATH = sys.argv[1]
KEY = '0c2a616bfd8442aec0495d04d3ae3599'

for s, d, p in payloads(PATH):
    if s != 1300 or len(p) < 26 or p[4:6] != bytes.fromhex('0002'):
        continue
    n = int.from_bytes(p[18:22], 'big')
    body = p[22:22 + n]
    try:
        text = gzip.decompress(rc4(body, KEY)).decode('utf-8')
    except Exception:
        continue
    try:
        obj = json.loads(text)
    except Exception:
        continue
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:12000])
    break
