import sys
import json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from curl_cffi import requests as creq

url = 'https://service.inke.cn/api/user/account/visitor/login'
try:
    r = creq.get(url, impersonate='chrome', timeout=12)
    print('status', r.status_code)
    print(r.text[:2000])
except Exception as e:
    print('ERR', e)
