import base64
import json
import random
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:/Scrapy-project/yingke_python')

import inke_tcp_collector as mod

LIVEID = sys.argv[1]
SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 25

BASE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_config.json'
FAKE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_fake_login.json'
RANDOM = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_random_uid.json'

# 生成随机 uid 配置
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


def run(name, path, refresh):
    mod.refresh_gid_from_adb = orig['gid'] if refresh else lambda c, *a, **k: c
    mod.refresh_device_fields_from_adb = orig['device'] if refresh else lambda c, *a, **k: c
    mod.refresh_env_from_mitm_log = orig['mitm'] if refresh else lambda c, *a, **k: c
    counts = {'chat': 0, 'member': 0, 'stats': 0, 'system': 0, 'other': 0}
    samples = []

    def on_message(msg):
        if msg.get('kind') != 'danmu':
            return
        cat = msg.get('category') or 'other'
        counts[cat] = counts.get(cat, 0) + 1
        if cat == 'chat' and len(samples) < 5:
            samples.append('%s: %s' % (msg.get('user'), msg.get('content')))

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
    print(name, counts, 'TOTAL', sum(counts.values()), flush=True)
    for s in samples:
        print('  CHAT', s, flush=True)


print('TARGET', LIVEID, 'SECONDS', SECONDS, 'RANDOM_UID', uid, flush=True)
run('dynamic-real', BASE, True)
run('static-real', BASE, False)
run('fake-gid-sid', FAKE, False)
run('random-uid', RANDOM, False)
