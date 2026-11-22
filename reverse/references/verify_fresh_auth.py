import base64
import hashlib
import hmac
import json
import sys

PATH = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_auth_flows.jsonl'
PKG = 'com.meelive.ingkee'
APPID = 'OklL'
SECRET = b'1ba5fb066d7e33d5'

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

rows = []
for line in open(PATH, encoding='utf-8', errors='replace'):
    if not line.strip():
        continue
    try:
        rows.append(json.loads(line))
    except Exception:
        pass

print('rows=%d' % len(rows))
for r in rows:
    headers = {k.lower(): v for k, v in r['headers'].items()}
    auth = headers.get('authorization')
    ts = headers.get('client-timestamp')
    if not auth or not ts or not auth.startswith('InkeV1 OklL:'):
        continue
    query = r.get('query', '')
    body = bytes.fromhex(r.get('body_hex', ''))
    if body:
        body_md5 = base64.b64encode(hashlib.md5(body).digest()).decode()
    else:
        body_md5 = ''
    msg = '%s\n%s\n%s\n%s\n%s' % (
        PKG, body_md5, r['method'].upper(), ts, query
    )
    sig = base64.b64encode(hmac.new(SECRET, msg.encode(), hashlib.sha1).digest()).decode()
    expected = auth.split(':', 1)[1]
    ok = sig == expected
    print('%s %s query_len=%d body_len=%d match=%s' % (
        r['method'], r['host'] + r['path'], len(query), r['body_len'], ok
    ))
    if not ok:
        print('  ts=%s' % ts)
        print('  expected=%s' % expected)
        print('  actual  =%s' % sig)
        print('  msg=%r' % msg[:500])
    if ok:
        print('MATCH_FOUND', json.dumps(r, ensure_ascii=False)[:2000])
        break
