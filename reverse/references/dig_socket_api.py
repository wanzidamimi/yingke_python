# -*- coding: utf-8 -*-
"""定位 getSoketUrl 对应的 HTTP 接口路径。"""
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from curl_cffi import requests
    KW = {"impersonate": "chrome"}
except Exception:
    import requests
    KW = {}

URL = "https://webcdn.inke.cn/www.inke.cn.live/static/js/liveroom.www.a6740050e.chunk.js"
js = requests.get(URL, timeout=20, **KW).text

# getSoketUrl 定义处：搜 "getSoketUrl" 全部出现位置
print("=== getSoketUrl occurrences ===")
for m in re.finditer(r'getSoketUrl', js):
    i = m.start()
    print("\n--- at", i, "---")
    print(js[max(0, i - 400): i + 400].replace("\n", " "))

# 搜 socket url 接口常见路径关键字
print("\n\n=== socket url path hints ===")
for kw in ["getSoketUrl:", "getSocketUrl", "socket_url", "socketUrl", "/web/", "chatroom"]:
    print("\n--", kw, "--")
    n = 0
    for m in re.finditer(re.escape(kw), js):
        i = m.start()
        seg = js[max(0, i - 150): i + 200].replace("\n", " ")
        if kw == "/web/" and "socket" not in seg.lower() and "soket" not in seg.lower():
            continue
        print("  ", seg[:350])
        n += 1
        if n >= 8:
            break
