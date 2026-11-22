import hashlib
import os
import time

OUT_DIR = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_bodies'
LOG_PATH = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_requests_detail.log'


def _log(line):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'a', encoding='utf-8', errors='replace') as f:
        f.write(line + '\n')
    print(line, flush=True)


def request(flow):
    url = flow.request.pretty_url
    if 'inke' not in url:
        return
    _log('REQ %s %s headers=%s body_len=%d' % (
        flow.request.method, url[:800],
        dict(flow.request.headers), len(flow.request.content)
    ))


def response(flow):
    url = flow.request.pretty_url
    if 'inke' not in url:
        return
    content = flow.response.content or b''
    _log('RESP %s status=%s len=%d type=%s url=%s' % (
        flow.request.method, flow.response.status_code, len(content),
        flow.response.headers.get('Content-Type'), url[:800]
    ))
    if len(content) < 100:
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    key = hashlib.md5(url.encode('utf-8')).hexdigest()[:12]
    name = '%s_%s_%s.bin' % (int(time.time() * 1000), key, flow.response.status_code)
    path = os.path.join(OUT_DIR, name)
    with open(path, 'wb') as f:
        f.write(content)
    _log('SAVED %s len=%d' % (path, len(content)))
