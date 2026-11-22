# -*- coding: utf-8 -*-
"""从映客官网前端 JS 里挖 WebSocket 弹幕地址（仅学习研究）。"""
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

# 1) 房间脚本（审计文档提到的）
SCRIPTS = [
    "https://webcdn.inke.cn/www.inke.cn.live/static/js/liveroom.www.a6740050e.chunk.js",
    "https://www.inke.cn/js/new-cn.js?v=20250226",
]
pat_ws = re.compile(r'wss?://[^\s"\'`<>\\]+')
pat_keyword = re.compile(r'.{80}(?:websocket|WebSocket|wss://|ws://|socket\.io|livews|imserver|chat).{120}', re.I)

for url in SCRIPTS:
    print("\n" + "=" * 70)
    print("FETCH", url)
    try:
        r = requests.get(url, timeout=20, **KW)
        print("status", r.status_code, "len", len(r.content))
        js = r.text
    except Exception as e:
        print("ERR", repr(e))
        continue

    hits = set(pat_ws.findall(js))
    print("\n-- ws/wss URLs (%d) --" % len(hits))
    for h in sorted(hits)[:40]:
        print("  ", h[:200])

    print("\n-- websocket keyword contexts --")
    ctxs = []
    for m in pat_keyword.finditer(js):
        c = m.group(0).replace("\n", " ")
        if c not in ctxs:
            ctxs.append(c)
    for c in ctxs[:25]:
        print("  ", c[:220])
