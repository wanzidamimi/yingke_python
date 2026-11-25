import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:/Scrapy-project/yingke_python')

import inke_tcp_collector as mod
from inke_tcp_collector import fetch_hot_rooms

BASE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_config.json'
FAKE = r'D:/Scrapy-project/yingke_python/reverse/references/inke_runtime_fake_login.json'

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 15
ROOM_COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 3
rooms = fetch_hot_rooms()[:ROOM_COUNT]

orig = {
    'gid': mod.refresh_gid_from_adb,
    'device': mod.refresh_device_fields_from_adb,
    'mitm': mod.refresh_env_from_mitm_log,
}

modes = [
    ('fake', FAKE, False),
    ('static-real', BASE, False),
    ('refresh-real', BASE, True),
]


def run(mode, cfg_path, allow_refresh, liveid, nick):
    mod.refresh_gid_from_adb = orig['gid'] if allow_refresh else lambda c, *a, **k: c
    mod.refresh_device_fields_from_adb = orig['device'] if allow_refresh else lambda c, *a, **k: c
    mod.refresh_env_from_mitm_log = orig['mitm'] if allow_refresh else lambda c, *a, **k: c

    counters = {'chat': 0, 'member': 0, 'stats': 0, 'other': 0}

    def on_message(msg):
        if msg.get('kind') != 'danmu':
            return
        cat = msg.get('category') or 'other'
        if cat in counters:
            counters[cat] += 1

    c = mod.InkeTcpCollector(on_message=on_message, liveid=liveid, config_path=cfg_path)
    try:
        c.start()
    except Exception as e:
        print(mode, nick, 'START_ERR', e, flush=True)
        return
    end = time.time() + SECONDS
    while time.time() < end and c.alive:
        time.sleep(0.5)
    c.stop()
    print(mode, nick, liveid, counters, 'total', sum(counters.values()), flush=True)


for r in rooms:
    print('===== ROOM', r['nick'], r['liveid'], '=====', flush=True)
    for mode, cfg, refresh in modes:
        run(mode, cfg, refresh, r['liveid'], r['nick'])
