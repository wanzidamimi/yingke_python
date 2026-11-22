# -*- coding: utf-8 -*-
"""端到端：先连 SSE，再启动采集，读取全部事件。"""
import sys, io, time, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests

BASE = "http://127.0.0.1:8801"
UID = "756130001"

def sse_reader():
    try:
        r = requests.get(BASE + "/api/events", stream=True, timeout=40)
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                print("EVENT:", line[6:][:300], flush=True)
    except Exception as e:
        print("SSE ERR:", repr(e)[:100], flush=True)

t = threading.Thread(target=sse_reader, daemon=True)
t.start()
time.sleep(1)
print("START:", requests.post(BASE + "/api/start", json={"room": UID}, timeout=10).text, flush=True)
time.sleep(25)
print("STATUS:", requests.get(BASE + "/api/status", timeout=5).text, flush=True)
