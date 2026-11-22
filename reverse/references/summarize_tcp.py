import struct
import sys
from collections import Counter, defaultdict

PATH = sys.argv[1]
SHB = 0x0A0D0D0A
EPB = 0x00000006
SPB = 0x00000003


def blocks(data):
    off = 0
    while off + 12 <= len(data):
        btype, blen = struct.unpack_from('<II', data, off)
        if blen < 12 or off + blen > len(data):
            break
        yield btype, data[off + 8:off + blen - 4]
        off += blen


def any_tcp_payload(packet):
    if len(packet) < 34:
        return None
    if struct.unpack_from('>H', packet, 12)[0] != 0x0800:
        return None
    ihl = (packet[14] & 0x0F) * 4
    if packet[23] != 6:
        return None
    tcp_off = 14 + ihl
    src_port, dst_port = struct.unpack_from('>HH', packet, tcp_off)
    data_off = (packet[tcp_off + 12] >> 4) * 4
    payload = packet[tcp_off + data_off:]
    return src_port, dst_port, payload


def classify(p):
    if not p:
        return 'empty'
    if p[:3] in (b'\x16\x03\x01', b'\x16\x03\x03', b'\x17\x03\x03', b'\x15\x03\x03'):
        return 'TLS'
    if p[:2] == b'\x1f\x8b':
        return 'gzip'
    if p.startswith((b'GET ', b'POST ', b'HTTP/1.1')):
        return 'HTTP'
    if p[0] in (0x89, 0x09):
        return 'inke_binary'
    if p[0] in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08):
        return 'protobuf_or_binary'
    return 'binary'


def main():
    data = open(PATH, 'rb').read()
    counts = Counter()
    samples = {}
    kinds = defaultdict(Counter)
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
        parsed = any_tcp_payload(packet)
        if not parsed or not parsed[2]:
            continue
        src, dst, p = parsed
        for port in (src, dst):
            if port < 1024 or port in (7002, 7003, 7005, 8081):
                counts[port] += 1
                kinds[port][classify(p)] += 1
                if port not in samples:
                    samples[port] = p
    print('top_ports:')
    for port, n in counts.most_common(20):
        print('  %-6d %8d  %s' % (port, n, dict(kinds[port].most_common(4))))
    print('\nsamples:')
    for port in [p for p, _ in counts.most_common(20)]:
        p = samples.get(port, b'')
        preview = p[:48]
        try:
            ascii_preview = ''.join(chr(c) if 32 <= c < 127 else '.' for c in preview)
        except Exception:
            ascii_preview = ''
        print('  port %-6d len=%-5d kind=%-18s hex=%s ascii=%s' % (
            port, len(p), classify(p), preview.hex(), ascii_preview
        ))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
