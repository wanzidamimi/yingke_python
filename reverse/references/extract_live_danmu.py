"""从 pktmon pcapng / tcpdump pcap 中提取映客直播间弹幕。

关键点：必须先按 TCP 流重组，再解析私有帧；单包解析会漏掉跨 TCP 段的 gzip/RC4 body。
"""
import gzip
import json
import sys

from app_tcp_client import rc4
from reassemble_tcp_frames import reassemble, parse_frames

KEY = '0c2a616bfd8442aec0495d04d3ae3599'
CHAT_TP = {'pub', 'pp', 'chat'}


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


def iter_items(obj):
    if not isinstance(obj, dict):
        return []
    bus = obj.get('bus_buf')
    if isinstance(bus, list):
        return bus
    if isinstance(bus, dict):
        return [bus]
    if 'ms' in obj:
        return [obj]
    return []


def main():
    for path in sys.argv[1:]:
        print('FILE', path)
        count = 0
        for key, stream in reassemble(path):
            if 1300 not in (key[1], key[3]):
                continue
            direction = 'S->C' if key[1] == 1300 else 'C->S'
            frames, _ = parse_frames(stream)
            for frame in frames:
                blen = int.from_bytes(frame[18:22], 'big')
                cmd = frame[4:6].hex()
                for via, text in decoded(frame[22:22 + blen]):
                    try:
                        obj = json.loads(text)
                    except Exception:
                        continue
                    for item in iter_items(obj):
                        ms = item.get('ms', [])
                        if isinstance(ms, dict):
                            ms = [ms]
                        for m in ms:
                            if not isinstance(m, dict):
                                continue
                            tp = m.get('tp')
                            if tp not in CHAT_TP:
                                continue
                            c = m.get('c')
                            if not c:
                                continue
                            frm = m.get('from') or {}
                            nic = frm.get('nic') if isinstance(frm, dict) else ''
                            uid = frm.get('id') if isinstance(frm, dict) else obj.get('uid')
                            count += 1
                            print('%s cmd=%s tp=%s msg_type=%s uid=%s nick=%s via=%s c=%s' % (
                                direction, cmd, tp, m.get('msg_type'), uid, nic, via,
                                str(c).replace('\n', '\\n')
                            ))
                    break
        print('TOTAL', count)


if __name__ == '__main__':
    main()
