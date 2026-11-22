#!/usr/bin/env python3
"""从 pktmon 导出的 pcapng 中提取 1300 端口 TCP payload。"""
import argparse
import struct
import sys

SHB = 0x0A0D0D0A
IDB = 0x00000001
EPB = 0x00000006
SPB = 0x00000003


def blocks(data):
    off = 0
    while off + 12 <= len(data):
        btype, blen = struct.unpack_from('<II', data, off)
        if blen < 12 or off + blen > len(data):
            break
        body = data[off + 8:off + blen - 4]
        yield btype, body
        off += blen


def payloads(path, port=1300):
    data = open(path, 'rb').read()
    out = []
    for btype, body in blocks(data):
        packet = None
        if btype == EPB and len(body) >= 20:
            cap_len = struct.unpack_from('<I', body, 12)[0]
            packet = body[20:20 + cap_len]
        elif btype == SPB and len(body) >= 4:
            cap_len = struct.unpack_from('<I', body, 0)[0]
            packet = body[4:4 + cap_len]
        if not packet:
            continue
        parsed = tcp_payload(packet, port)
        if parsed and parsed[2]:
            out.append(parsed)
    return out


def tcp_payload(packet, port=1300):
    if len(packet) < 34:
        return None
    ethertype = struct.unpack_from('>H', packet, 12)[0]
    if ethertype != 0x0800:
        return None
    ihl = (packet[14] & 0x0F) * 4
    if packet[23] != 6:
        return None
    tcp_off = 14 + ihl
    src_port, dst_port = struct.unpack_from('>HH', packet, tcp_off)
    if port not in (src_port, dst_port):
        return None
    data_off = (packet[tcp_off + 12] >> 4) * 4
    payload = packet[tcp_off + data_off:]
    return src_port, dst_port, payload


def main(path, full=False):
    data = open(path, 'rb').read()
    found = []
    for btype, body in blocks(data):
        packet = None
        if btype == EPB and len(body) >= 20:
            cap_len = struct.unpack_from('<I', body, 12)[0]
            packet = body[20:20 + cap_len]
        elif btype == SPB and len(body) >= 4:
            cap_len = struct.unpack_from('<I', body, 0)[0]
            packet = body[4:4 + cap_len]
        if not packet:
            continue
        parsed = tcp_payload(packet, port)
        if parsed and parsed[2]:
            found.append(parsed)
    print('payload_packets=%d' % len(found))
    for idx, (src, dst, payload) in enumerate(found):
        if full:
            preview = payload.hex()
            suffix = ''
        else:
            preview = payload[:160].hex()
            suffix = '...' if len(payload) > 160 else ''
        print('%03d %d->%d len=%d %s%s' % (idx, src, dst, len(payload), preview, suffix))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('pcapng')
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    main(args.pcapng, args.full)
