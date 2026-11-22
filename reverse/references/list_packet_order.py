import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from parse_pktmon_pcap import payloads

PATH = sys.argv[1]
for i, (s, d, p) in enumerate(payloads(PATH)):
    if len(p) < 22:
        continue
    if 1300 not in (s, d):
        continue
    cmd = p[4:6].hex()
    side = 'C->S' if s != 1300 else 'S->C'
    n = int.from_bytes(p[18:22], 'big') if len(p) >= 22 else 0
    print('%04d %s cmd=%s len=%d bodylen=%d' % (i, side, cmd, len(p), n))
