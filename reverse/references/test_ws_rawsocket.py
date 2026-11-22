# -*- coding: utf-8 -*-
"""纯 Python 原始 socket 手写 WS 握手，强制 HTTP/1.1（ALPN），排除 HTTP/2 干扰。仅学习研究。"""
import base64, os, sys, io, socket, ssl
from urllib.parse import urlparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
KW = {"impersonate": "chrome"}

# 1) 拿 WS URL（Chrome TLS）
s = requests.Session()
top = s.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
lid, uid = room["live_id"], room["uid"]
d = s.get("https://chatroom.inke.cn/url",
          params={"roomid": lid, "uid": uid, "id": lid, "access_from": "pc_web"},
          headers={"Referer": "https://www.inke.cn/"}, timeout=15, **KW).json()
ws_url = d["url"]
p = urlparse(ws_url)
host = p.netloc
path = p.path + ("?" + p.query if p.query else "")
print("HOST:", host)
print("PATH:", path[:200])

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def try_handshake(label, extra_headers, alpn=["http/1.1"]):
    key = base64.b64encode(os.urandom(16)).decode()
    lines = [
        "GET %s HTTP/1.1" % path,
        "Host: %s" % host,
        "Connection: Upgrade",
        "Upgrade: websocket",
        "Sec-WebSocket-Key: %s" % key,
        "Sec-WebSocket-Version: 13",
    ] + extra_headers + ["", ""]
    req = "\r\n".join(lines)
    try:
        ctx = ssl.create_default_context()
        ctx.set_alpn_protocols(alpn)
        raw = socket.create_connection((host, 443), timeout=10)
        ssock = ctx.wrap_socket(raw, server_hostname=host)
        print("\n[%s] ALPN negotiated: %s" % (label, ssock.selected_alpn_protocol()))
        ssock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = ssock.recv(4096)
            if not chunk:
                break
            resp += chunk
        head = resp.split(b"\r\n\r\n")[0].decode(errors="replace")
        status = head.split("\r\n")[0]
        upgrade = [l for l in head.split("\r\n") if l.lower().startswith(("upgrade:", "sec-websocket-accept", "connection:"))]
        print("[%s] %s" % (label, status))
        print("[%s] %s" % (label, upgrade))
        ssock.close()
        return status, head
    except Exception as e:
        print("[%s] ERR %s" % (label, repr(e)[:150]))
        return None, None

# 变体
try_handshake("minimal", [])
try_handshake("browser", ["Origin: https://www.inke.cn", "User-Agent: " + UA,
                          "Sec-WebSocket-Extensions: permessage-deflate; client_max_window_bits"])
try_handshake("chatroom-origin", ["Origin: https://chatroom.inke.cn", "User-Agent: " + UA])
