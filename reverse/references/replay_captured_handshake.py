#!/usr/bin/env python3
"""重放 pktmon 抓到的原始握手包，判断服务端是否接受。"""
import socket
import sys

from parse_pktmon_pcap import payloads

GATEWAYS = [('111.13.223.167', 1300), ('111.13.223.188', 1300), ('47.95.96.98', 1300)]


def main(path):
    pl = payloads(path)
    handshake = next((p for s, d, p in pl if s != 1300 and len(p) == 203), None)
    if not handshake:
        print('handshake not found')
        return
    print('replay_len=%d' % len(handshake))
    print('replay_hex=%s' % handshake.hex())
    for target in GATEWAYS:
        try:
            s = socket.create_connection(target, timeout=5)
        except OSError as exc:
            print('connect %s failed: %s' % (target, exc))
            continue
        print('connected', target)
        try:
            s.sendall(handshake)
            s.settimeout(4)
            data = s.recv(4096)
            print('response_len=%d' % len(data))
            print('response_hex=%s' % data.hex())
        except OSError as exc:
            print('socket error:', exc)
        finally:
            s.close()
        break


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main(sys.argv[1])
