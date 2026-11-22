# -*- coding: utf-8 -*-
"""统一 APK 获取入口：按包名 + 来源下载 -> 校验哈希 -> 登记 manifest。

模式：
  register  手工下载后登记（任何来源通用，最可靠）
  apkeep    调 EFForg/apkeep 从 google-play / apk-pure / f-droid 下载
  market    调 halifox/app_market_crawler 从国内商店抓下载地址（需先装该工具）

用法示例：
  python fetch.py register --package com.inke.tv --apk D:/downloads/inke.apk --source manual
  python fetch.py apkeep --package com.inke.tv --source apk-pure --version 8.5.5
  python fetch.py market --package com.inke.tv --market yingyongbao

设计原则：不重复造爬虫。外部工具只负责拿到 APK，本脚本统一做校验 + 登记，
后续 REA 分析只认 manifest.json 里的记录。
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
APKS_DIR = HERE.parent / "apks"
MANIFEST = HERE / "manifest.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data.setdefault("items", [])
    return data


def save_manifest(data):
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def register(package, apk_path, source, version=None, source_url=None, note=None, fingerprint=None):
    """登记一个已下载的 APK：复制到 apks/ 并计算 SHA-256。"""
    src = Path(apk_path).resolve()
    if not src.is_file():
        print("APK 不存在:", src)
        return 1
    if src.suffix.lower() != ".apk":
        print("警告: 文件后缀不是 .apk:", src.name)

    version = version or "unknown"
    APKS_DIR.mkdir(parents=True, exist_ok=True)
    dest = APKS_DIR / f"{package}_{version}.apk"
    if src != dest:
        shutil.copy2(src, dest)

    item = {
        "package": package,
        "version": version,
        "source": source,
        "source_url": source_url,
        "sha256": sha256(dest),
        "signer_fingerprint_sha256": fingerprint,
        "path": str(dest.relative_to(HERE.parent.parent)).replace("\\", "/"),
        "size": dest.stat().st_size,
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": note or "",
    }
    data = load_manifest()
    data["items"] = [x for x in data["items"]
                     if not (x.get("package") == package and x.get("version") == version)]
    data["items"].append(item)
    save_manifest(data)
    print("已登记:", json.dumps(item, ensure_ascii=False, indent=2))
    print("\n下一步: 用 REA inspect_apk_signature 校验签名，再 inspect_android_package 开始静态分析")
    return 0


def run_apkeep(package, source, version, email=None, token=None):
    """调用 apkeep 下载；需要本机已装 apkeep（cargo install apkeep 或 Docker）。"""
    exe = shutil.which("apkeep")
    if not exe:
        print("未找到 apkeep。安装方式见 README.md：cargo install apkeep / Docker / Termux pkg install apkeep")
        return 1
    target = f"{package}@{version}" if version else package
    cmd = [exe, "-a", target, "-d", source]
    if source == "google-play":
        if not email or not token:
            print("google-play 源需要 --email 与 --token (AAS token)")
            return 1
        cmd += ["-e", email, "-t", token]
    cmd += [str(APKS_DIR)]
    APKS_DIR.mkdir(parents=True, exist_ok=True)
    print("执行:", " ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        return rc
    apks = sorted(APKS_DIR.glob(f"{package}*.apk"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not apks:
        print("apkeep 未产出 APK")
        return 1
    return register(package, apks[0], source, version=version, source_url=f"apkeep:{source}")


def run_market(package, market):
    """提示调用 app_market_crawler 抓国内商店下载地址（工具需另行安装）。"""
    try:
        import app_market_crawler  # noqa: F401
    except ImportError:
        print("未安装 app_market_crawler。参见 reverse/fetch_apk/README.md 的 A 节。")
        print("安装后其 '下载地址' 字段接入本脚本；本骨架不内置爬虫以免接口失效后维护困难。")
        return 1
    print("检测到 app_market_crawler，请按包名模式抓取下载地址：")
    print(f"  python -m app_market_crawler crawl {market} --mode package-list --packages {package} --history")
    print("拿到下载地址后，用 register 模式登记本地 APK。")
    return 0


def main():
    p = argparse.ArgumentParser(description="统一 APK 获取与登记")
    sub = p.add_subparsers(dest="mode", required=True)

    r = sub.add_parser("register", help="登记已下载的 APK（任何来源）")
    r.add_argument("--package", required=True)
    r.add_argument("--apk", required=True, help="本地 APK 路径")
    r.add_argument("--source", default="manual")
    r.add_argument("--version")
    r.add_argument("--source-url")
    r.add_argument("--fingerprint", help="签名证书 SHA-256（REA inspect_apk_signature 可查）")
    r.add_argument("--note")

    a = sub.add_parser("apkeep", help="用 apkeep 从 google-play/apk-pure/f-droid 下载")
    a.add_argument("--package", required=True)
    a.add_argument("--source", default="apk-pure", choices=["google-play", "apk-pure", "f-droid"])
    a.add_argument("--version")
    a.add_argument("--email")
    a.add_argument("--token")

    m = sub.add_parser("market", help="国内商店（app_market_crawler）提示入口")
    m.add_argument("--package", required=True)
    m.add_argument("--market", default="yingyongbao",
                   choices=["360", "baidu", "huawei", "lenovo", "samsung",
                            "yingyongbao", "yingyonghui", "ppzhushou", "vivo",
                            "wandoujia", "xiaomi"])

    args = p.parse_args()
    if args.mode == "register":
        return register(args.package, args.apk, args.source, args.version,
                        args.source_url, args.note, args.fingerprint)
    if args.mode == "apkeep":
        return run_apkeep(args.package, args.source, args.version, args.email, args.token)
    if args.mode == "market":
        return run_market(args.package, args.market)
    return 1


if __name__ == "__main__":
    sys.exit(main())
