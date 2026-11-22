#!/usr/bin/env python3
"""重放真实握手包，用恢复出的 nonce 解密响应，再发送订阅包。"""
import argparse
import json
import socket
import sys
import time

from app_tcp_client import (
    GATEWAYS,
    build_subscribe_packet,
    find_packet,
    make_token,
    parse_packet,
    rc4,
)
from parse_pktmon_pcap import payloads

CAPTURED_NONCE = "ehebecee"


def find_handshake(path):
    pl = payloads(path)
    return next((p for s, d, p in pl if s != 1300 and len(p) == 203), None)


def find_client_cmd(path, cmd):
    pl = payloads(path)
    return next((
        p for s, d, p in pl
        if s != 1300 and len(p) > 20 and p[4:6] == cmd.to_bytes(2, 'big')
    ), None)


def read_one(sock, buf, timeout=10):
    import struct
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


def main(pcapng, subscribe_id, listen, nonce=CAPTURED_NONCE):
    handshake = find_handshake(pcapng)
    if not handshake:
        print('handshake not found')
        return
    print('handshake=%d bytes' % len(handshake))
    for target in GATEWAYS:
        try:
            sock = socket.create_connection(target, timeout=5)
        except OSError as exc:
            print('connect %s failed: %s' % (target, exc))
            continue
        print('connected', target)
        try:
            sock.sendall(handshake)
            buf = bytearray()
            packet = read_one(sock, buf)
            if not packet:
                print('no handshake response')
                continue
            plain = rc4(packet['body'], nonce)
            info = json.loads(plain.decode('utf-8'))
            key = info['key']
            print('handshake key=%s' % key)

            auth = find_client_cmd(pcapng, 0x4004)
            if auth:
                print('auth packet=%d bytes' % len(auth))
                sock.sendall(auth)
            else:
                print('auth packet not found')

            sub, meta = build_subscribe_packet(subscribe_id, key)
            print('subscribe packet=%s' % sub.hex())
            sock.sendall(sub)

            deadline = time.time() + listen
            cmd_counts = {}
            while time.time() < deadline:
                packet = read_one(sock, buf, timeout=max(1, int(deadline - time.time())))
                if not packet:
                    break
                cmd_counts[packet['cmd']] = cmd_counts.get(packet['cmd'], 0) + 1
                if packet['cmd'] == 0xB002:
                    try:
                        import gzip
                        plain_msg = gzip.decompress(packet['body'])
                        print('[recv] cmd=0xb002 gzip=%s' % plain_msg[:1000].decode('utf-8', errors='replace'))
                    except Exception as exc:
                        print('[recv] cmd=0xb002 gzip error=%s raw=%s' % (
                            exc, packet['body'][:80].hex()
                        ))
                else:
                    print('[recv] cmd=0x%04x len=%d raw=%s' % (
                        packet['cmd'], len(packet['body']), packet['body'][:80].hex()
                    ))
            print('cmd_counts=%s' % cmd_counts)
            return
        except OSError as exc:
            print('socket error:', exc)
        finally:
            sock.close()
    print('all gateways failed')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('pcapng')
    parser.add_argument('subscribe_id')
    parser.add_argument('--listen', type=int, default=30)
    parser.add_argument('--nonce', default=CAPTURED_NONCE)
    args = parser.parse_args()
    main(args.pcapng, args.subscribe_id, args.listen, args.nonce)
