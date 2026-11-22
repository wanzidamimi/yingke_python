import sys
import time

from curl_cffi import requests

AUTH = 'InkeV1 OklL:OKsTsC9B0kDa+VAaVYlyIhzr6dY='
UID = '779252212'
LIVEID = '1792755265153708'
HEADERS = {
    'Authorization': AUTH,
    'Client-TimeStamp': str(int(time.time() * 1000)),
    'User-Agent': 'okhttp/3.12.13',
    'Accept-Encoding': 'gzip',
}


def main():
    urls = [
        'https://service.inke.cn/api/message/get',
        'https://service.inke.cn/api/message/get_sys',
        'https://service.inke.cn/api/message/get_topic',
    ]
    common = {
        'uid': UID,
        'ik_appid': 'OklL',
        'cv': 'IK9.9.05_Android',
        'version_code': '9920',
        'version_name': '9.9.05',
        'conn': 'wifi',
        'ua': 'GooglePixel3',
        'xid': '81',
        'sid': '20ni2G7C9bzpDOzSCyLQfrJJGDjboWkxxpi2knSfhWARUXXtx4xIXIoi3',
        'mtid': 'd9c471b76710fca876003681b785db87',
    }
    param_sets = [
        dict(common, liveid=LIVEID, count='20'),
        dict(common, id=LIVEID, count='20'),
        dict(common, roomid=LIVEID, count='20'),
    ]
    for url in urls:
        for params in param_sets:
            try:
                r = requests.get(url, params=params, headers=HEADERS, impersonate='chrome', timeout=10)
                print(url, params, r.status_code, len(r.content), r.text[:300])
            except Exception as exc:
                print(url, params, 'ERR', exc)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
