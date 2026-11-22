import gzip
import sys

from app_tcp_client import rc4
from reassemble_tcp_frames import parse_frames, reassemble

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PATH = sys.argv[1]
KEY = '0c2a616bfd8442aec0495d04d3ae3599'

for key, stream in reassemble(PATH):
    if 1300 not in (key[1], key[3]) or key[1] == 1300:
        continue
    for frame in parse_frames(stream)[0]:
        cmd = frame[4:6].hex()
        if cmd not in ('0002', '4c04', '4020'):
            continue
        n = int.from_bytes(frame[18:22], 'big')
        body = frame[22:22+n]
        ext = frame[22+n:]
        print('CMD', cmd, 'HEADER', frame[:22].hex())
        print(' BODY_HEX', body[:200].hex())
        dec = rc4(body, KEY)
        print(' BODY_RC4_HEX', dec[:300].hex())
        print(' BODY_RC4', dec[:500].decode('utf-8', 'replace'))
        try:
            print(' BODY_GZIP', gzip.decompress(dec)[:500].decode('utf-8', 'replace'))
        except Exception:
            pass
        print(' EXT', ext[:500].decode('utf-8', 'replace'))
