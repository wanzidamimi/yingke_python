# 映客 HTTP 手机号登录探针 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改动现有弹幕采集主流程的前提下，独立验证映客手机号 + 短信验证码登录接口是否可通过纯 HTTP 完成，并确认需要哪些参数。

**Architecture:** 新增独立探针模块和 CLI，只放在 `reverse/references/` 与 `tests/` 下。探针从源码结论和真实 App 请求捕获中取得参数生成规则，不写死手机号/验证码。先写单元测试锁定手机号 RSA 加密、MD5 secret、Authorization 签名、请求体序列化，再实现最小可用请求脚本。

**Tech Stack:** Python 3.13、curl_cffi、cryptography、hashlib/hmac/base64、FastAPI TestClient（仅测试）、ADB/mitmproxy（仅用于获取真值，不进入主流程）。

**Spec:** 用户要求“先规划接口如何获取、哪些参数必传、是否从源码可获取、红绿测试，不瞎猜；原有逻辑不改，单纯测试这条路是否可行”。

## Global Constraints

- 不修改 `app.py`、`inke_tcp_collector.py`、`login_state.py`、`static/index.html` 等现有主流程。
- 测试手机号只从环境变量传入，不写入任何仓库文件、日志、测试结果。
- 短信验证码只从命令行临时读取，不落盘、不输出、不保存。
- 新增代码只在 `reverse/references/` 与 `tests/` 下。
- 所有真实请求必须可关闭；默认只做参数构造与单元测试，显式 `--send` 才发短信。

## Review Focus

- 手机号加密必须使用 APK 内 `rsa_public_key.pem`，RSA/ECB/PKCS1Padding，结果是否为 hex 或 base64 必须用真值捕获确认。
- `generatePhoneSecret` 与登录 `secret` 公式不同，测试必须分别覆盖。
- Authorization 签名 body_hash 是 body bytes 的 MD5 后 Base64，不是 32 位 hex。
- 公共 query 参数必须来自真值捕获，不用臆测。
- 登录响应字段 `session` / `secret` 必须能校验，secret 校验公式来自源码。

---

### Task 1: 真值捕获登录参数

**Files:**
- Create: `reverse/references/capture_login_request.py`
- Create: `reverse/references/captured_login_params.example.json`
- No production code changes.

**Interfaces:**
- Produces:
  - 一份脱敏后的真实 `phone_code`/`phone_login` query/body 模板
  - `region`、`phone` 加密格式、`secret` 公式验证结果

- [ ] **Step 1: 安装系统 CA 并开启选择性 MITM**
- [ ] **Step 2: 用 App UI 输入测试手机号并点发送验证码**
- [ ] **Step 3: 从 MITM 请求里提取 URL/query/body/headers**
- [ ] **Step 4: 脱敏保存为模板，手机号和验证码不得落盘**

---

### Task 2: 红灯测试

**Files:**
- Create: `tests/test_http_login_probe.py`

**Interfaces:**
- Consumes: Task 1 真值模板
- Requires functions:
  - `md5_hex(text: str) -> str`
  - `phone_secret(area_code: str, phone: str) -> str`
  - `login_secret(area_code: str, phone: str, code: str) -> str`
  - `encrypt_phone(area_code: str, phone: str, key_pem: str) -> str`
  - `authorization(body: bytes, method: str, query: str, timestamp: str) -> str`
  - `build_sms_body(params: dict) -> str`
  - `build_login_body(params: dict) -> str`

- [ ] **Step 1: 写失败测试并运行**
- [ ] **Step 2: 确认模块不存在导致 FAIL**

---

### Task 3: 实现隔离探针

**Files:**
- Create: `reverse/references/http_login_probe.py`
- Create: `reverse/references/run_http_login_probe.py`

**Interfaces:**
- Produces:
  - `send_sms_code(...)`
  - `login_with_code(...)`
  - CLI `--step sms|login --phone-env INKE_TEST_PHONE`

- [ ] **Step 1: 实现 RSA/secret/签名/body 序列化**
- [ ] **Step 2: 实现 `--step sms`**
- [ ] **Step 3: 实现 `--step login`**
- [ ] **Step 4: 绿灯测试全部通过**

---

### Task 4: 文档记录

**Files:**
- Modify: `逆向实战记录_映客.md`
- Create: `reverse/references/http_login_probe_result.md`

- [ ] **Step 1: 记录哪些参数源码可得、哪些依赖真值捕获**
- [ ] **Step 2: 记录可行性结论和未完成项**
