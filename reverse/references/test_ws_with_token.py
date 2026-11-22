# -*- coding: utf-8 -*-
"""尝试用 App 里提取的凭证填入 /url 的 token/sid，看 WS 能否握手。仅学习研究。"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from curl_cffi import requests
import websocket
KW = {"impersonate": "chrome"}

top = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
lid, uid = room["live_id"], room["uid"]
print("房间 liveid=%s uid=%s" % (lid, uid))

# 从 App 提取的凭证
SESSION_ID = "f48c885551a262f40249d078380bf5b4"   # track.session.manager.SESSION_ID
GID = "85c8b4a5ac8f203e618e3e25244b3823"           # conn_gid-tcp-779252212

def test(label, extra):
    p = {"roomid": lid, "uid": uid, "id": lid, "access_from": "pc_web"}
    p.update(extra)
    try:
        d = requests.get("https://chatroom.inke.cn/url", params=p,
                         headers={"Referer": "https://www.inke.cn/"}, timeout=15, **KW).json()
        url = d.get("url", "")
        from urllib.parse import urlparse, parse_qsl
        q = dict(parse_qsl(urlparse(url).query))
        print("\n[%s] dm_error=%s token=%r sid=%r session=%r" % (
            label, d.get("dm_error"), q.get("token"), q.get("sid"), q.get("session")))
        try:
            ws = websocket.create_connection(url, timeout=6)
            print("[%s] >>> WS 握手成功!" % label)
            ws.close()
            return True
        except Exception as e:
            print("[%s] WS: %s" % (label, "invalid" if "invalid parameters" in str(e) else str(e)[:50]))
    except Exception as e:
        print("[%s] ERR %s" % (label, repr(e)[:60]))
    return False

test("baseline", {})
test("token=SESSION_ID", {"token": SESSION_ID})
test("sid=SESSION_ID", {"sid": SESSION_ID})
test("token=GID", {"token": GID})
test("token+token=GID", {"token": GID, "session": "10000"})
