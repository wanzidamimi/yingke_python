# -*- coding: utf-8 -*-
"""找当前房间页实际使用的 JS 版本，搜 socket.io / sio_url / chatroom 连接。仅学习研究。"""
import re
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
KW = {"impersonate": "chrome"}

# 房间页 HTML
url = "https://www.inke.cn/liveroom/index.html?uid=771687341"
r = requests.get(url, timeout=20, **KW)
html = r.text
print("HTML len", len(html))
# 找所有 js 文件
js_files = re.findall(r'src=["\']([^"\']+\.js[^"\']*)["\']', html)
print("JS files:")
for j in js_files[:20]:
    print("  ", j)
# 找 chunk 名
chunks = re.findall(r'(liveroom[^"\']+\.js)', html)
print("liveroom chunks:", set(chunks))
