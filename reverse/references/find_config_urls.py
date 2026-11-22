import json
import re
import sys

path = sys.argv[1]
text = open(path, 'rb').read().decode('utf-8', 'ignore')
try:
    obj = json.loads(text)
except Exception:
    obj = None

if obj:
    def walk(x):
        if isinstance(x, dict):
            k = str(x.get('key', ''))
            u = x.get('url') or x.get('uri') or x.get('host')
            if u and any(s in k.lower() for s in ('chat', 'message', 'im', 'live', 'play')):
                print(k, u)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
else:
    for m in re.finditer(r'"key":"([^"]+)","url":"([^"]+)"', text):
        if any(s in m.group(1).lower() for s in ('chat', 'message', 'im', 'live', 'play')):
            print(m.group(1), m.group(2))
