import gzip
import sys
import zlib

from parse_pktmon_pcap import payloads

PATH = sys.argv[1]
PORTS = [int(x) for x in sys.argv[2:]] if len(sys.argv) > 2 else [80]
NEEDLES = [x.encode('utf-8') for x in ['来啦', '来啦来啦', 'chat', '弹幕']]

for port in PORTS:
    ps = payloads(PATH, port)
    print('PORT', port, 'payloads', len(ps))
    for s, d, p in ps:
        variants = [('raw', p)]
        for name, fn in [
            ('gzip', gzip.decompress),
            ('zlib', zlib.decompress),
            ('deflate', lambda x: zlib.decompress(x, -15)),
        ]:
            try:
                variants.append((name, fn(p)))
            except Exception:
                pass
        for name, data in variants:
            for needle in NEEDLES:
                if needle in data:
                    print('HIT', port, name, needle, data[:500])
                    break
print('done')
