import gzip
import struct
import sys
import zlib

PATH = sys.argv[1]
NEEDLES = [x.encode('utf-8') for x in ['测试弹幕123', '测试弹幕', '来啦来啦', '弹幕']]
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


def scan(tag, ports, data):
    for needle in NEEDLES:
        if needle in data:
            print('HIT', tag, ports, needle, data[:1000])
            return True
    return False


def main():
    data = open(PATH, 'rb').read()
    total = 0
    hits = 0
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
        total += 1
        src, dst, payload = parsed
        ports = '%d->%d' % (src, dst)
        variants = [('raw', payload)]
        for name, fn in [
            ('gzip', gzip.decompress),
            ('zlib', zlib.decompress),
            ('deflate', lambda x: zlib.decompress(x, -15)),
        ]:
            try:
                variants.append((name, fn(payload)))
            except Exception:
                pass
        for name, out in variants:
            if scan(name, ports, out):
                hits += 1
    print('tcp_payload_packets=%d hits=%d' % (total, hits))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
