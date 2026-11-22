import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'd:/Scrapy-project/yingke_python')

from inke_tcp_collector import InkeTcpCollector, fetch_hot_rooms

rooms = fetch_hot_rooms()
liveid = sys.argv[1] if len(sys.argv) > 1 else (rooms[0]['liveid'] if rooms else '1795309411539363')
seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 45
print('TARGET', liveid, seconds)

messages = []


def on_message(msg):
    if msg.get('kind') == 'danmu':
        messages.append(msg)
        print('DANMU', msg.get('category'), msg.get('user'), msg.get('content'))
    else:
        print('SYS', msg.get('kind'), msg.get('text'))


c = InkeTcpCollector(on_message=on_message, liveid=liveid)
c.start()
deadline = time.time() + seconds
while time.time() < deadline and c.alive:
    time.sleep(0.5)
c.stop()
print('TOTAL', len(messages))
