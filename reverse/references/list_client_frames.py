import gzip
import sys

from app_tcp_client import build_subscribe_body, rc4
from reassemble_tcp_frames import parse_frames, reassemble

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PATH = sys.argv[1]
KEY = '0c2a616bfd8442aec0495d04d3ae3599'

for key, stream in reassemble(PATH):
    if 1300 not in (key[1], key[3]):
        continue
    direction = 'S->C' if key[1] == 1300 else 'C->S'
    frames, _ = parse_frames(stream)
    for frame in frames:
        cmd = frame[4:6].hex()
        n = int.from_bytes(frame[18:22], 'big')
        body = frame[22:22+n]
        if direction != 'C->S' or cmd not in ('0100', '4004', '0004'):
            continue
        print('FRAME', direction, 'cmd', cmd, 'len', len(frame), 'body', n, body[:80].hex())
        if cmd == '0100':
            dec = rc4(body, KEY)
            print('  RC4', dec.hex())
            print('  RAW', dec[:300])
            try:
                print('  GZIP', gzip.decompress(dec)[:300])
            except Exception:
                pass
