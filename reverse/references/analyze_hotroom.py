#!/usr/bin/env python3
"""分析高热度直播间抓包：解压 cmd=0xb002 消息并统计 tp。"""
import collections
import gzip
import json
import sys

from app_tcp_client import rc4
from parse_pktmon_pcap import payloads

KEY = '0c2a616bfd8442aec0495d04d3ae3599'


def body_of(packet):
    if len(packet) < 22:
        return b''
    n = int.from_bytes(packet[18:22], 'big')
    return packet[22:22 + n]


def main(path):
    seen = set()
    types = collections.Counter()
    chats = []
    for s, d, p in payloads(path):
        if s != 1300 or len(p) < 30:
            continue
        body = body_of(p)
        if not body:
            continue
        try:
            if body[:2] == b'\x1f\x8b':
                plain = gzip.decompress(body)
            else:
                plain = gzip.decompress(rc4(body, KEY))
            msg = json.loads(plain.decode('utf-8'))
        except Exception:
            continue
        mid = msg.get('messageId')
        if mid and mid in seen:
            continue
        if mid:
            seen.add(mid)
        items = list(msg.get('ms', []))
        if isinstance(msg.get('bus_buf'), list):
            for inner in msg['bus_buf']:
                if isinstance(inner, dict):
                    items.extend(inner.get('ms', []))
        for item in items:
            tp = item.get('tp', '?')
            types[tp] += 1
            if tp in ('chat', 's.m', 'comment', 'danmu'):
                chats.append(item)
    print('unique_messages=%d' % len(seen))
    print('types=%s' % json.dumps(dict(types), ensure_ascii=False))
    for item in chats[:30]:
        print(json.dumps(item, ensure_ascii=False)[:1000])


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1])
