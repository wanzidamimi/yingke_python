import base64
import json
import random
import sys
import time
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:/Scrapy-project/yingke_python')

import inke_tcp_collector as mod

LIVEID = sys.argv[1]
ROUNDS = int(sys.argv[2]) if len(sys.argv) > 2 else 4
SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 12
BASE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_config.json'
FAKE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_fake_login.json'
RANDOM = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_random_uid.json'

cfg = json.load(open(BASE, encoding='utf-8'))
uid = str(random.randint(10000000, 99999999))
gid = '0123456789abcdef0123456789abcdef'
sid = 'FAKE_SESSION_DOES_NOT_EXIST'
cfg['uid'] = int(uid)
cfg['gid'] = gid
cfg['auth']['uid'] = int(uid)
cfg['auth']['bus_buf']['uid'] = uid
cfg['auth']['bus_buf']['gid'] = gid
cfg['auth']['bus_buf']['sid'] = sid
cfg['auth']['gid'] = gid
cfg['enter_room']['uid'] = int(uid)
cfg['enter_room']['bus_buf']['uid'] = int(uid)
cfg['enter_room']['gid'] = gid
cfg['enter_room']['bus_buf']['gid'] = gid
src = {'appid': '10000', 'uid': uid, 'page': 'unknown', 'time': '0'}
cfg['auth']['bus_buf']['source_info'] = base64.b64encode(
    json.dumps(src, separators=(',', ':')).encode()
).decode()
json.dump(cfg, open(RANDOM, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

orig = {
    'gid': mod.refresh_gid_from_adb,
    'device': mod.refresh_device_fields_from_adb,
    'mitm': mod.refresh_env_from_mitm_log,
}
modes = [
    ('dynamic-real', BASE, True),
    ('static-real', BASE, False),
    ('fake-gid-sid', FAKE, False),
    ('random-uid', RANDOM, False),
]
totals = defaultdict(lambda: {'chat': 0, 'member': 0, 'stats': 0, 'system': 0, 'other': 0})


def run(name, path, refresh):
    mod.refresh_gid_from_adb = orig['gid'] if refresh else lambda c, *a, **k: c
    mod.refresh_device_fields_from_adb = orig['device'] if refresh else lambda c, *a, **k: c
    mod.refresh_env_from_mitm_log = orig['mitm'] if refresh else lambda c, *a, **k: c

    def on_message(msg):
        if msg.get('kind') != 'danmu':
            return
        cat = msg.get('category') or 'other'
        totals[name][cat] = totals[name].get(cat, 0) + 1

    c = mod.InkeTcpCollector(on_message=on_message, liveid=LIVEID, config_path=path)
    try:
        c.start()
    except Exception as e:
        print(name, 'ERR', e, flush=True)
        return
    end = time.time() + SECONDS
    while time.time() < end and c.alive:
        time.sleep(0.5)
    c.stop()
    print('  %-13s %s' % (name, totals[name]), flush=True)


print('TARGET', LIVEID, 'ROUNDS', ROUNDS, 'SECONDS', SECONDS, 'RANDOM_UID', uid, flush=True)
for rnd in range(ROUNDS):
    print('ROUND', rnd + 1, flush=True)
    order = modes[:]
    random.shuffle(order)
    for name, path, refresh in order:
        run(name, path, refresh)
print('FINAL', flush=True)
for name, _path, _refresh in modes:
    counts = totals[name]
    print(name, counts, 'chat_total', counts['chat'], flush=True)
