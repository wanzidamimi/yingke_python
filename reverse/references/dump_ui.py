#!/usr/bin/env python3
import re
import subprocess
import sys

path = sys.argv[1] if len(sys.argv) > 1 else '/sdcard/ui.xml'
raw = subprocess.check_output([
    'adb', '-s', '127.0.0.1:5555', 'exec-out', 'cat', path
])
text = raw.decode('utf-8', 'replace')
for m in re.finditer(r'text="([^"]+)"[^>]*?bounds="([^"]+)"', text):
    label, bounds = m.group(1), m.group(2)
    if label:
        print(label, bounds)
