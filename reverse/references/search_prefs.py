#!/usr/bin/env python3
import subprocess

cmd = 'grep -R -o -E "17[0-9]{15}" /data/data/com.meelive.ingkee/shared_prefs /data/data/com.meelive.ingkee/files 2>/dev/null | head -60'
out = subprocess.check_output(['adb', '-s', '127.0.0.1:5555', 'shell', 'su', '-c', cmd])
print(out.decode('utf-8', 'replace'))
