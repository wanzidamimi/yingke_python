# -*- coding: utf-8 -*-
"""从当前在线的新版 JS chunk 中找 WebSocket / 弹幕连接逻辑。仅学习研究。"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from curl_cffi import requests
KW = {"impersonate": "chrome"}

# 拿房间页 HTML，提取所有 chunk js
html = requests.get("https://www.inke.cn/liveroom/index.html?uid=763972916", timeout=20, **KW).text
js_files = re.findall(r'(?:src=)?["\']([^"\']+\.js)["\']', html)
js_files = [u if u.startswith('http') else 'https:' + u if u.startswith('//') else 'https://www.inke.cn/' + u for u in js_files]
print("JS 文件数:", len(js_files))

patterns = [r'wss?://', r'getSoketUrl', r'socket', r'chatroom', r'sio_url', r'danmaku']
for url in js_files:
    if 'webcdn.inke.cn' not in url:
        continue
    try:
        js = requests.get(url, timeout=20, **KW).text
    except Exception as e:
        continue
    hits = {}
    for pat in patterns:
        n = len(re.findall(pat, js, re.I))
        if n:
            hits[pat] = n
    if hits:
        print("\n", url.split('/')[-1], "len", len(js), hits)
        # 打印 wss/chatroom 上下文
        for m in list(re.finditer(r'.{150}(?:wss?://|chatroom\.inke\.cn|sio_url|getSoketUrl).{250}', js, re.I))[:5]:
            print("   ", m.group(0).replace("\n", " ")[:400])
