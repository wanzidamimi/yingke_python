#!/usr/bin/env python3
import hashlib
import json
import socket
import sys
import time

from app_tcp_client import build_handshake_wrapped, build_packet, HANDSHAKE_WRAP_CMD, HANDSHAKE_CMD, PUBLIC_ID, rsa_encrypt, lv, u16, make_nonce, find_packet, parse_packet, rc4

SALT = '::plkfuyne820icnb8'
GID_DEC = 779252212
GID_HEX = '85c8b4a5ac8f203e618e3e25244b3823'


def wrapped_with_token(token, nonce):
    plain = u16(HANDSHAKE_CMD) + bytes([PUBLIC_ID]) + lv(token) + lv(nonce)
    inner = u16(HANDSHAKE_CMD) + bytes([PUBLIC_ID]) + rsa_encrypt(plain)
    ext = json.dumps({'re-ack': 'true', 'xid': 1, 'long_uid': GID_DEC}, separators=(',', ':')).encode()
    return build_packet(HANDSHAKE_WRAP_CMD, inner, 1, 0, 10000, ext=ext)


def read(sock, timeout=6):
    sock.settimeout(timeout)
    buf = bytearray()
    end = time.time() + timeout
    while time.time() < end:
        found = find_packet(buf)
        if found:
            start, p = found
            return parse_packet(p)
        try:
            b = sock.recv(4096)
        except socket.timeout:
            break
        if not b:
            break
        buf.extend(b)
    return None


for label, raw in [
    ('decimal', str(GID_DEC)),
    ('hex', GID_HEX),
]:
    token = hashlib.md5((raw + SALT).encode()).hexdigest()
    pkt = wrapped_with_token(token, 'ehebecee')
    print(label, token, len(pkt))
    s = socket.create_connection(('111.13.223.167', 1300), timeout=5)
    try:
        s.sendall(pkt)
        r = read(s)
        print('resp', r['res'] if r else None, len(r['body']) if r else 0)
    except Exception as e:
        print('err', e)
    finally:
        s.close()
