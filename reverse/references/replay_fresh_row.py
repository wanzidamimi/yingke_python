import json
import sys

from curl_cffi import requests

PATH = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_auth_flows.jsonl'
needle = sys.argv[1] if len(sys.argv) > 1 else '/api/v2/feed/get_update_num'
override_path = sys.argv[2] if len(sys.argv) > 2 else None

row = None
for line in open(PATH, encoding='utf-8-sig', errors='replace'):
    if not line.strip():
        continue
    r = json.loads(line)
    if needle in r.get('path', ''):
        row = r
        break
if not row:
    print('row not found')
    sys.exit(1)

new_path = row['path']
if override_path:
    new_path = override_path + (('?' + row['query']) if row['query'] else '')
url = 'https://' + row['host'] + new_path
headers = dict(row['headers'])
headers.pop('content-length', None)
headers.pop('Content-Length', None)
print('url', url[:300])
print('auth', headers.get('Authorization'))
resp = requests.request(
    row['method'], url, headers=headers, data=bytes.fromhex(row['body_hex']),
    impersonate='chrome', timeout=20
)
print('status', resp.status_code, 'len', len(resp.content))
print(resp.text[:1500])
