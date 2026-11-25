import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))

import http_login_probe as p


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["sms", "login", "dry"], required=True)
    ap.add_argument("--area-code", default="86")
    ap.add_argument("--region", default="cn")
    ap.add_argument("--request-id", default="")
    return ap.parse_args()


def main():
    args = parse_args()
    phone = os.environ.get("INKE_TEST_PHONE", "")
    code = os.environ.get("INKE_SMS_CODE", "")

    if args.step == "dry":
        print(json.dumps({
            "phone_secret": p.phone_secret(args.area_code, "13800138000"),
            "phone_rsa_len": len(p.encrypt_phone(args.area_code, "13800138000")),
            "query": p.build_query(),
        }, ensure_ascii=False))
        return

    if not phone:
        print("缺少环境变量 INKE_TEST_PHONE")
        return

    if args.step == "sms":
        r = p.send_sms_code(phone, args.area_code, args.region)
        print(json.dumps(r, ensure_ascii=False))
        return

    if not code:
        print("缺少环境变量 INKE_SMS_CODE")
        return
    if not args.request_id:
        print("缺少 --request-id")
        return
    r = p.login_with_code(phone, code, args.request_id, args.area_code, args.region)
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
