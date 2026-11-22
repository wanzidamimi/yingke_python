import sys
from reassemble_tcp_frames import pcapng_packets, ip_tcp

path = sys.argv[1]
data = open(path, 'rb').read()
streams = {}
for packet, linktype in pcapng_packets(data):
    parsed = ip_tcp(packet, linktype)
    if not parsed:
        continue
    src, sport, dst, dport, seq, payload = parsed
    if 1300 not in (sport, dport):
        continue
    key = (src, sport, dst, dport)
    streams.setdefault(key, []).append((seq, len(payload)))

for key, segs in streams.items():
    seqs = [x[0] for x in segs]
    print('STREAM', key, 'segments', len(segs), 'min', min(seqs), 'max', max(seqs), 'bytes', sum(x[1] for x in segs))
    print(' first 10', segs[:10])
