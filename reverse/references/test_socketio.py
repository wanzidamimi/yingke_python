# -*- coding: utf-8 -*-
"""测试 socket.io 端点与 access_from 变体。仅学习研究。"""
import json, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
import websocket

KW = {"impersonate": "chrome"}
liveid, uid = "1795004103423719", "771687341"

# 1) 不同 access_from 看返回的 url 形态
print("=== access_from 变体 ===")
for af in ["pc_web", "web", "pc", "h5", "app", ""]:
    try:
        d = requests.get("https://chatroom.inke.cn/url",
                         params={"roomid": liveid, "uid": uid, "id": liveid, "access_from": af},
                         headers={"Referer": "https://www.inke.cn/"}, timeout=15, **KW).json()
        u = d.get("url", "")
        print("  %-8s -> %s" % (af or "(空)", u[:100]))
    except Exception as e:
        print("  %-8s ERR %s" % (af, repr(e)[:60]))

# 2) 直接 socket.io 端点
print("\n=== socket.io 端点测试 ===")
sio_urls = [
    "wss://chatroom.inke.cn/socket.io/?EIO=4&transport=websocket&roomid=%s&uid=%s" % (liveid, uid),
    "wss://chatroom.inke.cn/socket.io/?EIO=3&transport=websocket",
]
for u in sio_urls:
    try:
        w = websocket.create_connection(u, timeout=8)
        print("  SUCCESS:", u[:100])
        w.settimeout(4)
        print("  first:", w.recv()[:200])
        w.close()
    except Exception as e:
        print("  FAIL:", repr(e)[:100])
