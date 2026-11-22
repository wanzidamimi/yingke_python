import gzip
import sys

from app_tcp_client import parse_packet, rc4
from parse_pktmon_pcap import payloads

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PATH = sys.argv[1]
KEY = sys.argv[2] if len(sys.argv) > 2 else '0c2a616bfd8442aec0495d04d3ae3599'

for s, d, p in payloads(PATH):
    if s != 1300 and len(p) > 22 and p[4:6] == bytes.fromhex('4004'):
        q = parse_packet(p)
        print('HEADER', {k: v for k, v in q.items() if k not in ('body', 'ext')})
        print('BODYLEN', len(q['body']), 'EXTLEN', len(q['ext']))
        print('EXT', q['ext'])
        for name, data in [
            ('raw', q['body']),
            ('rc4', rc4(q['body'], KEY)),
        ]:
            print(name, data[:400].hex())
            try:
                print(name, 'gzip', gzip.decompress(data)[:3000].decode('utf-8', 'replace'))
            except Exception as e:
                print(name, 'gzip err', e)
            try:
                print(name, 'text', data.decode('utf-8', 'replace')[:3000])
            except Exception:
                pass
        break
