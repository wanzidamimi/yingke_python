import base64
import json
import random
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:/Scrapy-project/yingke_python')

import inke_tcp_collector as mod
from inke_tcp_collector import InkeTcpCollector, fetch_hot_rooms

# 完全不读取本机登录态/缓存
mod.refresh_gid_from_adb = lambda c, *a, **k: c
mod.refresh_device_fields_from_adb = lambda c, *a, **k: c
mod.refresh_env_from_mitm_log = lambda c, *a, **k: c

BASE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_config.json'
OUT = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_random_uid.json'

uid = str(random.randint(10000000, 99999999))
fake_gid = '0123456789abcdef0123456789abcdef'
fake_sid = 'FAKE_SESSION_DOES_NOT_EXIST'

cfg = json.load(open(BASE, encoding='utf-8'))
cfg['uid'] = int(uid)
cfg['gid'] = fake_gid
cfg['auth']['uid'] = int(uid)
cfg['auth']['bus_buf']['uid'] = uid
cfg['auth']['bus_buf']['gid'] = fake_gid
cfg['auth']['bus_buf']['sid'] = fake_sid
cfg['auth']['gid'] = fake_gid
cfg['enter_room']['uid'] = int(uid)
cfg['enter_room']['bus_buf']['uid'] = int(uid)
cfg['enter_room']['gid'] = fake_gid
cfg['enter_room']['bus_buf']['gid'] = fake_gid
source = {"appid": "10000", "uid": uid, "page": "unknown", "time": "0"}
cfg['auth']['bus_buf']['source_info'] = base64.b64encode(
    json.dumps(source, separators=(',', ':')).encode()
).decode()
json.dump(cfg, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

liveid = sys.argv[1] if len(sys.argv) > 1 else fetch_hot_rooms()[0]['liveid']
print('TARGET', liveid, 'RANDOM_UID', uid, flush=True)

counts = {'chat': 0, 'member': 0, 'stats': 0, 'system': 0, 'other': 0}
count = [0]


def on_message(msg):
    if msg.get('kind') == 'danmu':
        count[0] += 1
        cat = msg.get('category') or 'other'
        counts[cat] = counts.get(cat, 0) + 1
        if count[0] <= 12:
            print('DANMU', msg.get('category'), msg.get('user'), msg.get('content'), flush=True)
    else:
        print('SYS', msg.get('text'), flush=True)


c = InkeTcpCollector(on_message=on_message, liveid=liveid, config_path=OUT)
c.start()
end = time.time() + 25
while time.time() < end and c.alive:
    time.sleep(0.5)
c.stop()
print('COUNTS', counts, 'TOTAL', count[0], flush=True)
