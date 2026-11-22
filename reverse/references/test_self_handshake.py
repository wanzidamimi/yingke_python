import socket
import sys

from app_tcp_client import (
    GATEWAYS,
    build_handshake_wrapped,
    find_packet,
    parse_packet,
    rc4,
)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
UID = 779252212
NONCE = 'abcdefgh'

handshake, meta = build_handshake_wrapped(UID, nonce=NONCE)
print('token', meta['token'], 'nonce', NONCE, 'packet', len(handshake))

for target in GATEWAYS:
    try:
        s = socket.create_connection(target, timeout=5)
    except OSError as e:
        print('connect failed', target, e)
        continue
    print('connected', target)
    s.sendall(handshake)
    s.settimeout(8)
    buf = bytearray()
    found = None
    try:
        import time
        end = time.time() + 8
        while time.time() < end:
            found = find_packet(buf)
            if found:
                break
            chunk = s.recv(4096)
            if not chunk:
                break
            buf.extend(chunk)
    except Exception as e:
        print('recv err', e)
    if not found:
        print('no response')
        s.close()
        continue
    packet = parse_packet(found[1])
    print('resp cmd=0x%04x res=%d body_len=%d' % (packet['cmd'], packet['res'], len(packet['body'])))
    try:
        print('plain', rc4(packet['body'], NONCE)[:300])
    except Exception as e:
        print('decrypt err', e)
    s.close()
    break
