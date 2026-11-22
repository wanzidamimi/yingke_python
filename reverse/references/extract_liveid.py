import gzip
import re
import sys

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

PATH = sys.argv[1]
KEY = '0c2a616bfd8442aec0495d04d3ae3599'
pat = re.compile(rb'"liveid":"(1[0-9]{15,})"')

seen = set()
for s, d, p in payloads(PATH):
    if s != 1300 or len(p) < 26:
        continue
    n = int.from_bytes(p[18:22], 'big')
    body = p[22:22 + n]
    for data in (body, rc4(body, KEY)):
        try:
            text = gzip.decompress(data)
        except Exception:
            continue
        for m in pat.finditer(text):
            v = m.group(1).decode()
            if v not in seen:
                seen.add(v)
                print(v)
print('count', len(seen))
