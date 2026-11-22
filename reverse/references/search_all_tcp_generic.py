import gzip
import struct
import sys
import zlib

from app_tcp_client import rc4

PATH = sys.argv[1]
NEEDLE = sys.argv[2].encode()
EPB = 0x00000006
SPB = 0x00000003
KEYS = ['0c2a616bfd8442aec0495d04d3ae3599', 'ehebecee', 'dbebdhgd', 'cbefcbhe']


def blocks(data):
    off = 0
    while off + 12 <= len(data):
        btype, blen = struct.unpack_from('<II', data, off)
        if blen < 12 or off + blen > len(data):
            break
        yield btype, data[off + 8:off + blen - 4]
        off += blen


def tcp_payload(packet):
    if len(packet) < 34 or struct.unpack_from('>H', packet, 12)[0] != 0x0800:
        return None
    ihl = (packet[14] & 0x0F) * 4
    if packet[23] != 6:
        return None
    tcp = 14 + ihl
    src, dst = struct.unpack_from('>HH', packet, tcp)
    off = (packet[tcp + 12] >> 4) * 4
    return src, dst, packet[tcp + off:]


def variants(p):
    out = [('raw', p)]
    for k in KEYS:
        out.append(('rc4:' + k, rc4(p, k)))
    for name, data in list(out):
        for dec, fn in [
            ('gzip', gzip.decompress),
            ('zlib', zlib.decompress),
            ('deflate', lambda x: zlib.decompress(x, -15)),
        ]:
            try:
                out.append((name + '/' + dec, fn(data)))
            except Exception:
                pass
    return out


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
        parsed = tcp_payload(packet)
        if not parsed or not parsed[2]:
            continue
        total += 1
        src, dst, p = parsed
        for name, out in variants(p):
            if NEEDLE in out:
                hits += 1
                print('HIT %d->%d %s len=%d %s' % (src, dst, name, len(out), out[:1000]))
                break
    print('tcp_payload_packets=%d hits=%d' % (total, hits))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
