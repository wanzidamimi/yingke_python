"""按 TCP 流重组后解析映客私有帧，避免跨包 body 被漏掉。"""
import gzip
import os
import re
import struct
import sys
import zlib

from app_tcp_client import rc4

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

KEYS = ['0c2a616bfd8442aec0495d04d3ae3599', 'ehebecee', 'dbebdhgd', 'cbefcbhe']
NEEDLE_ASCII = re.compile(rb'"tp"\s*:\s*"(pp|pub|chat)"')
NEEDLE_TEXT = [s.encode('utf-8') for s in ['来了', '来啦', '不让你为难了', '小为']]


def needle_match(data):
    return bool(NEEDLE_ASCII.search(data) or any(x in data for x in NEEDLE_TEXT))
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


def pcapng_packets(data):
    for btype, body in blocks(data):
        if btype == EPB and len(body) >= 20:
            caplen = struct.unpack_from('<I', body, 12)[0]
            yield body[20:20 + caplen], 1
        elif btype == SPB and len(body) >= 4:
            caplen = struct.unpack_from('<I', body, 0)[0]
            yield body[4:4 + caplen], 1


def pcap_packets(data):
    if len(data) < 24:
        return
    magic = data[:4]
    if magic == b'\xd4\xc3\xb2\xa1':
        endian, linktype = '<', struct.unpack_from('<I', data, 20)[0]
    elif magic == b'\xa1\xb2\xc3\xd4':
        endian, linktype = '>', struct.unpack_from('<I', data, 20)[0]
    elif magic == b'\x4d\x3c\xb2\xa1':
        endian, linktype = '<', struct.unpack_from('<I', data, 20)[0] & 0xffff
    elif magic == b'\xa1\xb2\x3c\x4d':
        endian, linktype = '>', struct.unpack_from('<I', data, 20)[0] >> 16
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


def ip_tcp(packet, linktype):
    if not packet:
        return None
    if linktype == 1:
        if len(packet) < 34 or struct.unpack_from('>H', packet, 12)[0] != 0x0800:
            return None
        ip_off = 14
    elif linktype == 113:
        if len(packet) < 32 or struct.unpack_from('>H', packet, 14)[0] != 0x0800:
            return None
        ip_off = 16
    else:
        return None
    version = packet[ip_off] >> 4
    if version == 4:
        ihl = (packet[ip_off] & 0x0F) * 4
        if packet[ip_off + 9] != 6:
            return None
        src = '.'.join(str(x) for x in packet[ip_off + 12:ip_off + 16])
        dst = '.'.join(str(x) for x in packet[ip_off + 16:ip_off + 20])
        tcp_off = ip_off + ihl
    elif version == 6:
        if packet[ip_off + 6] != 6:
            return None
        src = packet[ip_off + 8:ip_off + 24].hex()
        dst = packet[ip_off + 24:ip_off + 40].hex()
        tcp_off = ip_off + 40
    else:
        return None
    if len(packet) < tcp_off + 20:
        return None
    sport, dport, seq = struct.unpack_from('>HHI', packet, tcp_off)
    doff = (packet[tcp_off + 12] >> 4) * 4
    payload = packet[tcp_off + doff:]
    if not payload:
        return None
    return src, sport, dst, dport, seq, payload


def reassemble(path):
    data = open(path, 'rb').read()
    packets = pcapng_packets(data) if path.endswith('.pcapng') else pcap_packets(data)
    streams = {}
    for packet, linktype in packets:
        parsed = ip_tcp(packet, linktype)
        if not parsed:
            continue
        src, sport, dst, dport, seq, payload = parsed
        key = (src, sport, dst, dport)
        m = streams.setdefault(key, {})
        if seq not in m or len(payload) > len(m[seq]):
            m[seq] = payload
    for key, segs in streams.items():
        out = bytearray()
        for seq in sorted(segs):
            piece = segs[seq]
            if not out:
                out.extend(piece)
                continue
            expected = seq
            # append when contiguous with current end; compute start from first seq
            # simplest: rebuild from min seq and skip overlaps
        # rebuild strictly
        minseq = min(segs)
        cur = minseq
        out = bytearray()
        for seq in sorted(segs):
            piece = segs[seq]
            if seq > cur:
                break
            start = max(0, cur - seq)
            if start < len(piece):
                out.extend(piece[start:])
                cur = seq + len(piece)
        yield key, bytes(out)


def variants(body):
    out = [('raw', body)]
    if body[:2] == b'\x1f\x8b':
        try:
            out.append(('gzip', gzip.decompress(body)))
        except Exception:
            pass
    for key in KEYS:
        dec = rc4(body, key)
        out.append(('rc4:' + key, dec))
        try:
            out.append(('rc4/gzip:' + key, gzip.decompress(dec)))
        except Exception:
            pass
    return out


def parse_frames(stream):
    off = 0
    frames = []
    while off + 22 <= len(stream):
        mark = stream[off]
        if mark not in (0x89, 0x09):
            off += 1
            continue
        blen = int.from_bytes(stream[off + 18:off + 22], 'big')
        # ext length is last 4 bytes after body; tolerate it when present
        total = 22 + blen
        if blen < 0 or off + total + 4 <= len(stream):
            ext_len = int.from_bytes(stream[off + total:off + total + 4], 'big')
            if 0 <= ext_len <= 4096 and off + total + 4 + ext_len <= len(stream):
                total += 4 + ext_len
        if blen < 0 or off + total > len(stream):
            off += 1
            continue
        frame = stream[off:off + total]
        frames.append(frame)
        off += total
    return frames, off


def main():
    for path in sys.argv[1:]:
        print('FILE', os.path.basename(path))
        total_frames = 0
        parsed = 0
        hits = 0
        types = {}
        for key, stream in reassemble(path):
            if len(stream) < 22:
                continue
            if 1300 not in (key[1], key[3]):
                continue
            frames, used = parse_frames(stream)
            total_frames += len(frames)
            for frame in frames:
                body_len = int.from_bytes(frame[18:22], 'big')
                body = frame[22:22 + body_len]
                for name, data in variants(body):
                    if needle_match(data):
                        hits += 1
                        print(' HIT', key, frame[4:6].hex(), name, data[:1200].decode('utf-8', 'replace'))
                        break
                # count tp values
                for name, data in variants(body):
                    if name not in ('gzip',) and not name.startswith('rc4/gzip'):
                        continue
                    try:
                        text = data.decode('utf-8')
                    except Exception:
                        continue
                    for m in re.finditer(rb'"tp"\s*:\s*"([^"]+)"', data):
                        tp = m.group(1).decode('utf-8', 'replace')
                        types[tp] = types.get(tp, 0) + 1
                    parsed += 1
                    break
        print(' frames=%d parsed=%d hits=%d types=%s' % (total_frames, parsed, hits, types))


if __name__ == '__main__':
    main()
