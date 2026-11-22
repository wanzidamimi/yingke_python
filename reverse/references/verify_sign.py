import base64
import hashlib
import hmac
import re
import sys

LOG = r'd:/Scrapy-project/yingke_python/reverse/logs/mitm_requests_detail.log'
SECRET = b'1ba5fb066d7e33d5'
APPID = 'OklL'
PKG = 'com.meelive.ingkee'

line = None
for ln in open(LOG, encoding='utf-8', errors='replace'):
    if 'sign_from=android' in ln and 'Authorization' in ln and 'serviceinfo.inke.cn/serviceinfo/info?' in ln:
        line = ln
        break
if not line:
    print('no sample')
    sys.exit()

url = re.search(r'REQ GET (\S+)', line).group(1)
auth = re.search(r"'Authorization': 'InkeV1 OklL:([^']+)'", line).group(1)
ts = re.search(r"'Client-TimeStamp': '(\d+)'", line).group(1)
query = url.split('?', 1)[1]
body_md5 = ''
msg = '%s\n%s\n%s\n%s\n%s' % (PKG, body_md5, ts, query, APPID)
sig = base64.b64encode(hmac.new(SECRET, msg.encode(), hashlib.sha1).digest()).decode()
print('expected', sig)
print('actual  ', auth)
print('match', sig == auth)
