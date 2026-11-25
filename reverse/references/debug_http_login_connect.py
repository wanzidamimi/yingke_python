import json
import socket
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:/Scrapy-project/yingke_python")

from app_tcp_client import GATEWAYS, find_packet, make_nonce, parse_packet, rc4
from inke_tcp_collector import (
    build_auth_packet,
    build_room_packets,
    decode_body,
    load_runtime_config,
)

cfg = load_runtime_config()
print("uid", cfg.get("uid"), "gid_tail", str(cfg.get("gid") or "")[-8:], flush=True)
nonce = make_nonce()
handshake, meta = __import__("app_tcp_client").build_handshake_wrapped(
    int(cfg["uid"]), nonce=nonce
)
print("handshake token", meta["token"], flush=True)

for target in GATEWAYS:
    try:
        s = socket.create_connection(target, timeout=5)
    except OSError as e:
        print("connect failed", target, e, flush=True)
        continue
    print("connected", target, flush=True)
    s.sendall(handshake)
    s.settimeout(8)
    buf = bytearray()
    pkt = None
    import time
    end = time.time() + 8
    while time.time() < end:
        found = find_packet(buf)
        if found:
            pkt = parse_packet(found[1])
            break
        try:
            b = s.recv(4096)
        except socket.timeout:
            break
        if not b:
            break
        buf.extend(b)
    if not pkt:
        print("no handshake resp", flush=True)
        s.close()
        continue
    info = json.loads(rc4(pkt["body"], nonce).decode("utf-8"))
    key = info["key"]
    print("handshake resp", pkt["cmd"], "key_tail", key[-8:], flush=True)
    s.sendall(build_auth_packet(key, cfg))
    end = time.time() + 10
    auth = None
    while time.time() < end:
        found = find_packet(buf)
        if found:
            start, raw = found
            del buf[:start + len(raw)]
            q = parse_packet(raw)
            print("packet", hex(q["cmd"]), "res", q["res"], "len", len(q["body"]), flush=True)
            if q["cmd"] == 0x4004:
                auth = q
                break
            continue
        try:
            b = s.recv(4096)
        except socket.timeout:
            break
        if not b:
            break
        buf.extend(b)
    if auth:
        plain = decode_body(auth["cmd"], auth["body"], key)
        print("auth plain", plain[:1000] if plain else None, flush=True)
    else:
        print("no auth resp", flush=True)
    for packet in build_room_packets("1795437498494586", key, cfg):
        s.sendall(packet)
    s.settimeout(20)
    end = time.time() + 20
    chat = []
    while time.time() < end:
        found = find_packet(buf)
        if found:
            start, raw = found
            del buf[:start + len(raw)]
            q = parse_packet(raw)
            plain = decode_body(q["cmd"], q["body"], key)
            print("push", hex(q["cmd"]), "decoded", bool(plain), flush=True)
            if plain:
                print("push_head", plain[:300], flush=True)
            continue
        try:
            b = s.recv(4096)
        except socket.timeout:
            break
        if not b:
            break
        buf.extend(b)
    print("chat samples", chat[:5], flush=True)
    s.close()
    break
