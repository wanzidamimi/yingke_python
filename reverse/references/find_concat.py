# -*- coding: utf-8 -*-
"""找 JS 里 concat(r.url) 的 concat 函数定义。"""
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
KW = {"impersonate": "chrome"}
js = requests.get("https://webcdn.inke.cn/www.inke.cn.live/static/js/liveroom.www.a6740050e.chunk.js",
                  timeout=20, **KW).text

# 找 concat(...) 附近 + concat 定义
for m in re.finditer(r'new WebSocket\(', js):
    i = m.start()
    print("\n=== new WebSocket at", i, "===")
    print(js[i-600:i+200].replace("\n", " "))

# 找 "function concat" 或 "concat=" 定义
print("\n\n=== concat definitions ===")
for pat in [r'function concat\s*\(', r'concat\s*=\s*function', r'\.concat\s*=', r'concat\(']:
    ms = list(re.finditer(pat, js))
    print(pat, "count", len(ms))
    for m in ms[:5]:
        i = m.start()
        print("  ", js[max(0,i-100):i+250].replace("\n", " ")[:350])
