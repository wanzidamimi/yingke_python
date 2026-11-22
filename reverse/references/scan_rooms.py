#!/usr/bin/env python3
"""扫描多个直播间，统计纯接口收到的消息类型。"""
import gzip
import json
import socket
import sys
import time

from app_tcp_client import build_subscribe_packet, find_packet, parse_packet, rc4
from parse_pktmon_pcap import payloads
from replay_and_subscribe import find_client_cmd

PCAP = r'd:/Scrapy-project/yingke_python/reverse/logs/inke_room2.pcapng'
NONCE = 'dbebdhgd'
ROOMS = [
    '1795004103423719',
    '1795009528674000',
    '1795012237704688',
    '1795005437740747',
    '1795004462105958',
]


def handshake():
    return next(p for s, d, p in payloads(PCAP) if s != 1300 and len(p) == 203)


def read_one(sock, buf, timeout):
    sock.settimeout(timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = find_packet(buf)
        if found:
            start, packet = found
            del buf[:start + len(packet)]
            return parse_packet(packet)
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            break
        if not chunk:
            break
        buf.extend(chunk)
    return None


def scan(room, seconds=20):
    hs = handshake()
    sock = socket.create_connection(('111.13.223.188', 1300), timeout=5)
    try:
        sock.sendall(hs)
        buf = bytearray()
        resp = read_one(sock, buf, 8)
        if not resp:
            print('[%s] no response' % room)
            return
        key = json.loads(rc4(resp['body'], NONCE).decode())['key']
        auth = find_client_cmd(PCAP, 0x4004)
        if auth:
            sock.sendall(auth)
        sub, _ = build_subscribe_packet(room, key)
        sock.sendall(sub)
        deadline = time.time() + seconds
        types = {}
        while time.time() < deadline:
            pkt = read_one(sock, buf, max(1, int(deadline - time.time())))
            if not pkt:
                break
            if pkt['cmd'] != 0xB002:
                continue
            try:
                msg = json.loads(gzip.decompress(pkt['body']).decode('utf-8'))
            except Exception:
                continue
            for item in msg.get('ms', []):
                tp = item.get('tp', '?')
                types[tp] = types.get(tp, 0) + 1
                if tp in ('chat', 's.m', 'comment', 'danmu'):
                    print('[%s] %s %s' % (room, tp, json.dumps(item, ensure_ascii=False)[:500]))
        print('[%s] types=%s' % (room, json.dumps(types, ensure_ascii=False)))
    finally:
        sock.close()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for room in ROOMS:
        try:
            scan(room, 18)
        except Exception as exc:
            print('[%s] error=%s' % (room, exc))
