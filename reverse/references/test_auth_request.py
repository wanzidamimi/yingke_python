import base64
import hashlib
import hmac
import sys
import time

from curl_cffi import requests

PKG = 'com.meelive.ingkee'
APPID = 'OklL'
SECRET = b'1ba5fb066d7e33d5'

ts = str(int(time.time() * 1000))
query = (
    'cc=TG36064&dev_name=Google&ik_appid=OklL'
    '&code1462295386=' + ts +
    '&xid=1&cv=IK9.9.05_Android&ast=1'
    '&lc=3726b262d726e165&sign_from=android'
    '&ua=GooglePixel3&osversion=android_28'
    '&vv=20250806_100038%40master_dev%4057f7d5887eb94750ac96b39238c27c0dd4eeb08b%40Legacy_b1ff4f10b2890019e680a0b39ee2755bc4da8b01%402.7.0.2-mediafoundation-lite-player-extended-dev-57f7d588-202508060957%40Android'
    '&uid=779252212&liveid=1792755265153708&count=20'
)
msg = '%s\n\nGET\n%s\n%s' % (PKG, ts, query)
sig = base64.b64encode(hmac.new(SECRET, msg.encode(), hashlib.sha1).digest()).decode()
auth = 'InkeV1 %s:%s' % (APPID, sig)
url = 'https://service.inke.cn/api/message/get?' + query

headers = {
    'Authorization': auth,
    'Client-TimeStamp': ts,
    'User-Agent': 'okhttp/3.12.13',
    'Accept-Encoding': 'gzip',
}

print('ts', ts)
print('auth', auth)
r = requests.get(url, headers=headers, impersonate='chrome', timeout=15)
print('status', r.status_code)
print('len', len(r.content))
print(r.text[:1500])
