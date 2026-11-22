# -*- coding: utf-8 -*-
"""提取 get chatroom url 附近的完整代码，找 WebSocket 地址接口。"""
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

# 找 "get chatroom url" 前后各 3000 字符
for kw in ["get chatroom url error", "getChatroomUrl", "chatroomUrl", "chat_room_url", "onMessage(JSON.parse"]:
    idx = js.find(kw)
    print("\n" + "=" * 70)
    print("KW", kw, "at", idx)
    if idx < 0:
        continue
    seg = js[max(0, idx - 3000): idx + 800]
    print(seg)
