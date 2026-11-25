import os
import re

DIR = r'D:/Scrapy-project/yingke_python/reverse/logs/mitm_bodies'
KEYS = [
    'USER_PHONE_LOGIN', 'USER_PHONE_CODE', 'USER_JIGUANG_LOGIN',
    'USER_SHANYAN_LOGIN', 'USER_ACCOUT_VISITOR_LOGIN', 'USER_ACCOUNT_CODE',
    'RISK_SMS', 'RISK_SMS_CHECK', 'EVENT_VERIFY_INFO', 'EVENT_VERIFY_CFG',
    'IM_SIGNATURE', 'USER_INFO', 'USER_ACCOUNT_CHECK_SESSION',
    'USER_ACCOUNT_LOGIN', 'USER_ACCOUNT_REGISTER',
]
pat = re.compile(r'\{"key":"([A-Z_0-9]+)","url":"([^"]+)"')

seen = {}
for name in os.listdir(DIR):
    path = os.path.join(DIR, name)
    try:
        text = open(path, 'rb').read().decode('utf-8', 'ignore')
    except Exception:
        continue
    for m in pat.finditer(text):
        key = m.group(1)
        if key in KEYS:
            seen[key] = m.group(2)

for key in sorted(seen):
    print(key, seen[key])
