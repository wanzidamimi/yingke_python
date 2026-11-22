import gzip
import sys

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

PATH = sys.argv[1]
KEY = '0c2a616bfd8442aec0495d04d3ae3599'
NONCE = 'dbebdhgd'
NEEDLES = ['来啦', '蝉鸣半夏', 'chat', 's.m', '弹幕']

def scan(tag, data):
    if not data:
        return
    text = None
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        text = data.decode('utf-8', 'ignore')
    for n in NEEDLES:
        if n in text:
            print('HIT', tag, n, text[:1000])
            return True
    return False

for s, d, p in payloads(PATH):
    if s != 1300 or len(p) < 26:
        continue
    body_len = int.from_bytes(p[18:22], 'big')
    body = p[22:22 + body_len]
    variants = [('raw', body), ('rc4key', rc4(body, KEY)), ('rc4nonce', rc4(body, NONCE))]
    for name, data in variants:
        scan(name, data)
        for dec_name, fn in [('gzip', gzip.decompress)]:
            try:
                out = fn(data)
                scan(name + '/' + dec_name, out)
            except Exception:
                pass
print('done')
