#!/usr/bin/env python3
"""映客 App 私有 TCP 长连接：握手、RSA、RC4、订阅的最小复刻。

仅用于学习和授权环境下的协议分析，不处理账号鉴权或付费内容。
"""
import argparse
import base64
import hashlib
import json
import os
import random
import socket
import string
import struct
import sys
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

PUBLIC_KEY_B64 = (
    "WSQpWK0QMCaQCSl3NAOLKAEKK4QXKNMLsAULqANsEWnOg/kwLblL+ffcQlj4jQ6MCtbxP8QwU1DiXlxt7ZR7qMbzTwBGe0l/"
    "YtYMD6BmAo4ffD56iugaKaV+RRNSoRjookhIRTMpSZzLWHgZqTE49jyPQYzQCzdcSiqXbSEpQ1Ie2T/1FBXsDoPYvzFo8eaXiY51K"
    "FQBCgGPD+xbzgSNKAKL"
)
TOKEN_SALT = "::plkfuyne820icnb8"
MARK_OUT = 0x89
HANDSHAKE_CMD = 0x0001
HANDSHAKE_WRAP_CMD = 0x4003
SUBSCRIBE_CMD = 0x0100
PUBLIC_ID = 1
SESSION_ID = 10000
SEQ_BASE = 1
MSG_ID = 5
VERSION = 0x4C04
GATEWAYS = [
    ("111.13.223.188", 1300),
    ("111.13.223.167", 1300),
    ("47.95.96.98", 1300),
]


def u16(v):
    return struct.pack(">H", v & 0xFFFF)


def u32(v):
    return struct.pack(">I", v & 0xFFFFFFFF)


