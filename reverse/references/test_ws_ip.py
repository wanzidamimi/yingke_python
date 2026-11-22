# -*- coding: utf-8 -*-
"""诊断出口 IP 与 sec 签名绑定问题。仅学习研究。"""
import sys
import io
import socket
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 1) 本机出口 IP（curl_cffi）
from curl_cffi import requests
for url in ["https://api.ipify.org", "https://myip.ipip.net"]:
    try:
        r = requests.get(url, timeout=10, impersonate="chrome")
        print("%s -> %s" % (url, r.text[:120]))
    except Exception as e:
        print(url, "ERR", repr(e)[:80])

# 2) DNS 解析 chatroom.inke.cn
print("\nDNS chatroom.inke.cn:")
try:
    for res in socket.getaddrinfo("chatroom.inke.cn", 443, 0, socket.SOCK_STREAM):
        print("  ", res[4])
except Exception as e:
    print("  ERR", repr(e))

# 3) 对比 URL 里的 xrealip
from curl_cffi import requests as r2
liveid, uid = "1795004103423719", "771687341"
d = r2.get("https://chatroom.inke.cn/url",
           params={"roomid": liveid, "uid": uid, "id": liveid, "access_from": "pc_web"},
           headers={"Referer": "https://www.inke.cn/"}, timeout=15, impersonate="chrome").json()
from urllib.parse import urlparse, parse_qsl
q = dict(parse_qsl(urlparse(d["url"]).query))
print("\nURL 里的 xrealip:", q.get("xrealip"))
