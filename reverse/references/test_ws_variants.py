# -*- coding: utf-8 -*-
"""测试 WS URL 的各种变体，找出握手成功的参数组合。仅学习研究。"""
import json
import sys
import io
import time
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse, unquote
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from curl_cffi import requests
import websocket

KW = {"impersonate": "chrome"}
top = requests.get("https://webapi.busi.inke.cn/web/Live_top_pc", timeout=15, **KW).json()
room = top["data"]["list"][0]
liveid, uid = room["live_id"], room["uid"]
print("房间 liveid=%s uid=%s" % (liveid, uid))

params = {"roomid": liveid, "uid": uid, "id": liveid, "access_from": "pc_web"}
HDR = {"Referer": "https://www.inke.cn/", "Origin": "https://www.inke.cn"}
d = requests.get("https://chatroom.inke.cn/url", params=params, headers=HDR, timeout=15, **KW).json()
raw_url = d["url"]
print("原始 URL:", raw_url[:250])

# 生成变体
p = urlparse(raw_url)
q = parse_qsl(p.query, keep_blank_values=True)
print("\n原始参数:", q)

variants = {}
# v1: 原样
variants["raw"] = raw_url
# v2: 去重（保留首次）
seen = set()
q_dedup = []
for k, v in q:
    if (k, v) not in seen:
        seen.add((k, v))
        q_dedup.append((k, v))
variants["dedup"] = urlunparse(p._replace(query=urlencode(q_dedup)))
# v3: 去空值参数
q_noempty = [(k, v) for k, v in q if v != ""]
variants["noempty"] = urlunparse(p._replace(query=urlencode(q_noempty)))
# v4: 去重+去空
seen = set()
q_both = []
for k, v in q:
    if v == "" or (k, v) in seen:
        continue
    seen.add((k, v))
    q_both.append((k, v))
variants["dedup_noempty"] = urlunparse(p._replace(query=urlencode(q_both)))
# v5: 解码后再编码（%2B -> + 等）
variants["unquoted"] = unquote(raw_url)

HDRS = ["Origin: https://www.inke.cn", "Origin: https://chatroom.inke.cn"]

for name, url in variants.items():
    for hdr in HDRS:
        try:
            w = websocket.create_connection(url, timeout=8, header=[hdr])
            print("SUCCESS variant=%s hdr=%s" % (name, hdr))
            # 收几条
            w.settimeout(4)
            n = 0
            end = time.time() + 12
            while time.time() < end and n < 5:
                try:
                    raw = w.recv()
                    if raw:
                        obj = json.loads(raw)
                        print("  MSG:", json.dumps(obj, ensure_ascii=False)[:200])
                        n += 1
                except Exception as e:
                    if "timed out" not in str(e).lower():
                        print("  recv err:", repr(e)[:80])
                        break
                    break
            w.close()
            raise SystemExit(0)
        except SystemExit:
            raise
        except Exception as e:
            print("FAIL %-15s %-32s %s" % (name, hdr.split(':')[1].strip()[:30], repr(e)[:90]))
