import base64
import hashlib
import hmac
import itertools
import re

LOG = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_requests_detail.log'
SECRETS = [
    b'1ba5fb066d7e33d5',
    '1ba5fb066d7e33d5'.encode(),
]
APPID = 'OklL'
PKG = 'com.meelive.ingkee'

for line in open(LOG, encoding='utf-8', errors='replace'):
    if 'sign_from=android' in line and 'Authorization' in line and 'serviceinfo.inke.cn/serviceinfo/info?' in line:
        url = re.search(r'REQ GET (\S+)', line).group(1)
        auth = re.search(r"'Authorization': 'InkeV1 OklL:([^']+)'", line).group(1)
        ts = re.search(r"'Client-TimeStamp': '(\d+)'", line).group(1)
        break

query = url.split('?', 1)[1]
full = url
pathq = url.split('https://serviceinfo.inke.cn', 1)[1]

parts_options = {
    'pkg': [PKG, ''],
    'body': ['', '\n'],
    'ts': [ts, ts.upper()],
    'q': [query, '?' + query, pathq, pathq.lstrip('/')],
    'method': ['', 'GET', 'get'],
    'appid': [APPID, ''],
    'secret': ['', '1ba5fb066d7e33d5'],
    'sep': ['\n', '&', ''],
}

for secret in SECRETS:
    for vals in itertools.product(*parts_options.values()):
        d = dict(zip(parts_options.keys(), vals))
        sep = d['sep']
        elems = [d['pkg'], d['body'], d['ts'], d['q'], d['method'], d['appid'], d['secret']]
        msg = sep.join(x for x in elems if x != '')
        sig = base64.b64encode(hmac.new(secret, msg.encode(), hashlib.sha1).digest()).decode()
        if sig == auth:
            print('MATCH')
            print('secret', secret)
            print('msg', repr(msg))
            raise SystemExit
print('no match')
