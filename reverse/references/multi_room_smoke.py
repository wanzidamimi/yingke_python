import sys
import time
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'd:/Scrapy-project/yingke_python')

from inke_tcp_collector import InkeTcpCollector, fetch_hot_rooms

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
COUNT = int(sys.argv[2]) if len(sys.argv) > 2 else 5

rooms = fetch_hot_rooms()
print('HOT_ROOMS', len(rooms), flush=True)

for room in rooms[:COUNT]:
    liveid = room['liveid']
    nick = room['nick']
    print('\n===== ROOM', nick, liveid, '=====', flush=True)
    counts = Counter()
    samples = []

    def on_message(msg):
        if msg.get('kind') != 'danmu':
            print('SYS', msg.get('text'), flush=True)
            return
        cat = msg.get('category') or 'other'
        counts[cat] += 1
        if cat == 'chat' and len(samples) < 8:
            samples.append('%s: %s' % (msg.get('user', ''), msg.get('content', '')))

    c = InkeTcpCollector(on_message=on_message, liveid=liveid)
    try:
        c.start()
    except Exception as exc:
        print('START_ERR', exc, flush=True)
        continue
    deadline = time.time() + SECONDS
    while time.time() < deadline and c.alive:
        time.sleep(0.5)
    c.stop()
    print('SUMMARY', dict(counts), 'total', sum(counts.values()), flush=True)
    for line in samples:
        print('CHAT', line, flush=True)
