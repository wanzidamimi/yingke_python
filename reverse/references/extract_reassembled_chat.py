import gzip
import json
import re
import sys

from app_tcp_client import rc4
from reassemble_tcp_frames import reassemble, parse_frames

PATH = sys.argv[1]
KEY = '0c2a616bfd8442aec0495d04d3ae3599'


def decoded(body):
    out = []
    if body[:2] == b'\x1f\x8b':
        try:
            out.append(('gzip', gzip.decompress(body).decode('utf-8')))
        except Exception:
            pass
    d = rc4(body, KEY)
    out.append(('rc4', d.decode('utf-8', 'replace')))
    try:
        out.append(('rc4/gzip', gzip.decompress(d).decode('utf-8')))
    except Exception:
        pass
    return out


for key, stream in reassemble(PATH):
    if 1300 not in (key[1], key[3]):
        continue
    frames, _ = parse_frames(stream)
    for frame in frames:
        blen = int.from_bytes(frame[18:22], 'big')
        body = frame[22:22 + blen]
        cmd = frame[4:6].hex()
        for name, text in decoded(body):
            if '"tp":"pub"' in text or '"tp": "pub"' in text or '"c":"来啦来啦' in text:
                print('UPSTREAM', key, 'cmd', cmd, 'via', name)
                try:
                    print(json.dumps(json.loads(text), ensure_ascii=False, indent=2)[:6000])
                except Exception:
                    print(text[:6000])
            for m in re.finditer(r'"tp"\s*:\s*"([^"]+)"', text):
                if m.group(1) in ('chat', 'pp', 'pub'):
                    print('TP', key, 'cmd', cmd, 'via', name, m.group(1))
                    print(text[:4000])
                    break
