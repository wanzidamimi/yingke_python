import json
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"D:/Scrapy-project/yingke_python")

from inke_tcp_collector import InkeTcpCollector

LIVEID = sys.argv[1]
SECONDS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
counts = {"chat": 0, "member": 0, "stats": 0, "system": 0, "other": 0}
samples = []

def on_message(msg):
    if msg.get("kind") != "danmu":
        print("SYS", msg.get("text"), flush=True)
        return
    cat = msg.get("category") or "other"
    counts[cat] = counts.get(cat, 0) + 1
    if cat == "chat" and len(samples) < 10:
        samples.append("%s: %s" % (msg.get("user"), msg.get("content")))

c = InkeTcpCollector(on_message=on_message, liveid=LIVEID)
c.start()
end = time.time() + SECONDS
while time.time() < end and c.alive:
    time.sleep(0.5)
c.stop()
print("COUNTS", json.dumps(counts, ensure_ascii=False), "TOTAL", sum(counts.values()), flush=True)
for s in samples:
    print("CHAT", s, flush=True)
