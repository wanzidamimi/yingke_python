# -*- coding: utf-8 -*-
"""Web 端手机号验证码登录服务层。

手机号和验证码只存在于单次 HTTP 请求内存中：
- 短信阶段只把 request_id 放入短期 pending 表
- 验证码阶段立即消费 pending
- 不写日志、不写文件、不返回手机号/验证码
"""
import base64
import json
import random
import re
import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
REFS = ROOT / "reverse" / "references"
if str(REFS) not in sys.path:
    sys.path.insert(0, str(REFS))

import http_login_probe as probe  # noqa: E402
import inke_tcp_collector  # noqa: E402
import login_state  # noqa: E402

PENDING_TTL = 300
_pending = {}

PHONE_RE = re.compile(r"^\d{6,15}$")
CODE_RE = re.compile(r"^\d{4,8}$")


def _cleanup():
    now = time.time()
    for key in list(_pending):
        if now - _pending[key]["ts"] > PENDING_TTL:
            _pending.pop(key, None)


def _parse_body(text):
    if isinstance(text, dict):
        return text
    try:
        return json.loads(text)
    except Exception:
        return {}


def start_sms(phone, area_code="86", region="cn"):
    """发送短信验证码，返回一次性 token；不返回手机号和 request_id。"""
    _cleanup()
    phone = str(phone or "").strip().replace(" ", "")
    area_code = str(area_code or "86").strip()
    region = str(region or "cn").strip()
    if not PHONE_RE.match(phone):
        return {"ok": False, "error": "手机号格式不正确"}
    if not area_code.isdigit():
        return {"ok": False, "error": "区号格式不正确"}

    try:
        raw = probe.send_sms_code(phone, area_code=area_code, region=region)
    except Exception as e:
        return {"ok": False, "error": "短信请求失败: %s" % e}

    data = _parse_body(raw.get("body"))
    if data.get("dm_error") != 0:
        return {"ok": False, "error": data.get("error_msg") or "短信发送失败"}

    request_id = data.get("request_id")
    if not request_id:
        return {"ok": False, "error": "服务端未返回 request_id"}

    token = secrets.token_urlsafe(18)
    _pending[token] = {
        "request_id": request_id,
        "area_code": area_code,
        "region": region,
        "ts": time.time(),
    }
    return {
        "ok": True,
        "token": token,
        "message": "验证码已发送，请在 5 分钟内完成登录",
        "masked_phone": phone[:3] + "****" + phone[-4:],
    }


def _build_runtime_config(login_data, area_code, base=None):
    uid = int(login_data["uid"])
    session = str(login_data["session"])
    cfg = json.loads(json.dumps(base or login_state.load_base_config()))

    cfg["uid"] = uid
    cfg["session"] = 10000
    # HTTP 首次登录没有本地 gid；留空后由服务端在 0x4004 响应里分配。
    cfg["gid"] = ""

    auth = cfg.setdefault("auth", {})
    auth["uid"] = uid
    auth["gid"] = ""
    bus = auth.setdefault("bus_buf", {})
    bus["uid"] = str(uid)
    bus["sid"] = session
    bus["gid"] = ""
    bus["area_code"] = area_code

    source = {"appid": "10000", "uid": str(uid), "page": "unknown", "time": "0"}
    bus["source_info"] = base64.b64encode(
        json.dumps(source, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    bus["clientId"] = "%d#%d@%s$%d" % (
        int(time.time() * 1000),
        int(time.monotonic() * 1000),
        uid,
        random.randint(-2147483648, 2147483647),
    )

    enter = cfg.setdefault("enter_room", {})
    enter["uid"] = uid
    enter["gid"] = ""
    enter_bus = enter.setdefault("bus_buf", {})
    enter_bus["uid"] = uid
    enter_bus["gid"] = ""
    return cfg


def complete_login(token, phone, code):
    """用验证码完成登录并保存本地配置；pending 一次性消费。"""
    _cleanup()
    pending = _pending.pop(str(token or ""), None)
    if not pending:
        return {"ok": False, "error": "验证码会话不存在或已过期，请重新发送验证码"}

    phone = str(phone or "").strip().replace(" ", "")
    code = str(code or "").strip()
    if not PHONE_RE.match(phone):
        return {"ok": False, "error": "手机号格式不正确"}
    if not CODE_RE.match(code):
        return {"ok": False, "error": "验证码格式不正确"}

    try:
        raw = probe.login_with_code(
            phone,
            code,
            pending["request_id"],
            area_code=pending["area_code"],
            region=pending["region"],
        )
    except Exception as e:
        return {"ok": False, "error": "登录请求失败: %s" % e}

    data = _parse_body(raw.get("body"))
    if data.get("dm_error") != 0:
        return {"ok": False, "error": data.get("error_msg") or "登录失败"}

    if not probe.validate_login_result(data):
        return {"ok": False, "error": "登录响应校验失败"}

    cfg = _build_runtime_config(data, pending["area_code"])
    old_gid = cfg.get("gid")
    cfg = inke_tcp_collector.refresh_gid_from_adb(cfg)
    gid_refreshed = cfg.get("gid") != old_gid
    path = login_state.save_login_state({"config": cfg})
    masked = login_state.mask_login_state({"config": cfg})
    masked["uid"] = data.get("uid")
    masked["gid"] = "***" + str(cfg.get("gid") or "")[-4:]
    return {
        "ok": True,
        "message": "登录成功，本地配置已保存",
        "saved_to": path,
        "masked": masked,
        "gid_refreshed": gid_refreshed,
        "gid_note": "" if cfg.get("gid") else "首次连接 TCP 时由服务端自动分配 gid",
    }
