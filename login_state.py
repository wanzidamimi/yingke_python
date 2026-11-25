# -*- coding: utf-8 -*-
"""从 root Android 设备读取映客登录态，生成 TCP 采集器本地配置。

不接收、不保存手机号、密码、短信验证码或第三方登录 token。
"""
import base64
import json
import random
import re
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent
REFS = ROOT / "reverse" / "references"
BASE_CONFIG = REFS / "inke_runtime_config.json"
LOCAL_CONFIG = REFS / "inke_runtime_config.local.json"
EXAMPLE_CONFIG = REFS / "inke_runtime_config.example.json"
PKG = "com.meelive.ingkee"
ADB_SERIAL = "emulator-5554"

DEVICE_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/duomi_share_preference.xml"
GID_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/Connection_Gid_Store.xml"
SESSION_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/Connection_Session.xml"
ATOM_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/atom_sp.xml"
UNIQUE_ID_PREFS = "/data/data/com.meelive.ingkee/shared_prefs/sp_name_app_unique_id.xml"
WEBVIEW_CACHE = "/data/data/com.meelive.ingkee/cache/WebView/Default/HTTP Cache"

SID_RE = re.compile(r"sid=([A-Za-z0-9_-]{16,})")


def _adb_path():
    return shutil.which("adb") or r"C:\Users\Administrator\AppData\Local\Android\Sdk\platform-tools\adb.exe"


def _run_adb(serial, args, timeout=10):
    return subprocess.run(
        [_adb_path(), "-s", serial] + list(args),
        capture_output=True, timeout=timeout,
    )


def _text(proc):
    if proc is None:
        return ""
    return (proc.stdout or b"").decode("utf-8", "replace")


def _device_shell(serial, command, timeout=10, require_root=False):
    """执行设备 shell；root 不可用时尝试 su。"""
    direct = _run_adb(serial, ["shell", command], timeout=timeout)
    if direct.returncode == 0 and "Permission denied" not in _text(direct):
        return direct
    if require_root:
        return _run_adb(serial, ["shell", "su", "-c", command], timeout=timeout)
    return direct


def _read_device_file(serial, path, require_root=True):
    proc = _device_shell(serial, "cat '%s'" % path, require_root=require_root)
    if proc.returncode != 0:
        return ""
    return _text(proc)


def parse_prefs_xml(text):
    """解析 Android SharedPreferences XML，返回 name -> value。"""
    out = {}
    if not text:
        return out
    try:
        root = ET.fromstring(text)
    except Exception:
        return out
    for node in list(root):
        name = node.attrib.get("name")
        if not name:
            continue
        value = node.attrib.get("value")
        if value is None and node.text:
            value = node.text.strip()
        out[name] = value
    return out


def read_device_prefs(serial, path):
    return parse_prefs_xml(_read_device_file(serial, path))


def is_root(serial=ADB_SERIAL):
    proc = _device_shell(serial, "id", timeout=6)
    text = _text(proc)
    if "uid=0" in text:
        return True
    proc = _device_shell(serial, "id", timeout=6, require_root=True)
    return "uid=0" in _text(proc)


def check_environment(serial=ADB_SERIAL):
    """返回 ADB/root/设备/App/本地配置状态。"""
    result = {
        "ok": False,
        "adb": Path(_adb_path()).exists(),
        "device": False,
        "root": False,
        "app_installed": False,
        "local_config": LOCAL_CONFIG.exists(),
        "error": "",
    }
    if not result["adb"]:
        result["error"] = "未找到 adb"
        return result

    devices = _text(_run_adb(serial, ["devices"], timeout=6))
    result["device"] = serial in devices
    if not result["device"]:
        result["error"] = "设备未在线，请检查 USB 调试或 adb connect"
        return result

    result["root"] = is_root(serial)
    if not result["root"]:
        result["error"] = "设备没有 root，无法读取 App 私有登录态"
        return result

    installed = _text(_device_shell(serial, "pm path %s" % PKG, timeout=8))
    result["app_installed"] = bool(installed.strip())
    if not result["app_installed"]:
        result["error"] = "设备未安装映客 App"
        return result

    result["ok"] = True
    return result


def pick_sid(candidates, preferred=None):
    """从 WebView 缓存候选里选出现次数最多的 sid。"""
    values = [x for x in (candidates or []) if x]
    if preferred and preferred in values:
        return preferred
    if not values:
        return ""
    return Counter(values).most_common(1)[0][0]


def mask_value(value):
    if value is None:
        return ""
    s = str(value)
    if len(s) <= 10:
        return s[:2] + "***"
    return s[:6] + "***" + s[-4:]


def load_base_config(path=None):
    p = Path(path) if path else BASE_CONFIG
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _sid_candidates(serial):
    command = (
        "grep -R -a -o 'sid=[A-Za-z0-9_-]\\{16,\\}' '%s' 2>/dev/null" % WEBVIEW_CACHE
    )
    text = _text(_device_shell(serial, command, timeout=15, require_root=True))
    values = []
    for line in text.splitlines():
        values.extend(SID_RE.findall(line))
    return values


