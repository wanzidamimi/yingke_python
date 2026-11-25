import re
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'D:/Scrapy-project/yingke_python')

from inke_tcp_collector import InkeTcpCollector, fetch_hot_rooms

SECONDS = int(sys.argv[1]) if len(sys.argv) > 1 else 12
rooms = fetch_hot_rooms()
print('ROOMS', len(rooms), flush=True)

for r in rooms:
    counters = {'chat': 0, 'member': 0, 'stats': 0, 'other': 0}
    online = []

    def on_message(msg):
        if msg.get('kind') != 'danmu':
            return
        cat = msg.get('category') or 'other'
        if cat in counters:
            counters[cat] += 1
        if cat == 'stats':
            m = re.search(r'(\d+)', str(msg.get('content') or ''))
            if m:
                online.append(int(m.group(1)))

    c = InkeTcpCollector(on_message=on_message, liveid=r['liveid'])
    try:
        c.start()
    except Exception as e:
        print('ERR', r['nick'], e, flush=True)
        continue
    end = time.time() + SECONDS
    while time.time() < end and c.alive:
        time.sleep(0.5)
    c.stop()
    print('%s\t%s\tonline=%s\tchat=%d\tmember=%d\tstats=%d' % (
        r['nick'], r['liveid'], max(online) if online else 0,
        counters['chat'], counters['member'], counters['stats']
    ), flush=True)
