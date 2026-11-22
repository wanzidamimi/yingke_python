import json
import os

PATH = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_auth_flows.jsonl'

for line in open(PATH, encoding='utf-8-sig', errors='replace'):
    if not line.strip():
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    url = r.get('url', '')
    if '/v2/message' not in url and 'MESSAGE_V2' not in url:
        continue
    print('====', r.get('method'), r.get('host'), r.get('path')[:180])
    print('URL_LEN', len(url), 'QUERY_LEN', len(r.get('query', '')))
    print('HEADERS', {k: v for k, v in r.get('headers', {}).items() if k.lower() in ('authorization', 'client-timestamp', 'content-type', 'content-encoding')})
    body = bytes.fromhex(r.get('body_hex', ''))
    print('BODY_LEN', r.get('body_len'), 'BODY_PREFIX', body[:200])
