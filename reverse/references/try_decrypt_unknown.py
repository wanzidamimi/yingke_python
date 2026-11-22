import gzip
import sys
import zlib

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

PATH = sys.argv[1]
CMDS = {'06a4', 'a36c', 'f7aa', 'df47', '70ce', '3b9a', 'd1b3'}
KEYS = [
    '0c2a616bfd8442aec0495d04d3ae3599',
    'ehebecee',
    'dbebdhgd',
    'ee16515f4f38d16a67083557e8ff0a71',
]
NEEDLES = [b'chat', b'"tp"', '来啦'.encode(), b's.m', b'barrage', b'danmu']

def check(tag, data):
    if not data:
        return False
    hit = [n for n in NEEDLES if n in data]
    if hit:
        print('HIT', tag, hit, data[:500])
        return True
    return False

for s, d, p in payloads(PATH):
    if s != 1300 or len(p) < 26:
        continue
    cmd = p[4:6].hex()
    if cmd not in CMDS:
        continue
    body_len = int.from_bytes(p[18:22], 'big')
    body = p[22:22 + body_len]
    print('CMD', cmd, 'len', len(body), 'prefix', body[:16].hex())
    for name, data in [('raw', body)] + [('rc4:' + k, rc4(body, k)) for k in KEYS]:
        check(name, data)
        for dec_name, fn in [
            ('gzip', gzip.decompress),
            ('zlib', zlib.decompress),
            ('raw_deflate', lambda x: zlib.decompress(x, -15)),
        ]:
            try:
                out = fn(data)
                print('  DECOMPRESSED', name, dec_name, out[:200])
                check(name + '/' + dec_name, out)
            except Exception:
                pass
