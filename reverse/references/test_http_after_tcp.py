#!/usr/bin/env python3
"""先建立 TCP 握手/认证，再调用 HTTP 备份订阅。"""
import json
import socket
import sys
import time

import requests

from app_tcp_client import (
    SESSION_ID,
    SEQ_BASE,
    SUBSCRIBE_CMD,
    VERSION,
    build_packet,
    build_subscribe_body,
    find_packet,
    parse_packet,
    rc4,
)
from parse_pktmon_pcap import payloads
from replay_and_subscribe import find_client_cmd

PCAP = r'd:/Scrapy-project/yingke_python/reverse/logs/inke_room2.pcapng'
NONCE = 'dbebdhgd'
KEY = '0c2a616bfd8442aec0495d04d3ae3599'
GATEWAY = '111.13.223.188'


def handshake_packet():
    return next(p for s, d, p in payloads(PCAP) if s != 1300 and len(p) == 203)


def read_one(sock, buf, timeout=10):
    sock.settimeout(timeout)
    end = time.time() + timeout
    while time.time() < end:
        found = find_packet(buf)
        if found:
            start, pkt = found
            del buf[:start + len(pkt)]
            return parse_packet(pkt)
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        buf.extend(chunk)
    return None


def main(subscribe_id):
    hs = handshake_packet()
    auth = find_client_cmd(PCAP, 0x4004)
    sock = socket.create_connection((GATEWAY, 1300), timeout=5)
    buf = bytearray()
    try:
        sock.sendall(hs)
        resp = read_one(sock, buf)
        print('tcp handshake resp=%s' % (bool(resp),))
        if auth:
            sock.sendall(auth)
            ar = read_one(sock, buf, 5)
            print('tcp auth resp=%s len=%s' % (bool(ar), len(ar['body']) if ar else 0))
        sock.close()

        body = rc4(build_subscribe_body(subscribe_id), KEY)
        ext = json.dumps({'xid': 1}, separators=(',', ':')).encode()
        packet = build_packet(SUBSCRIBE_CMD, body, VERSION, SESSION_ID, SEQ_BASE, ext=ext)
        print('http packet_len=%d' % len(packet))
        r = requests.post('http://%s/subscribe' % GATEWAY, data=packet, timeout=20)
        print('http status=%s len=%d body=%r' % (r.status_code, len(r.content), r.content[:1000]))

    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1])
