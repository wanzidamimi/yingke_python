"""
app.py —— 映客弹幕实时显示 GUI（独立 FastAPI 服务）

启动：uvicorn app:app --host 127.0.0.1 --port 8801
浏览器打开 http://127.0.0.1:8801 ，输入直播间地址/房间号。
"""
import json
import queue
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from category import CATEGORIES
from inke_tcp_collector import InkeTcpCollector, fetch_hot_rooms, resolve_room
from recorder import SessionRecorder

STATIC = Path(__file__).parent / "static"
STATIC.mkdir(exist_ok=True)
app = FastAPI(title="映客弹幕实时显示（APP 逆向骨架）")

_queues = []
_state = {"room": "", "status": "idle", "client": None, "lock": threading.Lock()}
_recorder = SessionRecorder()


def _emit(event: dict):
    for q in list(_queues):
        try:
            q.put_nowait(event)
        except queue.Full:
            pass


def _on_message(msg: dict):
    _recorder.add(msg)
    _emit(msg)


def _run_worker(target: dict):
    room = target.get("room") or ""
    with _state["lock"]:
        _state["status"] = "connecting"
    _recorder.begin(room)
    collector = None
    try:
        uid, liveid = resolve_room(room, target.get("uid"), target.get("liveid"))
        _emit({"kind": "system", "text": f"目标房间: uid={uid or '?'} liveid={liveid or '?'}"})
        if not liveid:
            raise RuntimeError("未能解析 liveid，请直接填入 16 位 liveid 或从房间列表选择")

        _emit({"kind": "system", "text": "启动 TCP 1300 采集器…"})
        collector = InkeTcpCollector(on_message=_on_message, liveid=liveid)
        collector.start()
        with _state["lock"]:
            _state["status"] = "live"
            _state["client"] = collector
        while collector.alive:
            time.sleep(0.5)
    except Exception as e:
        _emit({"kind": "error", "text": f"采集异常: {e}"})
    finally:
        if collector:
            collector.stop()
        path = _recorder.save()
        with _state["lock"]:
            _state["status"] = "idle"
            _state["client"] = None
        if path:
            _emit({"kind": "system", "text": f"本次消息已保存: {path.name}（{_recorder.count} 条）"})
        _emit({"kind": "system", "text": "会话已结束"})


@app.get("/")
def index():
    return FileResponse(str(STATIC / "index.html"))


@app.get("/api/rooms")
async def rooms():
    return {"rooms": fetch_hot_rooms()}


@app.post("/api/resolve")
async def resolve(request: Request):
    data = await request.json()
    room = (data.get("room") or "").strip()
    uid, liveid = resolve_room(room, data.get("uid"), data.get("liveid"))
    return {"ok": bool(liveid), "uid": uid, "liveid": liveid}


@app.post("/api/start")
async def start(request: Request):
    data = await request.json()
    room = (data.get("room") or "").strip()
    uid = str(data.get("uid") or "").strip()
    liveid = str(data.get("liveid") or "").strip()
    if not room and not liveid:
        return {"ok": False, "error": "缺少直播间地址/房间号"}
    with _state["lock"]:
        if _state["status"] != "idle":
            return {"ok": False, "error": "已有会话运行中，请先停止"}
        _state["room"] = liveid or room
    target = {"room": room or liveid, "uid": uid, "liveid": liveid}
    threading.Thread(target=_run_worker, args=(target,), daemon=True).start()
    return {"ok": True}


@app.post("/api/stop")
async def stop():
    with _state["lock"]:
        client = _state["client"]
    if client:
        try:
            client.stop()
        except Exception:
            pass
    return {"ok": True}


@app.get("/api/events")
async def events():
    q = queue.Queue(maxsize=500)
    _queues.append(q)

    def gen():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    ev = q.get(timeout=15)
                    yield "data: " + json.dumps(ev, ensure_ascii=False) + "\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            if q in _queues:
                _queues.remove(q)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/status")
async def status():
    with _state["lock"]:
        return {"room": _state["room"], "status": _state["status"], "recorded": _recorder.count}


@app.get("/api/categories")
async def categories():
    return {"categories": [{"key": k, "label": lab, "color": col} for k, lab, col in CATEGORIES]}


@app.post("/api/export")
async def export():
    path = _recorder.save()
    if not path:
        return {"ok": False, "error": "当前会话尚无消息可导出"}
    return {"ok": True, "name": path.name, "count": _recorder.count}


@app.get("/api/history")
async def history():
    return {"files": SessionRecorder.list_files()}


@app.get("/api/download/{name}")
async def download(name: str):
    path = SessionRecorder.path_for(name)
    if not path:
        return {"ok": False, "error": "文件不存在"}
    return FileResponse(str(path), filename=name, media_type="text/csv")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
