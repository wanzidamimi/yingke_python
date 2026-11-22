# -*- coding: utf-8 -*-
"""映客 TCP 1300 弹幕采集器。

链路：
  自主 RSA 握手 -> 解密握手响应 -> 动态认证包 -> 动态进房/订阅
  -> 接收 0xb001 / 0xb002 -> gzip 或 RC4+gzip 解压
  -> 解析 tp=pub / tp=pp 弹幕并回调 on_message()
"""
import base64
import gzip
import json
import random
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent
REFS = ROOT / "reverse" / "references"
if str(REFS) not in sys.path:
    sys.path.insert(0, str(REFS))

from app_tcp_client import (  # noqa: E402
    GATEWAYS,
    build_handshake_wrapped,
    build_packet,
    build_subscribe_body,
    find_packet,
    make_nonce,
    parse_packet,
    rc4,
)
from parse_pktmon_pcap import payloads  # noqa: E402

DEFAULT_CONFIG = REFS / "inke_runtime_config.json"
MITM_FLOWS = REFS.parent / "logs" / "mitm_auth_flows.jsonl"
LONG_UID = 779252212
ADB_SERIAL = "emulator-5554"
GID_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/Connection_Gid_Store.xml"
DEVICE_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/duomi_share_preference.xml"
ATOM_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/atom_sp.xml"
UNIQUE_ID_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/sp_name_app_unique_id.xml"


def load_runtime_config(path=DEFAULT_CONFIG):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def refresh_gid_from_adb(config, serial=ADB_SERIAL):
    """如果模拟器在线，从 Connection_Gid_Store 动态刷新 gid。

    失败时静默保留 config 里的值，保证纯 Python 链路也能运行。
    """
    adb = shutil.which("adb")
    if not adb:
        return config
    try:
        proc = subprocess.run(
            [adb, "-s", serial, "shell", "cat", GID_PREFS],
            capture_output=True, timeout=6,
        )
        if proc.returncode != 0 or not proc.stdout:
            return config
        root = ET.fromstring(proc.stdout.decode("utf-8", "replace"))
        key = "conn_gid-tcp-%s" % config.get("uid")
        gid = None
        for node in root.findall("string"):
            if node.attrib.get("name") == key and node.text:
                gid = node.text.strip()
                break
        if not gid:
            return config
        config["gid"] = gid
        auth = config.setdefault("auth", {})
        auth["gid"] = gid
        if isinstance(auth.get("bus_buf"), dict):
            auth["bus_buf"]["gid"] = gid
        enter = config.setdefault("enter_room", {})
        enter["gid"] = gid
        if isinstance(enter.get("bus_buf"), dict):
            enter["bus_buf"]["gid"] = gid
    except Exception:
        pass
    return config


def _adb_prefs(serial, path):
    adb = shutil.which("adb")
    if not adb:
        return {}
    try:
        proc = subprocess.run(
            [adb, "-s", serial, "shell", "cat", path],
            capture_output=True, timeout=6,
        )
        if proc.returncode != 0 or not proc.stdout:
            return {}
        root = ET.fromstring(proc.stdout.decode("utf-8", "replace"))
        out = {}
        for node in list(root):
            name = node.attrib.get("name")
            if name and node.text:
                out[name] = node.text.strip()
        return out
    except Exception:
        return {}


