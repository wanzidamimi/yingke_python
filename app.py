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
from emulator_control import SHOT as EMULATOR_SHOT, wake_and_launch
from http_login_web import complete_login, start_sms
from inke_tcp_collector import InkeTcpCollector, fetch_hot_rooms, resolve_room
from login_session import current_session, logout, mark_logged_in
from login_state import check_environment, read_login_state, save_login_state
from recorder import SessionRecorder
from video_stream import is_allowed_stream_host, iter_upstream_stream, resolve_stream_addr

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


@app.get("/api/session/current")
async def session_current():
    return current_session()


@app.post("/api/session/logout")
async def session_logout():
    result = logout()
    with _state["lock"]:
        client = _state["client"]
    if client:
        try:
            client.stop()
        except Exception:
            pass
    return result


@app.post("/api/emulator/wake")
async def emulator_wake(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    pin = (data.get("pin") or "").strip() or None
    try:
        return wake_and_launch(pin=pin)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/emulator/screenshot")
async def emulator_screenshot():
    if not EMULATOR_SHOT.exists():
        return {"ok": False, "error": "暂无截图"}
    return FileResponse(str(EMULATOR_SHOT), media_type="image/png")


@app.post("/api/login/http/sms")
async def login_http_sms(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    return start_sms(
        data.get("phone") or "",
        area_code=data.get("area_code") or "86",
        region=data.get("region") or "cn",
    )


@app.post("/api/login/http/verify")
async def login_http_verify(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    result = complete_login(
        data.get("token") or "",
        data.get("phone") or "",
        data.get("code") or "",
    )
    if result.get("ok"):
        uid = (result.get("masked") or {}).get("uid")
        masked_phone = (result.get("masked") or {}).get("phone_masked") or ""
        if uid:
            mark_logged_in("http_sms", uid, masked_phone=masked_phone)
    return result


@app.get("/api/login/status")
async def login_status():
    env = check_environment()
    return {"ok": env["ok"], "environment": env}


@app.post("/api/login/open")
async def login_open(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    pin = (data.get("pin") or "").strip() or None
    try:
        return wake_and_launch(pin=pin)
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/login/sync")
async def login_sync(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    sid = (data.get("sid") or "").strip() or None
    try:
        result = read_login_state(preferred_sid=sid)
        if not result.get("ok"):
            return result
        path = save_login_state(result)
        uid = (result.get("masked") or {}).get("uid")
        if uid:
            mark_logged_in("adb_root", uid)
        return {
            "ok": True,
            "message": "登录态已保存到本地配置",
            "saved_to": path,
            "masked": result.get("masked"),
            "sid_candidate_count": result.get("sid_candidate_count", 0),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
    session = current_session()
    if not session.get("logged_in"):
        return {
            "ok": False,
            "reason": "not_logged_in",
            "error": "请先登录映客账号",
        }
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


@app.get("/api/video/check")
async def video_check(liveid: str = "", refresh: int = 0):
    liveid = str(liveid or "").strip()
    if not liveid:
        return {"ok": False, "error": "缺少 liveid"}
    url = resolve_stream_addr(liveid, force=bool(refresh))
    if not url:
        return {"ok": False, "error": "该直播间暂无可播放画面"}
    if not is_allowed_stream_host(url):
        return {"ok": False, "reason": "disallowed_stream_host", "error": "流地址不在白名单内"}
    return {"ok": True, "content_type": "video/x-flv"}


@app.get("/api/video/stream")
async def video_stream_proxy(liveid: str = "", refresh: int = 0):
    liveid = str(liveid or "").strip()
    if not liveid:
        return {"ok": False, "error": "缺少 liveid"}
    url = resolve_stream_addr(liveid, force=bool(refresh))
    if not url:
        return {"ok": False, "error": "该直播间暂无可播放画面"}
    if not is_allowed_stream_host(url):
        return {"ok": False, "reason": "disallowed_stream_host", "error": "流地址不在白名单内"}
    return StreamingResponse(
        iter_upstream_stream(url),
        media_type="video/x-flv",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Accel-Buffering": "no",
        },
    )


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
