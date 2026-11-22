import os
import re

DIR = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_bodies'
seen = {}
pat = re.compile(r'\{"key":"(MESSAGE_V2_[A-Z_0-9]+)","url":"([^"]+)"')

for name in os.listdir(DIR):
    path = os.path.join(DIR, name)
    try:
        text = open(path, 'rb').read().decode('utf-8', 'ignore')
    except Exception:
        continue
    for m in pat.finditer(text):
        seen[m.group(1)] = m.group(2)

for key in sorted(seen):
    print('%s %s' % (key, seen[key]))
