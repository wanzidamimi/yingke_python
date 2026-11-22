import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'd:/Scrapy-project/yingke_python')

from inke_tcp_collector import (
    DEFAULT_NONCE,
    find_auth,
    find_handshake,
    read_packet,
)
from app_tcp_client import GATEWAYS, parse_packet, rc4
from reassemble_tcp_frames import parse_frames, reassemble

PATH = sys.argv[1]
LIVEID = sys.argv[2]
HS_PATH = sys.argv[3] if len(sys.argv) > 3 else PATH
KEY = '0c2a616bfd8442aec0495d04d3ae3599'

handshake = find_handshake(HS_PATH)
auth = find_auth(HS_PATH)
print('handshake', len(handshake), 'auth', len(auth))

# 从同一抓包取客户端真实 0002 / 4c04 / 4020 帧
frames = {}
for stream_key, stream in reassemble(PATH):
    if 1300 not in (stream_key[1], stream_key[3]) or stream_key[1] == 1300:
        continue
    for frame in parse_frames(stream)[0]:
        cmd = frame[4:6].hex()
        frames.setdefault(cmd, frame)
print('frames', {k: len(v) for k, v in frames.items()})

for target in GATEWAYS:
    import socket
    sock = socket.create_connection(target, timeout=5)
    print('connected', target)
    sock.sendall(handshake)
    buf = bytearray()
    p = read_packet(sock, buf, timeout=8)
    info = rc4(p['body'], DEFAULT_NONCE)
    print('handshake resp', p['cmd'], info[:160])
    sock.sendall(auth)
    for cmd in ('0002', '4c04', '4020'):
        if cmd in frames:
            print('send', cmd, len(frames[cmd]))
            sock.sendall(frames[cmd])
    deadline = time.time() + 45
    while time.time() < deadline:
        p = read_packet(sock, buf, timeout=1)
        if not p:
            continue
        print('RECV cmd=%04x len=%d' % (p['cmd'], len(p['body'])))
    sock.close()
    break
