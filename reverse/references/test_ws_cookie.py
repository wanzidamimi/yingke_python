# -*- coding: utf-8 -*-
"""诊断 WS 握手：会话 cookie + 去 xrealip 等变体。仅学习研究。"""
import json
import sys
import io
import time
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests as curlreq
import websocket

liveid, uid = "1795004103423719", "771687341"
params = {"roomid": liveid, "uid": uid, "id": liveid, "access_from": "pc_web"}

# 用会话先访问房间页与 /url，保持 cookie
s = curlreq.Session()
s.get("https://www.inke.cn/", timeout=15, impersonate="chrome")
s.get("https://www.inke.cn/live/%s" % liveid, timeout=15, impersonate="chrome")
r = s.get("https://chatroom.inke.cn/url", params=params,
          headers={"Referer": "https://www.inke.cn/live/%s" % liveid},
          timeout=15, impersonate="chrome")
d = r.json()
ws_url = d["url"]
print("dm_error=%s" % d.get("dm_error"))
print("cookies:", dict(s.cookies))
print("WS URL:", ws_url)

p = urlparse(ws_url)
q = parse_qsl(p.query, keep_blank_values=True)

# cookie 字符串
cookie_str = "; ".join("%s=%s" % (k, v) for k, v in s.cookies.items())

# 变体
variants = {"raw": ws_url}
# 去 xrealip
q2 = [(k, v) for k, v in q if k != "xrealip"]
variants["no_xrealip"] = urlunparse(p._replace(query=urlencode(q2)))
# 去重去空去 xrealip
seen = set(); q3 = []
for k, v in q:
    if k == "xrealip" or v == "" or (k, v) in seen:
        continue
    seen.add((k, v)); q3.append((k, v))
variants["clean"] = urlunparse(p._replace(query=urlencode(q3)))

headers_sets = {
    "cookie+origin": ["Origin: https://www.inke.cn", "Referer: https://www.inke.cn/", "Cookie: " + cookie_str],
    "cookie+chatroom": ["Origin: https://chatroom.inke.cn", "Cookie: " + cookie_str],
    "full-browser": [
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Origin: https://www.inke.cn", "Referer: https://www.inke.cn/",
        "Accept-Language: zh-CN,zh;q=0.9", "Cookie: " + cookie_str,
    ],
}

for vname, url in variants.items():
    for hname, hdr in headers_sets.items():
        try:
            w = websocket.create_connection(url, timeout=8, header=hdr)
            print("\n*** SUCCESS v=%s h=%s ***" % (vname, hname))
            w.settimeout(5)
            end = time.time() + 15
            n = 0
            while time.time() < end and n < 8:
                try:
                    raw = w.recv()
                    if raw:
                        obj = json.loads(raw)
                        print("MSG:", json.dumps(obj, ensure_ascii=False)[:250])
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
            print("FAIL v=%-12s h=%-16s %s" % (vname, hname, repr(e)[:70]))