def refresh_device_fields_from_adb(config, serial=ADB_SERIAL):
    """从 App 本地缓存刷新设备字段；失败时保留原配置。"""
    device = _adb_prefs(serial, DEVICE_PREFS)
    atom = _adb_prefs(serial, ATOM_PREFS)
    unique = _adb_prefs(serial, UNIQUE_ID_PREFS)

    auth = config.setdefault("auth", {})
    bus = auth.setdefault("bus_buf", {})
    uid = str(config.get("uid") or bus.get("uid") or LONG_UID)

    smid = device.get("PHONE_SMID") or atom.get("smid")
    devi = device.get("PHONE_DEVI")
    cv = device.get("app_client_version")
    aid = unique.get("app_unique_id")

    if smid:
        bus["smid"] = smid
    if devi:
        bus["devi"] = devi
    if cv:
        bus["cv"] = cv
    if aid:
        bus["aid"] = aid

    bus["uid"] = uid
    auth["uid"] = int(uid) if uid.isdigit() else uid
    enter = config.setdefault("enter_room", {})
    enter["uid"] = auth["uid"]
    if isinstance(enter.get("bus_buf"), dict):
        enter["bus_buf"]["uid"] = auth["uid"]

    source = {
        "appid": "10000",
        "uid": uid,
        "page": "unknown",
        "time": "0",
    }
    bus["source_info"] = base64.b64encode(
        json.dumps(source, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")

    elapsed_ms = int(time.monotonic() * 1000)
    client_id = "%d#%d@%s$%d" % (
        int(time.time() * 1000),
        elapsed_ms,
        uid,
        random.randint(-2147483648, 2147483647),
    )
    bus["clientId"] = client_id
    return config


def refresh_env_from_mitm_log(config, path=MITM_FLOWS):
    """从最近一次 MITM 日志里刷新 sid/cc/lc/mtid/mtxid 等会话环境字段。"""
    if not Path(path).exists():
        return config
    keys = ("sid", "cc", "lc", "mtid", "mtxid", "ua", "osversion")
    best = None
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if "/serviceinfo/info" not in str(row.get("path", "")):
                    continue
                q = parse_qs(str(row.get("query", "")))
                if all(k in q and q[k] for k in keys):
                    best = {k: q[k][0] for k in keys}
    except Exception:
        return config

    if not best:
        return config

    bus = config.setdefault("auth", {}).setdefault("bus_buf", {})
    mapping = {
        "sid": "sid", "cc": "cc", "lc": "lc", "mtid": "mtid",
        "mtxid": "mtxid", "ua": "ua", "osversion": "osversion",
    }
    for src, dst in mapping.items():
        bus[dst] = best[src]
    return config


TP_MAP = {
    "pub": ("chat", "弹幕"),
    "pp": ("chat", "弹幕"),
    "chat": ("chat", "弹幕"),
    "user_join_tip": ("member", "进场"),
    "color": ("member", "进场"),
    "usernu": ("stats", "在线人数"),
    "gift_refine_sync_state": ("gift", "礼物"),
    "doubleclickcount": ("like", "点赞"),
    "guard_seat_info_update": ("guard", "守护"),
    "c_room_hour_time_ranking": ("rank", "排行"),
    "barrage_conf": ("system", "弹幕配置"),
    "cfg": ("system", "配置"),
    "sys": ("system", "系统"),
    "ff": ("system", "系统"),
    "ann": ("system", "公告"),
    "live_red_dot": ("system", "提示"),
    "activitys_refresh": ("system", "活动"),
}

HOT_ROOMS_URL = "https://webapi.busi.inke.cn/web/Live_top_pc"
SHARE_URL = "https://webapi.busi.inke.cn/web/live_share_pc"
_hot_cache = {"ts": 0, "rooms": []}


def resolve_room(raw, uid=None, liveid=None):
    """把页面输入/房间卡片参数统一解析为 (uid, liveid)。"""
    uid = str(uid or "").strip() or None
    liveid = str(liveid or "").strip() or None
    raw = str(raw or "").strip()

    if "?" in raw or "://" in raw:
        try:
            q = parse_qs(urlparse(raw).query)
            uid = uid or (q.get("uid") or [None])[0]
            liveid = liveid or (
                q.get("liveid") or q.get("live_id") or q.get("id") or [None]
            )[0]
        except Exception:
            pass

    if not liveid and raw.isdigit():
        if len(raw) >= 15:
            liveid = raw
        else:
            uid = uid or raw

    if not liveid and uid:
        liveid = lookup_liveid(uid)
    return uid, liveid


def lookup_liveid(uid):
    try:
        from curl_cffi import requests as creq

        d = creq.get(SHARE_URL, params={"uid": uid}, impersonate="chrome", timeout=10).json()
        data = d.get("data") or {}
        if str(data.get("status")) == "1" and data.get("liveid"):
            return str(data["liveid"])
    except Exception:
        pass
    return None


def fetch_hot_rooms(ttl=60):
    """获取热门直播列表，供页面选择直播间。"""
    now = time.time()
    if _hot_cache["rooms"] and now - _hot_cache["ts"] < ttl:
        return list(_hot_cache["rooms"])
    try:
        from curl_cffi import requests as creq

        data = creq.get(HOT_ROOMS_URL, impersonate="chrome", timeout=10).json()
        rows = ((data.get("data") or {}).get("list") or [])
    except Exception:
        rows = []
    rooms = []
    for row in rows:
        liveid = str(row.get("live_id") or "").strip()
        uid = str(row.get("uid") or "").strip()
        if not liveid:
            continue
        rooms.append({
            "uid": uid,
            "liveid": liveid,
            "nick": row.get("nick") or "",
            "portrait": row.get("portrait") or "",
        })
    _hot_cache["ts"] = now
    _hot_cache["rooms"] = rooms
    return list(rooms)


def _find_packet(path, predicate):
    try:
        pl = payloads(path)
    except Exception:
        return None
    return next((p for s, d, p in pl if predicate(s, d, p)), None)


def find_handshake(path):
    return _find_packet(
        path,
        lambda s, d, p: s != 1300 and len(p) == 203 and p[:1] == b"\x89",
    )


def find_auth(path):
    return _find_packet(
        path,
        lambda s, d, p: s != 1300 and len(p) > 20 and p[4:6] == b"\x40\x04",
    )


def find_client_frame(path, cmd):
    """从样本里取一条完整客户端帧（按单包即可，0002/4c04/4020 都不跨包）。"""
    return _find_packet(
        path,
        lambda s, d, p: s != 1300 and len(p) > 22 and p[4:6] == cmd,
    )


def build_auth_packet(key, config=None, long_uid=LONG_UID):
    """按运行时配置动态构造 0x4004 认证包。"""
    config = config or load_runtime_config()
    body = json.dumps(
        config["auth"], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    ext = json.dumps(
        {"proto-type": "tcp", "xid": 2, "long-uid": long_uid},
        separators=(",", ":"),
    ).encode("utf-8")
    return build_packet(
        0x4004, rc4(body, key), 0x0002, 0, 10000,
        msg_id=5, mark=0x89, ext=ext,
    )


def build_room_packets(liveid, key, config=None, long_uid=LONG_UID):
    """按真实 App 序列构造 0002 / 4c04 / 4020 三个进房包。

    真实序列：
      0002 = c.jr 进房请求，body = RC4(JSON)
      4c04 = 房间订阅，body 明文，ext={"long-uid":..., "xid":13}
      4020 = 历史消息同步，body 空，ext={"liveid":..., "max-id":..., ...}
    """
    liveid = str(liveid)
    out = []

    # 0002：用运行时 JSON 模板改 rid/liveid，再按握手 key 重新 RC4
    config = config or load_runtime_config()
    obj = json.loads(json.dumps(config["enter_room"]))
    bus = obj.get("bus_buf") if isinstance(obj.get("bus_buf"), dict) else {}
    bus["rid"] = liveid
    bus["liveid"] = liveid
    obj["bus_buf"] = bus
    new_body = rc4(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        key,
    )
    ext = json.dumps({"xid": 12, "long-uid": long_uid}, separators=(",", ":")).encode()
    out.append(build_packet(
        0x0002, new_body, 0x000C, 0, 10000,
        msg_id=5, mark=0x89, ext=ext,
    ))

    # 4c04：房间订阅
    sub_body = build_subscribe_body(liveid, cmd=0x0100)
    ext = json.dumps({"long-uid": long_uid, "xid": 13}, separators=(",", ":")).encode()
    out.append(build_packet(
        0x4C04, sub_body, 0x000D, 0, 10000,
        msg_id=5, mark=0x89, ext=ext,
    ))

    # 4020：历史/消息同步
    ext = json.dumps({
        "liveid": liveid,
        "max-id": int(time.time() * 1000) * 1000,
        "xid": 14,
        "long-uid": long_uid,
    }, separators=(",", ":")).encode()
    out.append(build_packet(
        0x4020, b"", 0x000E, 0, 10000,
        msg_id=5, mark=0x89, ext=ext,
    ))
    return out


def read_packet(sock, buf, timeout=1.0):
    sock.settimeout(timeout)
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = find_packet(buf)
        if found:
            start, packet = found
            del buf[:start + len(packet)]
            return parse_packet(packet)
        try:
            chunk = sock.recv(65536)
        except socket.timeout:
            break
        except OSError:
            return None
        if not chunk:
            return None
        buf.extend(chunk)
    return None


def decode_body(cmd, body, key):
    if cmd == 0xB002:
        try:
            return gzip.decompress(body)
        except Exception:
            return None
    if cmd in (0xB001, 0x0002, 0x0015):
        try:
            return gzip.decompress(rc4(body, key))
        except Exception:
            return None
    try:
        return gzip.decompress(body)
    except Exception:
        return None


def _items(obj):
    if not isinstance(obj, dict):
        return []
    bus = obj.get("bus_buf")
    if isinstance(bus, list):
        return bus
    if isinstance(bus, dict):
        return [bus]
    if "ms" in obj:
        return [obj]
    return []


def normalize(obj, liveid, seq=None):
    out = []
    obj_liveid = str(obj.get("liveid") or liveid or "")
    for item in _items(obj):
        ms = item.get("ms", []) if isinstance(item, dict) else []
        if isinstance(ms, dict):
            ms = [ms]
        for m in ms:
            if not isinstance(m, dict):
                continue
            tp = str(m.get("tp") or "")
            cat, label = TP_MAP.get(tp, ("other", "其他"))
            frm = m.get("from") if isinstance(m.get("from"), dict) else {}
            user = m.get("user") if isinstance(m.get("user"), dict) else {}
            nick = frm.get("nic") or user.get("nick") or ""
            text = m.get("c") or m.get("ct") or ""
            if not text and isinstance(m.get("content"), list):
                text = "".join(
                    seg.get("text", "") for seg in m["content"]
                    if isinstance(seg, dict)
                )
            if tp == "usernu":
                text = "在线 %s 人" % m.get("n", "?")
            if not text and not nick:
                continue
            out.append({
                "kind": "danmu",
                "category": cat,
                "category_label": label,
                "message_type": tp,
                "user": nick,
                "content": text,
                "text": ("%s: %s" % (nick, text)) if nick and text else (text or nick),
                "liveid": obj_liveid,
                "seq": seq,
                "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
    return out


class InkeTcpCollector:
    def __init__(self, on_message=None, liveid=None, config_path=None):
        self.on_message = on_message
        self.liveid = str(liveid or "").strip()
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG
        self.running = False
        self.alive = False
        self._thread = None
        self._sock = None
        self._seq = 0
        self.state = "idle"

    def _emit(self, text, kind="system"):
        if self.on_message:
            self.on_message({"kind": kind, "text": text})

    def start(self):
        if not self.liveid:
            raise RuntimeError("缺少 liveid")
        config = load_runtime_config(self.config_path)
        config = refresh_gid_from_adb(config)
        config = refresh_device_fields_from_adb(config)
        config = refresh_env_from_mitm_log(config)
        nonce = make_nonce()
        handshake, meta = build_handshake_wrapped(int(config["uid"]), nonce=nonce)
        self._runtime_config = config
        self._handshake = handshake
        self._nonce = nonce
        self._handshake_meta = meta
        self.running = True
        self.alive = True
        self.state = "connecting"
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def _run(self):
        last_error = ""
        while self.running:
            try:
                self._connect_once()
                last_error = ""
            except Exception as exc:
                last_error = str(exc)
                self._emit("连接异常: %s，3 秒后重连" % last_error, "error")
            if not self.running:
                break
            time.sleep(3)
        self.alive = False
        self.state = "idle"
        if last_error:
            self._emit("采集线程结束: %s" % last_error, "error")

    def _connect_once(self):
        errors = []
        for target in GATEWAYS:
            if not self.running:
                return
            sock = None
            try:
                sock = socket.create_connection(target, timeout=5)
                self._sock = sock
                sock.sendall(self._handshake)
                buf = bytearray()
                packet = read_packet(sock, buf, timeout=8)
                if not packet:
                    raise RuntimeError("握手无响应")
                info = json.loads(rc4(packet["body"], self._nonce).decode("utf-8"))
                key = info["key"]
                sock.sendall(build_auth_packet(key, self._runtime_config))
                for packet in build_room_packets(self.liveid, key, self._runtime_config):
                    sock.sendall(packet)
                self.state = "live"
                self._emit("已连接 %s:%d，订阅 liveid=%s" % (target[0], target[1], self.liveid))
                self._recv_loop(sock, buf, key)
                return
            except Exception as exc:
                errors.append("%s:%s %s" % (target[0], target[1], exc))
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except Exception:
                        pass
                if self._sock is sock:
                    self._sock = None
        raise RuntimeError("所有网关失败: %s" % "; ".join(errors))

    def _recv_loop(self, sock, buf, key):
        while self.running:
            packet = read_packet(sock, buf, timeout=1.0)
            if packet is None:
                continue
            plain = decode_body(packet["cmd"], packet["body"], key)
            if not plain:
                continue
            try:
                obj = json.loads(plain.decode("utf-8"))
            except Exception:
                continue
            self._seq += 1
            for msg in normalize(obj, self.liveid, self._seq):
                if self.on_message:
                    self.on_message(msg)

    def stop(self):
        self.running = False
        self.alive = False
        self.state = "idle"
        sock = self._sock
        self._sock = None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                sock.close()
            except Exception:
                pass
