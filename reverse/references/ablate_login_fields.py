import base64
import copy
import json
import random
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:/Scrapy-project/yingke_python')

import inke_tcp_collector as mod

LIVEID = sys.argv[1]
SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
BASE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_config.json'
TMP = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_ablate.json'

base = json.load(open(BASE, encoding='utf-8'))

# 模拟非 root：不读取任何本地动态字段
mod.refresh_gid_from_adb = lambda c, *a, **k: c
mod.refresh_device_fields_from_adb = lambda c, *a, **k: c
mod.refresh_env_from_mitm_log = lambda c, *a, **k: c


def set_uid(cfg, uid):
    uid = str(uid)
    cfg['uid'] = int(uid)
    cfg['auth']['uid'] = int(uid)
    cfg['auth']['bus_buf']['uid'] = uid
    cfg['enter_room']['uid'] = int(uid)
    cfg['enter_room']['bus_buf']['uid'] = int(uid)
    src = {'appid': '10000', 'uid': uid, 'page': 'unknown', 'time': '0'}
    cfg['auth']['bus_buf']['source_info'] = base64.b64encode(
        json.dumps(src, separators=(',', ':')).encode()
    ).decode()
    cfg['auth']['bus_buf']['clientId'] = '%d#%d@%s$%d' % (
        int(time.time() * 1000), int(time.monotonic() * 1000),
        uid, random.randint(-2147483648, 2147483647)
    )


def set_gid(cfg, gid):
    cfg['gid'] = gid
    cfg['auth']['gid'] = gid
    cfg['auth']['bus_buf']['gid'] = gid
    cfg['enter_room']['gid'] = gid
    cfg['enter_room']['bus_buf']['gid'] = gid


def set_sid(cfg, sid):
    cfg['auth']['bus_buf']['sid'] = sid


FAKE_GID = '0123456789abcdef0123456789abcdef'
FAKE_SID = 'FAKE_SESSION_DOES_NOT_EXIST'
RANDOM_UID = str(random.randint(10000000, 99999999))

variants = []
variants.append(('all-real', copy.deepcopy(base)))
c = copy.deepcopy(base); set_gid(c, FAKE_GID); variants.append(('fake-gid', c))
c = copy.deepcopy(base); set_sid(c, FAKE_SID); variants.append(('fake-sid', c))
c = copy.deepcopy(base); set_gid(c, FAKE_GID); set_sid(c, FAKE_SID); variants.append(('fake-gid+sid', c))
c = copy.deepcopy(base); set_uid(c, RANDOM_UID); variants.append(('random-uid', c))
c = copy.deepcopy(base); set_uid(c, RANDOM_UID); set_gid(c, FAKE_GID); set_sid(c, FAKE_SID); variants.append(('random-identity', c))


def run(name, cfg):
    json.dump(cfg, open(TMP, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    counts = {'chat': 0, 'member': 0, 'stats': 0, 'system': 0, 'other': 0}
    samples = []

    def on_message(msg):
        if msg.get('kind') != 'danmu':
            return
        cat = msg.get('category') or 'other'
        counts[cat] = counts.get(cat, 0) + 1
        if cat == 'chat' and len(samples) < 3:
            samples.append('%s: %s' % (msg.get('user'), msg.get('content')))

    c = mod.InkeTcpCollector(on_message=on_message, liveid=LIVEID, config_path=TMP)
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
        print('  ', s, flush=True)


print('TARGET', LIVEID, 'SECONDS', SECONDS, 'RANDOM_UID', RANDOM_UID, flush=True)
for name, cfg in variants:
    run(name, cfg)
