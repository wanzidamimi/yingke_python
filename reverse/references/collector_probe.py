# -*- coding: utf-8 -*-
"""直接测 InkeDanmu 采集器：不加 liveid 过滤，验证消息能回调。"""
import sys, io, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from inke_danmu import InkeDanmu

got = []
def cb(m):
    got.append(m)
    if len(got) <= 5:
        print("MSG:", m.get("kind"), m.get("category_label"), m.get("user"), m.get("text", "")[:50], flush=True)

c = InkeDanmu(on_message=cb)  # 无过滤
pid = c.start()
print("PID", pid, "alive", c.alive, flush=True)
time.sleep(20)
c.stop()
print("TOTAL", len(got), flush=True)
