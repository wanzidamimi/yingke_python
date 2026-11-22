#!/usr/bin/env python3
import subprocess
import sys

cmd = sys.argv[1]
devices = subprocess.check_output(['adb', 'devices']).decode('utf-8', 'replace').splitlines()
serial = next(
    (line.split('\t')[0] for line in devices if '\tdevice' in line and '127.0.0.1:5555' in line),
    next((line.split('\t')[0] for line in devices if '\tdevice' in line), 'emulator-5554')
)
out = subprocess.check_output([
    'adb', '-s', serial, 'shell', "su -c '%s'" % cmd
])
print(out.decode('utf-8', 'replace'))
