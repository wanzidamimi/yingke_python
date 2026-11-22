import json
import sys

PATH = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_auth_flows.jsonl'
needle = sys.argv[1] if len(sys.argv) > 1 else '12345678'
raw = needle.encode()

rows = []
total = 0
for line in open(PATH, encoding='utf-8-sig', errors='replace'):
    if not line.strip():
        continue
    total += 1
    try:
        r = json.loads(line)
    except Exception:
        continue
    blob = json.dumps(r, ensure_ascii=False)
    body = bytes.fromhex(r.get('body_hex', ''))
    text = (r.get('url', '') + r.get('query', '')).encode('utf-8', 'replace')
    if needle in blob or raw in body or raw in text:
        rows.append(r)

print('flows=%d hits=%d' % (total, len(rows)))
for r in rows[:20]:
    print('METHOD', r['method'])
    print('URL', r['url'][:600])
    print('HEADERS', {k: v for k, v in r['headers'].items() if k.lower() in ('authorization', 'client-timestamp', 'content-type', 'host')})
    print('BODY_LEN', r['body_len'])
    print('BODY_HEX', r['body_hex'][:600])
    print()
