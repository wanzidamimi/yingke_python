import json
import time

from mitmproxy import http

OUT = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_auth_flows.jsonl'


def request(flow: http.HTTPFlow):
    req = flow.request
    rec = {
        'ts': time.time(),
        'method': req.method,
        'url': req.pretty_url,
        'host': req.host,
        'path': req.path,
        'query': req.pretty_url.split('?', 1)[1] if '?' in req.pretty_url else '',
        'headers': dict(req.headers),
        'body_len': len(req.content),
        'body_hex': req.content[:256].hex(),
    }
    with open(OUT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    auth = req.headers.get('Authorization')
    if auth:
        print('AUTH %s %s %s %s' % (
            rec['ts'], req.method, req.pretty_url[:180], auth
        ), flush=True)
