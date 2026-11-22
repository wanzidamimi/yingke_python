import gzip
import sys

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PATH = sys.argv[1]
KEY = '0c2a616bfd8442aec0495d04d3ae3599'

for s, d, p in payloads(PATH):
    if s == 1300 or len(p) < 30 or p[4:6] != bytes.fromhex('0100'):
        continue
    n = int.from_bytes(p[18:22], 'big')
    body = p[22:22+n]
    print('SUB PACKET', len(p), 'body', n, body.hex())
    dec = rc4(body, KEY)
    print('RC4 HEX', dec.hex())
    print('RC4 RAW', dec[:500])
    try:
        print('GZIP', gzip.decompress(dec)[:1000])
    except Exception as e:
        print('GZIP ERR', e)
    print('EXT', p[22+n:].hex())
