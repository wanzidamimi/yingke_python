import os
import re

LOG = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_requests_detail.log'

last_url = None
for line in open(LOG, encoding='utf-8', errors='replace'):
    if line.startswith('RESP '):
        m = re.search(r'url=(\S+)', line)
        last_url = m.group(1) if m else None
    elif line.startswith('SAVED ') and last_url:
        m = re.search(r'SAVED (\S+) len=(\d+)', line)
        if not m:
            continue
        path, size = m.group(1), m.group(2)
        try:
            head = open(path, 'rb').read(24).hex()
        except Exception:
            head = ''
        from urllib.parse import urlparse
        u = urlparse(last_url)
        print('%-55s %-8s %s' % (u.path, size, head))
