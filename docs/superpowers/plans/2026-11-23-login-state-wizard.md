# 映客登录态读取向导 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在 Web 页面引导下，用 root Android 设备登录映客，并把 TCP 弹幕采集所需的登录态参数保存到本地配置。

**Architecture:** 新增独立的 `login_state.py` 负责 ADB 检测、root 检测、SharedPreferences 读取、字段汇总、配置保存和脱敏预览；`app.py` 暴露状态/唤醒/同步 API；`static/index.html` 提供分步向导；`inke_tcp_collector.py` 优先加载本地登录态配置。页面不接收、不保存手机号、密码、短信验证码。

**Tech Stack:** Python 3.13、FastAPI、ADB、XML SharedPreferences、本地 JSON 配置、原生 HTML/JS。

**Spec:** A+C 精简版方案；`逆向实战记录_映客.md` 18.33-18.38；用户在 2026-11-23 的确认。

## Global Constraints

- 不接收、不保存账号密码、短信验证码或第三方登录 token。
- 首版只支持 root Android / root 模拟器；非 root 设备必须明确提示不支持。
- 真实登录态只能写入 `reverse/references/inke_runtime_config.local.json`，该文件必须被 `.gitignore` 忽略。
- 页面展示字段必须脱敏，不展示完整 `sid/gid/smid/clientId`。
- 采集器必须在存在本地登录态配置时优先使用它。

## Review Focus

- 非 root 手机点击同步时，必须返回明确错误，不能假装成功。
- `sid` 缺失时，必须标为缺失，不能用假值静默替代。
- 用户尚未在手机登录时，必须提示先登录，不能写入半套配置。
- 本地登录态文件不能进入 Git。
- 页面不能出现密码/验证码输入框。

---

### Task 1: 登录态读取模块

**Files:**
- Create: `login_state.py`
- Modify: `reverse/references/inke_runtime_config.example.json`
- Create: `.gitignore` 或追加忽略项
- Test: `tests/test_login_state.py`

**Interfaces:**
- Produces:
  - `check_environment(serial="emulator-5554") -> dict`
  - `read_login_state(serial="emulator-5554", config_path=None) -> dict`
  - `save_login_state(result: dict, output_path=None) -> str`
  - `mask_login_state(result: dict) -> dict`

- [ ] **Step 1: 写失败测试**

覆盖 XML 解析、字段缺失、脱敏、非 root 返回失败。

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_login_state.py -v`
Expected: FAIL。

- [ ] **Step 3: 实现 ADB 环境检测**

检测 `adb`、设备在线、`adb shell id` 是否 root、映客是否安装。

- [ ] **Step 4: 实现 SharedPreferences 读取**

读取：
  - `duomi_share_preference.xml` 的 `pre_loginuid_for_hotfix`、`PHONE_SMID`、`PHONE_DEVI`、`app_client_version`
  - `Connection_Gid_Store.xml` 的 `conn_gid-tcp-<uid>`
  - `Connection_Session.xml` 的 `session`
  - `atom_sp.xml` 的 `smid`
  - `sp_name_app_unique_id.xml` 的 `app_unique_id`

- [ ] **Step 5: 实现 sid 读取与回退**

优先从运行时可访问的登录缓存读取 `session/sid`；找不到时从已有本地/MITM 配置回退，并把来源写进结果；仍找不到则标记缺失。

- [ ] **Step 6: 实现保存与脱敏**

合并基础配置和新字段，保存到 `inke_runtime_config.local.json`；返回脱敏预览。

- [ ] **Step 7: 运行测试确认通过**

Run: `python -m pytest tests/test_login_state.py -v`
Expected: PASS。

---

### Task 2: Web API

**Files:**
- Modify: `app.py`
- Test: `tests/test_login_api.py`

**Interfaces:**
- Consumes: Task 1 的四个函数。
- Produces:
  - `GET /api/login/status`
  - `POST /api/login/open`
  - `POST /api/login/sync`

- [ ] **Step 1: 写失败测试**

用 FastAPI TestClient monkeypatch `login_state` 函数，断言三个接口返回结构。

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_login_api.py -v`
Expected: FAIL。

- [ ] **Step 3: 实现三个接口**

`/api/login/status` 返回环境、root、App、配置摘要；`/api/login/open` 调 `wake_and_launch()`；`/api/login/sync` 调 `read_login_state()` 和 `save_login_state()`。

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_login_api.py -v`
Expected: PASS。

---

### Task 3: Web 向导 UI

**Files:**
- Modify: `static/index.html`
- Test: `tests/ui_smoke.spec.js`

**Interfaces:**
- Consumes: Task 2 三个接口。

- [ ] **Step 1: 写 UI 冒烟断言**

断言页面存在“登录向导”入口、三步说明、无密码/验证码输入框。

- [ ] **Step 2: 实现向导面板**

加入三步：
  1. 检查环境
  2. 打开映客并手动登录
  3. 读取并保存登录态

- [ ] **Step 3: 实现状态展示**

显示 root/设备/App/字段齐全状态，字段脱敏展示。

- [ ] **Step 4: 运行 lint 和 UI 冒烟**

Run: lint + `npx playwright test tests/ui_smoke.spec.js`
Expected: PASS。

---

### Task 4: 采集器优先使用本地登录态

**Files:**
- Modify: `inke_tcp_collector.py`
- Test: `tests/test_collector_config.py`

**Interfaces:**
- Consumes: `reverse/references/inke_runtime_config.local.json`

- [ ] **Step 1: 写失败测试**

断言存在 local 配置时优先加载；不存在时回退 example/base 配置。

- [ ] **Step 2: 实现动态配置路径解析**

`load_runtime_config(path=None)` 优先 local。

- [ ] **Step 3: 运行测试确认通过**

Run: `python -m pytest tests/test_collector_config.py -v`
Expected: PASS。

---

### Task 5: 文档和使用说明

**Files:**
- Modify: `README.md`
- Modify: `逆向实战记录_映客.md`

- [ ] **Step 1: 更新 README**

加入首次使用登录向导、root 限制、隐私说明。

- [ ] **Step 2: 追加逆向记录**

新增 18.39：登录态读取向导实现。

- [ ] **Step 3: 全量验证**

Run: `python -m pytest`, `python -m py_compile app.py login_state.py inke_tcp_collector.py`
Expected: PASS。