def lv(data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    return u16(len(data)) + data


def rot_minus_10(text):
    out = []
    for ch in text:
        if "a" <= ch <= "z":
            out.append(chr((ord(ch) - 97 - 10) % 26 + 97))
        elif "A" <= ch <= "Z":
            out.append(chr((ord(ch) - 65 - 10) % 26 + 65))
        else:
            out.append(ch)
    return "".join(out)


def load_rsa_public_key(encoded=PUBLIC_KEY_B64):
    der = base64.b64decode(rot_minus_10(encoded))
    return serialization.load_der_public_key(der)


def rsa_encrypt(data, key=None):
    key = key or load_rsa_public_key()
    return key.encrypt(data, padding.PKCS1v15())


def rc4(data, key):
    """与 App yk.a.Rc4 等价：key 为字符串，按平台默认字节编码处理。"""
    key_bytes = key.encode("utf-8")
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key_bytes[i % len(key_bytes)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    out = bytearray()
    i = j = 0
    for byte in data:
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        k = s[(s[i] + s[j]) & 0xFF]
        out.append(byte ^ k)
    return bytes(out)


def make_token(session_id):
    raw = str(session_id) + TOKEN_SALT
    return hashlib.md5(raw.encode("utf-8")).hexdigest().lower()


def make_nonce(length=8):
    # App 的 cl/c.h(8) 有 bug：取 nextInt(length % 26)，所以实际只取 a-h。
    return "".join(random.choice("abcdefgh") for _ in range(length))


def build_handshake(gid=SESSION_ID, nonce=None):
    """构造 HandshakeRequest。

    RSA 明文只有 lv(token)+lv(nonce)；
    u16(cmd)+public_id 在 RSA 密文外面。
    """
    nonce = nonce or make_nonce()
    token = make_token(gid)
    plain = lv(token) + lv(nonce)
    cipher = rsa_encrypt(plain)
    packet = u16(HANDSHAKE_CMD) + bytes([PUBLIC_ID]) + cipher
    return packet, {"gid": gid, "token": token, "nonce": nonce, "plain": plain}


def build_packet(cmd, body, version, f, g, msg_id=MSG_ID, mark=MARK_OUT, ext=b""):
    body_len = u32(len(body))
    packet = (
        bytes([mark])
        + u16(msg_id)
        + bytes([0])
        + u16(cmd)
        + u16(version)
        + u32(f)
        + u32(g)
        + u16(0)
        + body_len
        + body
        + u32(len(ext))
        + ext
    )
    return packet


def build_handshake_wrapped(gid=SESSION_ID, nonce=None):
    inner, meta = build_handshake(gid, nonce)
    ext = json.dumps(
        {"re-ack": "true", "xid": 1, "long-uid": gid},
        separators=(",", ":"),
    ).encode("utf-8")
    packet = build_packet(
        HANDSHAKE_WRAP_CMD, inner, 1, 0, SESSION_ID,
        msg_id=MSG_ID, ext=ext,
    )
    meta["wrapped"] = packet
    return packet, meta


def build_subscribe_body(subscribe_id, cmd=SUBSCRIBE_CMD):
    topic = "topic_" + subscribe_id[-2:]
    body = (
        u16(cmd)
        + lv("domain")
        + lv("group")
        + lv(topic)
        + lv(subscribe_id)
    )
    return body


def build_subscribe_packet(subscribe_id, rc4_key, session_id=SESSION_ID, seq=SEQ_BASE):
    body = build_subscribe_body(str(subscribe_id))
    encrypted = rc4(body, rc4_key)
    meta = {
        "SubscribeRequest": {
            "long-uid": session_id,
            "subscribe_id": str(subscribe_id),
        }
    }
    return build_packet(SUBSCRIBE_CMD, encrypted, VERSION, session_id, seq), meta


def find_packet(buf):
    """按抓包实测：请求 mark=0x89，响应 mark=0x09。"""
    start = -1
    for idx, byte in enumerate(buf):
        if byte in (0x89, 0x09):
            start = idx
            break
    if start < 0:
        return None
    if len(buf) - start < 22:
        return None
    body_len = struct.unpack(">I", buf[start + 18:start + 22])[0]
    ext_off = start + 22 + body_len
    if len(buf) == ext_off:
        return start, bytes(buf[start:ext_off])
    if len(buf) < ext_off + 4:
        return None
    ext_len = struct.unpack(">I", buf[ext_off:ext_off + 4])[0]
    total = ext_off + 4 + ext_len
    if len(buf) < total:
        return None
    return start, bytes(buf[start:total])


def parse_packet(packet):
    if len(packet) < 22:
        return None
    body_len = struct.unpack(">I", packet[18:22])[0]
    ext_off = 22 + body_len
    ext_len = 0
    if len(packet) >= ext_off + 4:
        ext_len = struct.unpack(">I", packet[ext_off:ext_off + 4])[0]
    return {
        "mark": packet[0],
        "msg_id": struct.unpack(">H", packet[1:3])[0],
        "flag": packet[3],
        "cmd": struct.unpack(">H", packet[4:6])[0],
        "version": struct.unpack(">H", packet[6:8])[0],
        "f": struct.unpack(">I", packet[8:12])[0],
        "g": struct.unpack(">I", packet[12:16])[0],
        "res": struct.unpack(">H", packet[16:18])[0],
        "body": packet[22:ext_off],
        "ext": packet[ext_off + 4:ext_off + 4 + ext_len],
    }


def read_packet(sock, buf, timeout=10):
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
        except (ConnectionResetError, OSError) as exc:
            print("[recv] socket error: %s" % exc)
            break
        if not chunk:
            break
        buf.extend(chunk)
    return None


def connect(gateways=GATEWAYS):
    errors = []
    for host, port in gateways:
        try:
            sock = socket.create_connection((host, port), timeout=5)
            return sock, (host, port)
        except OSError as exc:
            errors.append((host, port, str(exc)))
    raise RuntimeError("all gateways failed: %r" % (errors,))


def run(subscribe_id, session_id=SESSION_ID, gid=None, host=None, port=1300, listen=30, nonce=None):
    gateways = [(host, port)] if host else GATEWAYS
    handshake, hs_meta = build_handshake_wrapped(gid if gid is not None else SESSION_ID, nonce=nonce)
    print("[handshake] gid=%s nonce=%s token=%s" % (hs_meta["gid"], hs_meta["nonce"], hs_meta["token"]))
    print("[handshake] inner=%s" % hs_meta["plain"].hex())
    print("[handshake] final=%s" % handshake.hex())

    for target in gateways:
        try:
            sock = socket.create_connection(target, timeout=5)
        except OSError as exc:
            print("[tcp] connect %s failed: %s" % (target, exc))
            continue
        print("[tcp] connected", target)
        try:
            sock.sendall(handshake)
            buf = bytearray()
            packet = read_packet(sock, buf, timeout=10)
            if not packet:
                print("[handshake] no response from", target)
                continue
            print("[handshake] response cmd=0x%04x res=%d body_len=%d" % (
                packet["cmd"], packet["res"], len(packet["body"])
            ))
            decrypted = rc4(packet["body"], hs_meta["nonce"])
            try:
                key_info = json.loads(decrypted.decode("utf-8"))
                rc4_key = key_info["key"]
            except Exception as exc:
                print("[handshake] decode failed: %s raw=%r" % (exc, decrypted[:200]))
                continue
            print("[handshake] key=%s" % rc4_key)

            sub_packet, sub_meta = build_subscribe_packet(subscribe_id, rc4_key, session_id)
            print("[subscribe] packet=%s" % sub_packet.hex())
            print("[subscribe] meta=%s" % json.dumps(sub_meta, ensure_ascii=False))
            sock.sendall(sub_packet)

            deadline = time.time() + listen
            while time.time() < deadline:
                packet = read_packet(sock, buf, timeout=max(1, int(deadline - time.time())))
                if not packet:
                    break
                body = rc4(packet["body"], rc4_key)
                try:
                    body_text = body.decode("utf-8")
                except UnicodeDecodeError:
                    body_text = repr(body[:200])
                print("[recv] cmd=0x%04x res=%d len=%d body=%s" % (
                    packet["cmd"], packet["res"], len(packet["body"]), body_text[:1000]
                ))
            return
        finally:
            sock.close()
    print("[tcp] all gateways rejected handshake")


def self_test():
    packet, meta = build_handshake(779252212, nonce="abcdefgh")
    assert len(packet) == 131, len(packet)
    assert meta["token"] == hashlib.md5(("779252212" + TOKEN_SALT).encode()).hexdigest()
    wrapped, meta2 = build_handshake_wrapped(779252212, nonce="abcdefgh")
    parsed = parse_packet(wrapped)
    assert parsed and parsed["cmd"] == HANDSHAKE_WRAP_CMD
    assert len(wrapped) == 203, len(wrapped)
    assert b'"long_uid":779252212' in parsed["ext"]
    sub, _ = build_subscribe_packet("123456", "testkey")
    parsed = parse_packet(sub)
    assert parsed and parsed["cmd"] == SUBSCRIBE_CMD
    assert len(sub) == 26 + len(parsed["body"])
    print("[self-test] handshake/subscribe ok")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser()
    parser.add_argument("--subscribe-id", default="", help="直播间 ID / 订阅 ID")
    parser.add_argument("--session", type=int, default=SESSION_ID, help="Connection_Session 中的 session")
    parser.add_argument("--gid", type=int, default=None, help="Connection_Gid_Store 键名里的十进制 gid")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=1300)
    parser.add_argument("--listen", type=int, default=30)
    parser.add_argument("--nonce", default=None, help="固定 nonce（调试用）")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif not args.subscribe_id:
        parser.error("--subscribe-id is required unless --self-test is used")
    else:
        run(args.subscribe_id, args.session, args.gid, args.host, args.port, args.listen, args.nonce)
