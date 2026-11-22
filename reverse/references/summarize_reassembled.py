import gzip
import json
import sys

from app_tcp_client import rc4
from reassemble_tcp_frames import reassemble, parse_frames

PATH = sys.argv[1]
KEY = '0c2a616bfd8442aec0495d04d3ae3599'


def texts(body):
    out = []
    if body[:2] == b'\x1f\x8b':
        try:
            out.append(('gzip', gzip.decompress(body).decode('utf-8')))
        except Exception:
            pass
    dec = rc4(body, KEY)
    out.append(('rc4', dec.decode('utf-8', 'replace')))
    try:
        out.append(('rc4/gzip', gzip.decompress(dec).decode('utf-8')))
    except Exception:
        pass
    return out


for key, stream in reassemble(PATH):
    if 1300 not in (key[1], key[3]):
        continue
    direction = 'C->S' if key[1] == 1300 else 'S->C'
    frames, _ = parse_frames(stream)
    for frame in frames:
        blen = int.from_bytes(frame[18:22], 'big')
        cmd = frame[4:6].hex()
        for name, text in texts(frame[22:22 + blen]):
            try:
                obj = json.loads(text)
            except Exception:
                continue
            items = []
            if isinstance(obj.get('bus_buf'), list):
                items.extend(obj['bus_buf'])
            elif isinstance(obj.get('bus_buf'), dict):
                items.append(obj['bus_buf'])
            elif 'ms' in obj:
                items.append(obj)
            for item in items:
                if not isinstance(item, dict):
                    continue
                ms = item.get('ms', [])
                if isinstance(ms, dict):
                    ms = [ms]
                for m in ms:
                    if not isinstance(m, dict):
                        continue
                    c = m.get('c', '')
                    tp = m.get('tp', '')
                    if not c and not tp:
                        continue
                    frm = m.get('from') or {}
                    nic = frm.get('nic') if isinstance(frm, dict) else ''
                    print('%s cmd=%s tp=%s msg_type=%s nic=%s c=%s' % (
                        direction, cmd, tp, m.get('msg_type'), nic, str(c)[:120]
                    ))
            break
