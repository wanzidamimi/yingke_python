# -*- coding: utf-8 -*-
"""深挖 chatroom.inke.cn 相关的 WebSocket 弹幕连接逻辑（仅学习研究）。"""
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
r = requests.get(URL, timeout=20, **KW)
js = r.text
print("JS len", len(js))

# 1) chatroom.inke.cn 上下文
print("\n=== chatroom.inke.cn contexts ===")
for m in re.finditer(r'.{200}chatroom\.inke\.cn.{400}', js, re.I):
    print("---")
    print(m.group(0).replace("\n", " ")[:650])

# 2) 搜 pub_chat / 连接相关配置
for kw in ["pub_chat", "socket", "connect", "wsUrl", "ws_url", "wechat", "chatroom"]:
    print("\n=== keyword: %s ===" % kw)
    cnt = 0
    for m in re.finditer(r'.{120}' + re.escape(kw) + r'.{250}', js, re.I):
        print("  ", m.group(0).replace("\n", " ")[:380])
        cnt += 1
        if cnt >= 6:
            break

# 3) 找所有 inke.cn 域名
print("\n=== all inke.cn domains ===")
doms = set(re.findall(r'[a-z0-9.\-]+\.inke\.cn', js, re.I))
for d in sorted(doms):
    print("  ", d)
