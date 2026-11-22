import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'd:/Scrapy-project/yingke_python')

from fastapi.testclient import TestClient

from app import app
from inke_tcp_collector import fetch_hot_rooms

rooms = fetch_hot_rooms()
liveid = rooms[0]['liveid']
print('TARGET', liveid)

with TestClient(app) as client:
    print('index', client.get('/').status_code)
    rooms_resp = client.get('/api/rooms').json()
    print('rooms', len(rooms_resp['rooms']))
    print('resolve', client.post('/api/resolve', json={'room': liveid}).json())

    r = client.post('/api/start', json={'room': liveid, 'liveid': liveid})
    print('start', r.json())
    time.sleep(20)
    status = client.get('/api/status').json()
    print('status', status)
    exp = client.post('/api/export').json()
    print('export', exp)
    print('stop', client.post('/api/stop').json())
