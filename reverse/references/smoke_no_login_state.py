import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:/Scrapy-project/yingke_python')

import inke_tcp_collector as mod
from inke_tcp_collector import InkeTcpCollector, fetch_hot_rooms

# 模拟“非 root 手机”：不读取本地缓存和 MITM 日志
mod.refresh_gid_from_adb = lambda c, *a, **k: c
mod.refresh_device_fields_from_adb = lambda c, *a, **k: c
mod.refresh_env_from_mitm_log = lambda c, *a, **k: c

BASE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_config.json'
OUT = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_fake_login.json'

cfg = json.load(open(BASE, encoding='utf-8'))
fake_gid = '0123456789abcdef0123456789abcdef'
fake_sid = 'FAKE_SESSION_DOES_NOT_EXIST'
cfg['gid'] = fake_gid
cfg['auth']['gid'] = fake_gid
cfg['auth']['bus_buf']['gid'] = fake_gid
cfg['auth']['bus_buf']['sid'] = fake_sid
cfg['enter_room']['gid'] = fake_gid
cfg['enter_room']['bus_buf']['gid'] = fake_gid
json.dump(cfg, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

liveid = sys.argv[1] if len(sys.argv) > 1 else fetch_hot_rooms()[0]['liveid']
print('TARGET', liveid, 'GID', fake_gid, 'SID', fake_sid)

count = [0]


def on_message(msg):
    if msg.get('kind') == 'danmu':
        count[0] += 1
        if count[0] <= 5:
            print('DANMU', msg.get('category'), msg.get('user'), msg.get('content'))
    else:
        print('SYS', msg.get('text'))


c = InkeTcpCollector(on_message=on_message, liveid=liveid, config_path=OUT)
c.start()
end = time.time() + 20
while time.time() < end and c.alive:
    time.sleep(0.5)
c.stop()
print('TOTAL', count[0])