def build_config(uid, gid, session, sid, smid, devi, cv, aid, base=None):
    """把读取到的字段合并成采集器配置。"""
    cfg = json.loads(json.dumps(base or load_base_config()))
    uid = int(uid) if str(uid).isdigit() else uid
    uid_s = str(uid)

    cfg["uid"] = uid
    cfg["gid"] = gid
    cfg["session"] = session

    auth = cfg.setdefault("auth", {})
    auth["uid"] = uid
    auth["gid"] = gid
    bus = auth.setdefault("bus_buf", {})
    bus["uid"] = uid_s
    bus["gid"] = gid
    bus["sid"] = sid
    if smid:
        bus["smid"] = smid
    if devi:
        bus["devi"] = devi
    if cv:
        bus["cv"] = cv
    if aid:
        bus["aid"] = aid

    source = {"appid": "10000", "uid": uid_s, "page": "unknown", "time": "0"}
    bus["source_info"] = base64.b64encode(
        json.dumps(source, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    bus["clientId"] = "%d#%d@%s$%d" % (
        int(time.time() * 1000),
        int(time.monotonic() * 1000),
        uid_s,
        random.randint(-2147483648, 2147483647),
    )

    enter = cfg.setdefault("enter_room", {})
    enter["uid"] = uid
    enter["gid"] = gid
    enter_bus = enter.setdefault("bus_buf", {})
    enter_bus["uid"] = uid
    enter_bus["gid"] = gid
    return cfg


def read_login_state(serial=ADB_SERIAL, config_path=None, preferred_sid=None):
    """读取 root 设备登录态，返回完整结果。"""
    env = check_environment(serial)
    if not env["ok"]:
        return {
            "ok": False,
            "error": env["error"],
            "environment": env,
        }

    base = load_base_config(config_path)
    device_prefs = read_device_prefs(serial, DEVICE_PREFS)
    gid_prefs = read_device_prefs(serial, GID_PREFS)
    session_prefs = read_device_prefs(serial, SESSION_PREFS)
    atom_prefs = read_device_prefs(serial, ATOM_PREFS)
    unique_prefs = read_device_prefs(serial, UNIQUE_ID_PREFS)

    uid = device_prefs.get("pre_loginuid_for_hotfix") or base.get("uid")
    gid = ""
    if uid:
        gid = gid_prefs.get("conn_gid-tcp-%s" % uid, "")
    if not gid:
        for key, value in gid_prefs.items():
            if key.startswith("conn_gid-tcp-") and value:
                uid = uid or key.rsplit("-", 1)[-1]
                gid = value
                break

    session = session_prefs.get("session") or base.get("session") or 10000
    smid = device_prefs.get("PHONE_SMID") or atom_prefs.get("smid") or base["auth"]["bus_buf"].get("smid")
    devi = device_prefs.get("PHONE_DEVI") or base["auth"]["bus_buf"].get("devi")
    cv = device_prefs.get("app_client_version") or base["auth"]["bus_buf"].get("cv")
    aid = unique_prefs.get("app_unique_id") or base["auth"]["bus_buf"].get("aid")

    candidates = _sid_candidates(serial)
    old_sid = base.get("auth", {}).get("bus_buf", {}).get("sid") or ""
    sid = pick_sid(candidates, preferred=preferred_sid or old_sid)
    if not sid:
        sid = old_sid

    missing = []
    for name, value in [
        ("uid", uid), ("gid", gid), ("sid", sid), ("smid", smid), ("devi", devi)
    ]:
        if not value:
            missing.append(name)

    cfg = build_config(
        uid=uid, gid=gid, session=session, sid=sid,
        smid=smid, devi=devi, cv=cv, aid=aid, base=base,
    )
    masked = mask_login_state({"config": cfg, "sid_candidates": candidates})
    return {
        "ok": not missing,
        "error": "缺少字段: %s" % ", ".join(missing) if missing else "",
        "environment": env,
        "fields": {
            "uid": uid,
            "gid": bool(gid),
            "session": session,
            "sid": bool(sid),
            "smid": bool(smid),
            "devi": bool(devi),
            "cv": bool(cv),
            "aid": bool(aid),
        },
        "sid_candidate_count": len(candidates),
        "sid_candidates": candidates,
        "missing": missing,
        "config": cfg,
        "masked": masked,
    }


def save_login_state(result, output_path=None):
    if not result.get("config"):
        raise ValueError("登录态结果里没有 config")
    path = Path(output_path) if output_path else LOCAL_CONFIG
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result["config"], f, ensure_ascii=False, indent=2)
    return str(path)


def mask_login_state(result):
    cfg = result.get("config") or {}
    bus = cfg.get("auth", {}).get("bus_buf", {})
    return {
        "uid": cfg.get("uid"),
        "gid": mask_value(cfg.get("gid")),
        "session": cfg.get("session"),
        "sid": mask_value(bus.get("sid")),
        "smid": mask_value(bus.get("smid")),
        "devi": mask_value(bus.get("devi")),
        "cv": bus.get("cv"),
        "aid": mask_value(bus.get("aid")),
        "clientId": mask_value(bus.get("clientId")),
    }
