#!/usr/bin/env python3
"""从 pktmon 抓到的握手响应中穷举 App 生成的 8 位 nonce。"""
import argparse
import itertools
import json
import struct
import sys

import numpy as np
from numba import njit

from parse_pktmon_pcap import blocks, tcp_payload

ALPHABET = b"abcdefgh"


def payloads(path):
    data = open(path, 'rb').read()
    out = []
    for btype, body in blocks(data):
        packet = None
        if btype == 0x00000006 and len(body) >= 20:
            cap_len = struct.unpack_from('<I', body, 12)[0]
            packet = body[20:20 + cap_len]
        elif btype == 0x00000003 and len(body) >= 4:
            cap_len = struct.unpack_from('<I', body, 0)[0]
            packet = body[4:4 + cap_len]
        if not packet:
            continue
        parsed = tcp_payload(packet)
        if parsed and parsed[2]:
            out.append(parsed)
    return out


def outer_body(payload):
    if len(payload) < 26:
        return None
    body_len = struct.unpack_from('>I', payload, 18)[0]
    if len(payload) < 22 + body_len:
        return None
    return payload[22:22 + body_len]


@njit(cache=True)
def rc4_prefix(data, alphabet, idx, out_len):
    key = np.empty(8, dtype=np.uint8)
    n = idx
    for pos in range(8):
        key[7 - pos] = alphabet[n % 8]
        n //= 8
    s = np.arange(256, dtype=np.uint8)
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % 8]) & 0xFF
        tmp = s[i]
        s[i] = s[j]
        s[j] = tmp
    i = 0
    j = 0
    out = np.empty(out_len, dtype=np.uint8)
    for k in range(out_len):
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        tmp = s[i]
        s[i] = s[j]
        s[j] = tmp
        out[k] = data[k] ^ s[(s[i] + s[j]) & 0xFF]
    return out, key


@njit(cache=True)
def contains_key(data, alphabet, idx, out_len):
    out, key = rc4_prefix(data, alphabet, idx, out_len)
    for pos in range(out_len - 3):
        if out[pos] == 0x22 and out[pos + 1] == 0x6B and out[pos + 2] == 0x65 and out[pos + 3] == 0x79:
            return True, key
    return False, key


def find_nonce(data, prefix=b'{"key"'):
    alphabet = np.frombuffer(ALPHABET, dtype=np.uint8)
    arr = np.frombuffer(data, dtype=np.uint8)
    total = 8 ** 8
    for idx in range(total):
        ok, key = contains_key(arr, alphabet, idx, len(arr))
        if ok:
            return key.tobytes().decode('ascii'), idx
    return None, None


def main(path):
    pl = payloads(path)
    handshake = next((p for s, d, p in pl if s != 1300 and len(p) == 203), None)
    response = next((p for s, d, p in pl if s == 1300 and len(p) > 100 and p[0] == 0x09), None)
    if not handshake or not response:
        print('handshake/response not found')
        return
    body = outer_body(response)
    print('handshake_len=%d response_len=%d body_len=%d' % (
        len(handshake), len(response), len(body or b'')
    ))
    print('response_body=%s' % (body or b'').hex())
    nonce, idx = find_nonce(body)
    print('nonce=%s index=%s' % (nonce, idx))
    if nonce:
        from app_tcp_client import rc4
        plain = rc4(body, nonce)
        print('plain=%r' % plain)
        try:
            print('json=%s' % json.dumps(json.loads(plain.decode('utf-8')), ensure_ascii=False))
        except Exception as exc:
            print('json error=%s' % exc)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('pcapng')
    args = parser.parse_args()
    main(args.pcapng)
