import base64
import hashlib
import hmac
import itertools
import os
import re
import sys

LOG = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_requests_detail.log'
SMALI_ROOT = r'd:/Scrapy-project/yingke_python/reverse/smali_out'
APPID = 'OklL'
PKG = 'com.meelive.ingkee'

sample = None
for line in open(LOG, encoding='utf-8', errors='replace'):
    if 'sign_from=android' in line and 'Authorization' in line and 'serviceinfo.inke.cn/serviceinfo/info?' in line:
        url = re.search(r'REQ GET (\S+)', line).group(1)
        auth = re.search(r"'Authorization': 'InkeV1 OklL:([^']+)'", line).group(1)
        ts = re.search(r"'Client-TimeStamp': '(\d+)'", line).group(1)
        sample = (url, auth, ts)
        break
if not sample:
    print('no sample')
    sys.exit()

url, auth, ts = sample
query = url.split('?', 1)[1]
pathq = url.split('https://serviceinfo.inke.cn', 1)[1]

secrets = set()
pat = re.compile(r'const-string\s+v\d+,\s+"([^"]{16})"')
for dp, _, fs in os.walk(SMALI_ROOT):
    for f in fs:
        if not f.endswith('.smali'):
            continue
        try:
            text = open(os.path.join(dp, f), encoding='utf-8', errors='ignore').read()
        except Exception:
            continue
        for s in pat.findall(text):
            if re.fullmatch(r'[ -~]{16}', s):
                secrets.add(s.encode())
secrets.update([
    b'1ba5fb066d7e33d5',
    bytes.fromhex('1ba5fb066d7e33d5'),
    b'OklL',
    b'com.meelive.ingkee',
    b'GF10000',
    b'3000000000000000',
])

options = {
    'pkg': [PKG, ''],
    'body': ['', '\n'],
    'ts': [ts],
    'q': [query, '?' + query, pathq, pathq.lstrip('/')],
    'method': ['', 'GET'],
    'appid': [APPID, ''],
    'secret_msg': ['', '1ba5fb066d7e33d5'],
}
print('secrets=%d' % len(secrets))
for secret in secrets:
    for vals in itertools.product(*options.values()):
        d = dict(zip(options.keys(), vals))
        secret_text = secret.decode('utf-8', 'ignore')
        elems = [d['pkg'], d['body'], d['ts'], d['q'], d['method'], d['appid'], d['secret_msg'], secret_text]
        msg = '\n'.join(x for x in elems if x != '')
        if '\n' not in msg:
            continue
        sig = base64.b64encode(hmac.new(secret, msg.encode(), hashlib.sha1).digest()).decode()
        if sig == auth:
            print('MATCH secret=%r msg=%r' % (secret, msg))
            sys.exit()
print('no match')
