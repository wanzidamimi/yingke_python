#!/usr/bin/env python3
"""一键抓模拟器 App 流量并汇总目标地址。

用法：
  python quick_capture.py
  python quick_capture.py --seconds 20
  python quick_capture.py --no-launch
"""
import argparse
import collections
import os
import re
import subprocess
import sys
import time

LOCAL_PCAP = r'd:/Scrapy-project/yingke_python/reverse/logs/quick_capture.pcap'
REMOTE_PCAP = '/sdcard/inke_quick.pcap'
PKG = 'com.meelive.ingkee'


def adb(args, text=False):
    out = subprocess.check_output(['adb'] + args, stderr=subprocess.STDOUT)
    return out.decode('utf-8', 'replace') if text else out


def pick_device():
    lines = adb(['devices'], True).splitlines()
    devices = [line.split('\t')[0] for line in lines if '\tdevice' in line]
    for preferred in ('127.0.0.1:5555', 'emulator-5554'):
        if preferred in devices:
            return preferred
    if not devices:
        raise RuntimeError('no adb device')
    return devices[0]


def shell(dev, cmd, check=True):
    args = ['-s', dev, 'shell', cmd]
    if check:
        return adb(args, True)
    out = subprocess.run(['adb'] + args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return out.stdout.decode('utf-8', 'replace')


def main(seconds, launch):
    dev = pick_device()
    print('device=%s' % dev)
    print('start tcpdump...')
    shell(dev, "su -c 'pkill tcpdump'", check=False)
    shell(dev, "su -c 'nohup tcpdump -i any -s 0 -w %s >/dev/null 2>&1 &'" % REMOTE_PCAP)
    time.sleep(1)
    if launch:
        shell(dev, 'am force-stop %s' % PKG)
        time.sleep(1)
        shell(dev, 'monkey -p %s -c android.intent.category.LAUNCHER 1' % PKG)
    print('capturing %ds...' % seconds)
    time.sleep(seconds)
    shell(dev, "su -c 'pkill tcpdump'", check=False)
    os.makedirs(os.path.dirname(LOCAL_PCAP), exist_ok=True)
    adb(['-s', dev, 'pull', REMOTE_PCAP, LOCAL_PCAP])
    print('pcap=%s' % LOCAL_PCAP)

    syn = shell(dev, "tcpdump -nn -r %s 'tcp[tcpflags] & tcp-syn != 0' 2>/dev/null" % REMOTE_PCAP)
    dst_counts = collections.Counter()
    for line in syn.splitlines():
        m = re.search(r'IP\s+\S+\s+>\s+(\d+\.\d+\.\d+\.\d+\.\d+):', line)
        if m:
            dst_counts[m.group(1)] += 1
    print('tcp_syn_targets=%d' % len(dst_counts))
    for dst, count in dst_counts.most_common(40):
        print('  %-24s %d' % (dst, count))

    dns = shell(dev, "tcpdump -r %s udp port 53 2>/dev/null | head -80" % REMOTE_PCAP)
    if dns.strip():
        print('dns_sample:')
        for line in dns.splitlines()[:40]:
            print('  ' + line.strip())


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--no-launch', action='store_true')
    args = parser.parse_args()
    main(args.seconds, not args.no_launch)
