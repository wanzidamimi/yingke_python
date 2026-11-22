# -*- coding: utf-8 -*-
"""分析 sec 签名构成（尝试常见 MD5 组合）。仅学习研究。"""
import hashlib, sys, io
from urllib.parse import urlparse, parse_qsl, unquote
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from curl_cffi import requests

d = requests.get("https://chatroom.inke.cn/url",
    params={"roomid": "1794998465174825", "uid": "763972916", "id": "1794998465174825", "access_from": "pc_web"},
    headers={"Referer": "https://www.inke.cn/"}, impersonate="chrome", timeout=15).json()
q = dict(parse_qsl(urlparse(d["url"]).query))
sec = q["sec"]; time_ = q["time"]; nonce = unquote(q["nonce"])
print("sec=%s time=%s nonce=%s" % (sec, time_, nonce))

cands = {
    "time+nonce": time_ + nonce,
    "nonce+time": nonce + time_,
    "md5(time)+nonce": hashlib.md5(time_.encode()).hexdigest() + nonce,
    "roomid+time+nonce": q["roomid"] + time_ + nonce,
    "nonce (raw)": nonce,
}
for name, raw in cands.items():
    for algo in ["md5", "sha1", "sha256"]:
        h = getattr(hashlib, algo)(raw.encode()).hexdigest()
        if h == sec or h[:32] == sec:
            print("MATCH!", name, algo, raw[:80])
print("\n尝试常见盐值:")
salts = ["inke", "chatinke", "chatroom", "ik", "pc_web", "inke.cn", "appshatcher"]
for salt in salts:
    for raw in [time_+nonce+salt, salt+time_+nonce, nonce+time_+salt, salt+nonce+time_]:
        if hashlib.md5(raw.encode()).hexdigest() == sec:
            print("MATCH salt=%s raw=%s" % (salt, raw[:80]))
print("done")
