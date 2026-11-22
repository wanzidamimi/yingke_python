import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'd:/Scrapy-project/yingke_python')

from inke_tcp_collector import InkeTcpCollector, fetch_hot_rooms, load_runtime_config

BASE = load_runtime_config()
TEST_CFG = r'd:/Scrapy-project/yingke_python/reverse/references/inke_runtime_no_passthrough.json'

cfg = json.loads(json.dumps(BASE))
b = cfg['enter_room']['bus_buf']['b']
b.pop('pass-through', None)
with open(TEST_CFG, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)

liveid = fetch_hot_rooms()[0]['liveid']
print('TARGET', liveid, 'PASS_THROUGH', 'absent')

msgs = []


def on_message(msg):
    if msg.get('kind') == 'danmu':
        msgs.append(msg)
        if len(msgs) <= 8:
            print('DANMU', msg.get('category'), msg.get('user'), msg.get('content'))
    else:
        print('SYS', msg.get('text'))


c = InkeTcpCollector(on_message=on_message, liveid=liveid, config_path=TEST_CFG)
c.start()
end = time.time() + 35
while time.time() < end and c.alive:
    time.sleep(0.5)
c.stop()
print('TOTAL', len(msgs))
