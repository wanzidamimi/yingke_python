#!/usr/bin/env python3
"""复刻 ol/e.HttpSubscriber：POST 订阅包到 http://<gateway>/subscribe。"""
import argparse
import json
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
    rc4,
)

KEY = "0c2a616bfd8442aec0495d04d3ae3599"
URLS = [
    "http://111.13.223.188/subscribe",
    "http://111.13.223.167/subscribe",
    "http://47.95.96.98/subscribe",
]


def main(subscribe_id, xid, max_id, timeout):
    body = rc4(build_subscribe_body(subscribe_id), KEY)
    ext_obj = {"xid": xid}
    if max_id >= 0:
        ext_obj["max-id"] = max_id
    ext = json.dumps(ext_obj, separators=(",", ":")).encode()
    packet = build_packet(SUBSCRIBE_CMD, body, VERSION, SESSION_ID, SEQ_BASE, ext=ext)
    print("packet_len=%d" % len(packet))
    print("packet_hex=%s" % packet.hex())
    for url in URLS:
        try:
            start = time.time()
            resp = requests.post(url, data=packet, timeout=timeout)
            print("%s status=%s len=%d elapsed=%.1f" % (
                url, resp.status_code, len(resp.content), time.time() - start
            ))
            print("  body=%r" % resp.content[:1000])
        except Exception as exc:
            print("%s error=%s" % (url, exc))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("subscribe_id")
    parser.add_argument("--xid", type=int, default=5)
    parser.add_argument("--max-id", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    main(args.subscribe_id, args.xid, args.max_id, args.timeout)
