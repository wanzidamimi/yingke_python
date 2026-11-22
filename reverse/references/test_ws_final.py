# -*- coding: utf-8 -*-
"""最后尝试：完整浏览器头 + 保持 URL 原样连接。仅学习研究。"""
import json, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
import websocket

KW = {"impersonate": "chrome"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

s = requests.Session()
# 先访问房间页建立 cookie
uid = "771687341"
s.get("https://www.inke.cn/liveroom/index.html?uid=%s" % uid, timeout=15, impersonate="chrome")
d = s.get("https://chatroom.inke.cn/url",
          params={"roomid": uid, "uid": uid, "id": uid, "access_from": "pc_web"},
          headers={"Referer": "https://www.inke.cn/liveroom/index.html?uid=%s" % uid,
                   "User-Agent": UA},
          timeout=15, impersonate="chrome").json()
ws_url = d["url"]
cookie = "; ".join("%s=%s" % (k, v) for k, v in s.cookies.items())
print("cookie:", cookie)
print("url:", ws_url[:180])

hdrs = [
    "GET %s HTTP/1.1" % ws_url.split("chatroom.inke.cn")[1],
    "Host: chatroom.inke.cn",
    "Upgrade: websocket",
    "Connection: Upgrade",
    "Sec-WebSocket-Version: 13",
    "Origin: https://www.inke.cn",
    "Referer: https://www.inke.cn/",
    "User-Agent: %s" % UA,
    "Cookie: %s" % cookie,
]

# 尝试 1: 完整头
for attempt, header in [
    ("full", hdrs),
    ("origin-only", ["Origin: https://www.inke.cn", "User-Agent: " + UA, "Cookie: " + cookie]),
    ("no-origin", ["User-Agent: " + UA]),
]:
    try:
        w = websocket.create_connection(ws_url, timeout=10, header=header, suppress_origin=True)
        print("SUCCESS", attempt)
        w.settimeout(5)
        end = time.time() + 20
        n = 0
        while time.time() < end and n < 10:
            try:
                raw = w.recv()
                if raw:
                    print("MSG:", raw[:250])
                    n += 1
            except Exception as e:
                if "timed out" not in str(e).lower():
                    print("recv err:", repr(e)[:80])
                break
        w.close()
        raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as e:
        print("FAIL", attempt, repr(e)[:100])
