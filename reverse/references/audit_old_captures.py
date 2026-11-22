import glob
import gzip
import hashlib
import json
import os
import re
import sys

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

KEY = '0c2a616bfd8442aec0495d04d3ae3599'
CN = re.compile(r'[\u4e00-\u9fff]{2,}')

FILES = [
    r'd:/Scrapy-project/yingke_python/reverse/logs/inke1300_raw.pcapng',
    r'd:/Scrapy-project/yingke_python/reverse/logs/inke_room2.pcapng',
    r'd:/Scrapy-project/yingke_python/reverse/logs/hotroom3.pcapng',
    r'd:/Scrapy-project/yingke_python/reverse/logs/hotboth2.pcapng',
    r'd:/Scrapy-project/yingke_python/reverse/logs/danmu_long.pcapng',
    r'd:/Scrapy-project/yingke_python/reverse/logs/danmu_1300_now.pcapng',
    r'd:/Scrapy-project/yingke_python/reverse/logs/danmu_1300_relaunch.pcapng',
]


def body_of(p):
    if len(p) < 22:
        return b''
    n = int.from_bytes(p[18:22], 'big')
    return p[22:22 + n]


def text_variants(body):
    out = []
    for name, data in [('raw', body), ('rc4', rc4(body, KEY))]:
        out.append((name, data))
        for dec, fn in [('gzip', gzip.decompress)]:
            try:
                out.append((name + '/' + dec, fn(data)))
            except Exception:
                pass
    return out


for path in FILES:
    if not os.path.exists(path):
        print('MISSING', os.path.basename(path))
        continue
    raw = open(path, 'rb').read()
    raw_cn = len(CN.findall(raw.decode('utf-8', 'ignore')))
    print('\nFILE', os.path.basename(path), 'size', len(raw), 'raw_cn_hits', raw_cn)
    seen = set()
    examples = []
    for s, d, p in payloads(path):
        if s != 1300 or len(p) < 26 or p[4:6] not in (
            bytes.fromhex(x) for x in ('b002', 'b001', '0002', '0015')
        ):
            continue
        body = body_of(p)
        for name, data in text_variants(body):
            try:
                text = data.decode('utf-8')
            except Exception:
                continue
            words = CN.findall(text)
            if not words:
                continue
            key = hashlib.md5(text.encode()).hexdigest()
            if key in seen:
                continue
            seen.add(key)
            examples.append((p[4:6].hex(), name, words[:8], text[:350]))
            if len(examples) >= 8:
                break
        if len(examples) >= 8:
            break
    print('decompressed_cn_messages', len(examples))
    for cmd, name, words, text in examples:
        print('  cmd=%s via=%s words=%s' % (cmd, name, words))
        print('    %s' % text.replace('\n', ' ')[:300])
