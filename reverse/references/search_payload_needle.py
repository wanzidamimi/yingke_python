import gzip
import sys
import zlib

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

PATH = sys.argv[1]
NEEDLE = sys.argv[2].encode()
PORTS = [int(x) for x in sys.argv[3:]] or [1300]
KEYS = ['0c2a616bfd8442aec0495d04d3ae3599', 'ehebecee', 'dbebdhgd']

for port in PORTS:
    ps = payloads(PATH, port)
    print('PORT', port, 'payloads', len(ps))
    hits = 0
    for idx, (s, d, p) in enumerate(ps):
        variants = [('raw', p)]
        for k in KEYS:
            variants.append(('rc4:' + k, rc4(p, k)))
        for name, data in list(variants):
            for dec_name, fn in [
                ('gzip', gzip.decompress),
                ('zlib', zlib.decompress),
                ('deflate', lambda x: zlib.decompress(x, -15)),
            ]:
                try:
                    variants.append((name + '/' + dec_name, fn(data)))
                except Exception:
                    pass
        for name, data in variants:
            if NEEDLE in data:
                hits += 1
                print('HIT', idx, s, d, name, len(data), data[:1000])
                break
    print('hits', hits)
