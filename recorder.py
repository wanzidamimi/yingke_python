# -*- coding: utf-8 -*-
"""会话录制：连接→停止期间累计消息并导出 CSV（UTF-8-BOM）。"""
import csv
import re
import threading
import time
from pathlib import Path

EXPORT_DIR = Path(__file__).parent / "exports"
FIELDS = ["time", "category", "category_label", "message_type", "user", "content", "text", "seq"]


class SessionRecorder:
    def __init__(self, export_dir=EXPORT_DIR):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._rows = []
        self._room = ""
        self._started = ""

    def begin(self, room):
        with self._lock:
            self._room = room or ""
            self._started = time.strftime("%Y-%m-%d %H:%M:%S")
            self._rows = []

    def add(self, msg):
        if msg.get("kind") != "danmu" and msg.get("kind") != "binary":
            return
        with self._lock:
            self._rows.append({
                "time": msg.get("ts") or time.strftime("%Y-%m-%d %H:%M:%S"),
                "category": msg.get("category") or "",
                "category_label": msg.get("category_label") or "",
                "message_type": msg.get("message_type") or "",
                "user": msg.get("user") or "",
                "content": msg.get("content") or "",
                "text": msg.get("text") or "",
                "seq": msg.get("seq") if msg.get("seq") is not None else "",
            })

    @property
    def count(self):
        with self._lock:
            return len(self._rows)

    def save(self):
        with self._lock:
            rows = list(self._rows)
            room = self._room
        if not rows:
            return None
        stamp = time.strftime("%Y%m%d_%H%M%S")
        safe_room = re.sub(r"\W+", "_", room)[-24:].strip("_") or "room"
        path = self.export_dir / f"inke_{safe_room}_{stamp}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    @classmethod
    def list_files(cls, export_dir=EXPORT_DIR):
        d = Path(export_dir)
        d.mkdir(parents=True, exist_ok=True)
        out = []
        for p in sorted(d.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(p, encoding="utf-8-sig", errors="replace") as f:
                    rows = max(sum(1 for _ in f) - 1, 0)
            except OSError:
                rows = 0
            st = p.stat()
            out.append({
                "name": p.name, "size": st.st_size, "rows": rows,
                "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
            })
        return out

    @classmethod
    def path_for(cls, name, export_dir=EXPORT_DIR):
        d = Path(export_dir).resolve()
        p = (d / name).resolve()
        if d not in p.parents or p.suffix.lower() != ".csv" or not p.is_file():
            return None
        return p
