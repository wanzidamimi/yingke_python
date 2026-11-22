import gzip
import os
import re
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LOG_DIR = r'd:/Scrapy-project/yingke_python/reverse/logs'
NEEDLE_ASCII = re.compile(rb'"tp"\s*:\s*"(pp|pub)"')
NEEDLE_TEXT = [s.encode('utf-8') for s in ['来了', '来啦', '不让你为难了', '小为']]


def needle_matches(data):
    if NEEDLE_ASCII.search(data):
        return True
    return any(x in data for x in NEEDLE_TEXT)
KEYS = [
    b'0c2a616bfd8442aec0495d04d3ae3599',
    b'ehebecee', b'dbebdhgd', b'cbefcbhe',
]

EPB = 0x00000006
SPB = 0x00000003


def rc4(data, key):
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xff
        S[i], S[j] = S[j], S[i]
    out = bytearray()
    i = j = 0
    for c in data:
        i = (i + 1) & 0xff
        j = (j + S[i]) & 0xff
        S[i], S[j] = S[j], S[i]
        out.append(c ^ S[(S[i] + S[j]) & 0xff])
    return bytes(out)


def variants(data):
    out = [('raw', data)]
    for k in KEYS:
        out.append(('rc4:' + k.decode(), rc4(data, k)))
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


def tcp_payload(packet, linktype=1):
    if not packet:
        return None
    if linktype == 1:
        if len(packet) < 34 or struct.unpack_from('>H', packet, 12)[0] != 0x0800:
            return None
        ip_off = 14
        proto = packet[23]
    elif linktype == 113:  # Linux cooked capture
        if len(packet) < 32:
            return None
        if struct.unpack_from('>H', packet, 14)[0] != 0x0800:
            return None
        ip_off = 16
        proto = packet[23 + 2]  # SLL adds 2 bytes before IP
    else:
        return None
    if proto != 6:
        return None
    ihl = (packet[ip_off] & 0x0F) * 4
    tcp_off = ip_off + ihl
    if len(packet) < tcp_off + 20:
        return None
    src, dst = struct.unpack_from('>HH', packet, tcp_off)
    data_off = (packet[tcp_off + 12] >> 4) * 4
    payload = packet[tcp_off + data_off:]
    if not payload:
        return None
    return src, dst, payload


def pcapng_packets(data):
    off = 0
    while off + 12 <= len(data):
        btype, blen = struct.unpack_from('<II', data, off)
        if blen < 12 or off + blen > len(data):
            break
        body = data[off + 8:off + blen - 4]
        packet = None
        if btype == EPB and len(body) >= 20:
            cap_len = struct.unpack_from('<I', body, 12)[0]
            packet = body[20:20 + cap_len]
        elif btype == SPB and len(body) >= 4:
            cap_len = struct.unpack_from('<I', body, 0)[0]
            packet = body[4:4 + cap_len]
        if packet:
            yield packet, 1
        off += blen


def pcap_packets(data):
    if len(data) < 24:
        return
    magic = data[:4]
    if magic == b'\xd4\xc3\xb2\xa1':
        endian = '<'
        linktype = struct.unpack_from('<I', data, 20)[0]
    elif magic == b'\xa1\xb2\xc3\xd4':
        endian = '>'
        linktype = struct.unpack_from('<I', data, 20)[0]
    elif magic == b'\x4d\x3c\xb2\xa1':
        endian = '<'
        linktype = struct.unpack_from('<I', data, 20)[0] & 0xffff
    elif magic == b'\xa1\xb2\x3c\x4d':
        endian = '>'
        linktype = struct.unpack_from('<I', data, 20)[0] >> 16
    else:
        return
    off = 24
    while off + 16 <= len(data):
        _, _, caplen, _ = struct.unpack_from(endian + 'IIII', data, off)
        off += 16
        packet = data[off:off + caplen]
        off += caplen
        if packet:
            yield packet, linktype


def packets(path):
    data = open(path, 'rb').read()
    raw_hits = [x.decode('utf-8', 'replace') for x in NEEDLE_TEXT if x in data]
    if NEEDLE_ASCII.search(data):
        raw_hits.append('tp=pp/pub')
    if raw_hits:
        print('RAW_HITS', os.path.basename(path), raw_hits[:5])
    if path.endswith('.pcapng'):
        return pcapng_packets(data)
    return pcap_packets(data)


def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = sorted(
            os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR)
            if f.endswith(('.pcap', '.pcapng'))
        )
    for path in files:
        if os.path.getsize(path) == 0:
            continue
        total = 0
        hits = 0
        print('FILE', os.path.basename(path))
        for packet, linktype in packets(path):
            parsed = tcp_payload(packet, linktype)
            if not parsed:
                continue
            src, dst, payload = parsed
            total += 1
            for name, data in variants(payload):
                if not needle_matches(data):
                    continue
                hits += 1
                print('  HIT %d->%d via=%s cmd=%s len=%d ctx=%s' % (
                    src, dst, name,
                    payload[4:6].hex() if len(payload) > 6 else '?',
                    len(data),
                    data[:1000].decode('utf-8', 'replace')
                ))
                break
        print('  tcp_packets=%d hits=%d' % (total, hits))


if __name__ == '__main__':
    main()
