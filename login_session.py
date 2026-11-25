# -*- coding: utf-8 -*-
"""Web 登录会话状态。

只有 `inke_runtime_config.local.json` 是用户凭证。
`inke_runtime_config.json` 是协议模板，不作为登录凭证回退。
"""
import json
import time
from pathlib import Path

import login_state

ROOT = Path(__file__).parent
META = ROOT / "reverse" / "references" / "login_session.json"


def _read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def credential_valid(config):
    """判断本地配置是否含有最关键的登录凭证。"""
    if not isinstance(config, dict):
        return False
    try:
        uid = int(config.get("uid") or 0)
    except Exception:
        return False
    bus = config.get("auth", {}).get("bus_buf", {})
    sid = str(bus.get("sid") or "").strip()
    return uid > 0 and bool(sid)


def current_session(config_path=None, meta_path=None):
    config_path = Path(config_path) if config_path else login_state.LOCAL_CONFIG
    meta_path = Path(meta_path) if meta_path else META

    if not config_path.exists():
        return {
            "ok": True,
            "logged_in": False,
            "reason": "missing_local_config",
            "user": None,
        }

    config = _read_json(config_path)
    if not credential_valid(config):
        return {
            "ok": True,
            "logged_in": False,
            "reason": "incomplete_credentials",
            "user": None,
        }

    meta = _read_json(meta_path, {})
    uid = int(config["uid"])
    gid = str(config.get("gid") or "").strip()
    user = {
        "uid": uid,
        "login_method": meta.get("login_method") or "local_config",
        "phone_masked": meta.get("phone_masked") or "",
        "gid_status": "ready" if gid else "pending",
        "logged_at": meta.get("logged_at") or "",
    }
    return {"ok": True, "logged_in": True, "reason": "", "user": user}


def mark_logged_in(login_method, uid, masked_phone="", gid_status="pending", meta_path=None):
    meta_path = Path(meta_path) if meta_path else META
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "login_method": login_method,
        "uid": uid,
        "phone_masked": masked_phone,
        "gid_status": gid_status,
        "logged_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def logout(config_path=None, meta_path=None):
    config_path = Path(config_path) if config_path else login_state.LOCAL_CONFIG
    meta_path = Path(meta_path) if meta_path else META
    removed = []
    for path in (config_path, meta_path):
        try:
            if path.exists():
                path.unlink()
                removed.append(str(path))
        except Exception:
            pass
    return {"ok": True, "message": "已退出登录", "removed": removed}
