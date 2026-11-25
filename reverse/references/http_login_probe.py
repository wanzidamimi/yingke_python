# -*- coding: utf-8 -*-
"""映客手机号 + 短信验证码登录探针。

只用于隔离测试，不接入现有采集主流程。
手机号和验证码只从环境变量/运行时参数传入，不落盘。
"""
import base64
import hashlib
import hmac
import json
import random
import time
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
LOCAL_CONFIG = ROOT / "reverse" / "references" / "inke_runtime_config.local.json"
BASE_CONFIG = ROOT / "reverse" / "references" / "inke_runtime_config.json"

PKG = "com.meelive.ingkee"
APPID = "OklL"
AUTH_SECRET = b"1ba5fb066d7e33d5"

SMS_URL = "https://service.inke.cn/user/account/phone_code"
LOGIN_URL = "https://service.inke.cn/user/account/phone_login"

# 来自已安装 APK assets/rsa_public_key.pem；公钥不是秘密。
RSA_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmjZzbDPaO9tA7qMMoIZL
E7JZDpaMe9mU3a1aATz+Mmi1PMzfmdOQQmsKipIkN05i9JwBP3bYnNQCHD6L/zsD
QOcNrxVdyta1jn+Z2LqfOjCD9tm7nN36BlppShOnloKBO5459Eq6tT57djMxdbze
B57YDuM4bA1FUNljSRSmGM3ecm+wPxNc3jatG4PVt54fBWrWb52xL7nAj6oBOe1g
14xrdv70e4ruTkI6U8cfXMm6GYR7KwKGxGoHznBGalkYJXn5QPpKISDLIqwNYl/i
kO0qoJvFlg7QAORXDGWK+RIhEPi3lSLGff5fZqqhtOOoW5vs0dFrAa7N7RkPHXvE
/QIDAQAB
-----END PUBLIC KEY-----
"""


def md5_hex(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def phone_secret(area_code: str, phone: str) -> str:
    raw = "%s%s" % (area_code, str(phone).replace(" ", ""))
    return md5_hex(raw)


def login_secret(area_code: str, phone: str, code: str) -> str:
    raw = "%s%s#%s" % (area_code, str(phone).replace(" ", ""), code)
    return md5_hex(raw)


def load_public_key():
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    return load_pem_public_key(RSA_PUBLIC_KEY_PEM.encode("utf-8"))


def encrypt_phone(area_code: str, phone: str, key_pem: str = RSA_PUBLIC_KEY_PEM) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    public_key = serialization.load_pem_public_key(key_pem.encode("utf-8"))
    raw = ("%s%s" % (area_code, str(phone).replace(" ", ""))).encode("utf-8")
    encrypted = public_key.encrypt(raw, padding.PKCS1v15())
    return encrypted.hex()


def authorization(body: bytes, method: str, query: str, timestamp: str) -> str:
    body_md5 = ""
    if body:
        body_md5 = base64.b64encode(hashlib.md5(body).digest()).decode()
    message = "%s\n%s\n%s\n%s\n%s" % (
        PKG,
        body_md5,
        method.upper(),
        timestamp,
        query,
    )
    sig = base64.b64encode(
        hmac.new(AUTH_SECRET, message.encode("utf-8"), hashlib.sha1).digest()
    ).decode()
    return "InkeV1 %s:%s" % (APPID, sig)


def _json_body(params: dict) -> bytes:
    return json.dumps(
        params,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def build_sms_body(params: dict) -> str:
    keys = ["phone", "region", "secret", "source", "area_code", "finger_list"]
    ordered = {k: params[k] for k in keys if k in params}
    return _json_body(ordered).decode("utf-8")


def build_login_body(params: dict) -> str:
    keys = [
        "request_id", "phone", "code", "secret", "dev_name",
        "finger_list", "link", "visitor_uid", "target_uid",
    ]
    ordered = {k: params[k] for k in keys if k in params}
    return _json_body(ordered).decode("utf-8")


def load_common_config(path=None):
    p = Path(path) if path else (LOCAL_CONFIG if LOCAL_CONFIG.exists() else BASE_CONFIG)
    with open(p, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg.get("auth", {}).get("bus_buf", {})


def build_query(extra=None, xid=1, include_user=False, config=None):
    """按 MITM 真值模板构造 HTTP query。"""
    cfg = config or load_common_config()
    q = {
        "cc": cfg.get("cc", "TG36064"),
        "dev_name": cfg.get("dev_name", "Google"),
        "ik_appid": cfg.get("ik_appid", "OklL"),
        "xid": str(xid),
        "cv": cfg.get("cv", "IK9.9.05_Android"),
        "ast": "1",
        "lc": cfg.get("lc", "3726b262d726e165"),
        "sign_from": "android",
        "ua": cfg.get("ua", "GooglePixel3"),
        "osversion": cfg.get("osversion", "android_28"),
    }
    for key in ("smid", "conn", "mtid", "mtxid", "aid", "source_info"):
        if cfg.get(key):
            q[key] = cfg[key]
    if include_user:
        for key in ("uid", "sid"):
            if cfg.get(key):
                q[key] = cfg[key]
    code_key = "code%d" % random.randint(0, 2 ** 31 - 1)
    q[code_key] = str(int(time.time() * 1000))
    if extra:
        q.update(extra)
    return urlencode(q)


def _headers(body: bytes, query: str, timestamp: str):
    return {
        "Authorization": authorization(body, "POST", query, timestamp),
        "Client-TimeStamp": timestamp,
        "Content-Type": "text/plain; charset=utf-8",
        "User-Agent": "okhttp/3.12.13",
        "Accept-Encoding": "gzip",
    }


def _post(url, body_text, query, impersonate="chrome"):
    from curl_cffi import requests as creq

    body = body_text.encode("utf-8")
    full_url = url + "?" + query
    ts = str(int(time.time() * 1000))
    r = creq.post(
        full_url,
        data=body,
        headers=_headers(body, query, ts),
        impersonate=impersonate,
        timeout=15,
    )
    return r.status_code, r.text


def send_sms_code(phone, area_code="86", region="cn", config=None):
    """发送短信验证码；只在调用时接收 phone，不保存。"""
    cfg = config or load_common_config()
    body_text = build_sms_body({
        "phone": encrypt_phone(area_code, phone),
        "region": region,
        "secret": phone_secret(area_code, phone),
        "source": "login",
        "area_code": str(area_code),
        "finger_list": {},
    })
    query = build_query(xid=1, include_user=False, config=cfg)
    status, text = _post(SMS_URL, body_text, query)
    return {"status": status, "body": text, "query": query}


def login_with_code(phone, code, request_id, area_code="86", region="cn", config=None):
    """用短信验证码登录；验证码只在调用时接收，不保存。"""
    cfg = config or load_common_config()
    body_text = build_login_body({
        "request_id": request_id,
        "phone": encrypt_phone(area_code, phone),
        "code": code,
        "secret": login_secret(area_code, phone, code),
        "dev_name": cfg.get("dev_name", "GooglePixel3"),
        "finger_list": {},
        "link": 0,
        "visitor_uid": 0,
        "target_uid": 0,
    })
    query = build_query(xid=2, include_user=False, config=cfg)
    status, text = _post(LOGIN_URL, body_text, query)
    return {"status": status, "body": text, "query": query}


def validate_login_result(data):
    """校验登录响应里的 secret 是否与 session/uid 匹配。"""
    if not isinstance(data, dict):
        return False
    uid = str(data.get("uid") or "")
    session = data.get("session") or ""
    secret = data.get("secret") or ""
    expected = md5_hex("IKLOGIN#RsDyXjH#%s#%s#MsJzKdY" % (session, uid))
    return secret == expected
