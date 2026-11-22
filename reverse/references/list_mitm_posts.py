import json

PATH = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_auth_flows.jsonl'
rows = []
for line in open(PATH, encoding='utf-8-sig', errors='replace'):
    if not line.strip():
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    if r['method'] == 'POST' or r['body_len'] > 0:
        rows.append(r)
print('post_or_body_flows=%d' % len(rows))
for r in rows[-80:]:
    print('%-6s %-45s len=%-6d %s' % (
        r['method'], (r['host'] + r['path'])[:45], r['body_len'],
        r['body_hex'][:80]
    ))
