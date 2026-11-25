import copy
import json
import socket
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:/Scrapy-project/yingke_python")

from app_tcp_client import GATEWAYS, build_handshake_wrapped, find_packet, make_nonce, parse_packet, rc4
from inke_tcp_collector import build_auth_packet, decode_body, load_runtime_config

LIVEID = "1795437498494586"
BASE = load_runtime_config()
REAL_GID = "<redacted>"


def set_gid(cfg, gid):
    cfg["gid"] = gid
    cfg["auth"]["gid"] = gid
    cfg["auth"]["bus_buf"]["gid"] = gid
    return cfg


def run(label, gid):
    cfg = copy.deepcopy(BASE)
    set_gid(cfg, gid)
    nonce = make_nonce()
    handshake, _ = build_handshake_wrapped(int(cfg["uid"]), nonce=nonce)
    print("\nMODE", label, "gid_tail", gid[-8:], flush=True)
    for target in GATEWAYS:
        try:
            s = socket.create_connection(target, timeout=5)
        except OSError:
            continue
        s.sendall(handshake)
        s.settimeout(8)
        buf = bytearray()
        pkt = None
        end = time.time() + 8
        while time.time() < end:
            f = find_packet(buf)
            if f:
                pkt = parse_packet(f[1])
                break
            try:
                b = s.recv(4096)
            except socket.timeout:
                break
            if not b:
                break
            buf.extend(b)
        if not pkt:
            s.close()
            continue
        key = json.loads(rc4(pkt["body"], nonce).decode())["key"]
        s.sendall(build_auth_packet(key, cfg))
        end = time.time() + 8
        auth = None
        while time.time() < end:
            f = find_packet(buf)
            if f:
                start, raw = f
                del buf[:start + len(raw)]
                q = parse_packet(raw)
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
            print("AUTH", auth["res"], plain[:300] if plain else None, flush=True)
        else:
            print("AUTH none", flush=True)
        s.close()
        return


run("empty", "")
run("old", BASE.get("gid") or "")
run("device-real", REAL_GID)
