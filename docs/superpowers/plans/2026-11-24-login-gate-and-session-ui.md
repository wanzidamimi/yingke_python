# 映客登录门禁与当前用户面板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户进入 Web 页面时明确知道当前是否已有可用映客登录凭证；没有凭证时弹窗引导登录，有凭证时在右上角显示当前账号并支持退出登录。

**Architecture:** 新增独立 `login_session.py`，只把 `inke_runtime_config.local.json` 视为用户凭证；`inke_runtime_config.json` 降级为协议模板，不再作为可登录凭证。`app.py` 增加当前会话与登出接口，并在 `/api/start` 前做门禁。前端在页面加载、点击房间卡片、点击“连接采集”时检查会话；无凭证弹出登录方式选择框，登录后刷新右上角用户卡片。

**Tech Stack:** Python 3.13、FastAPI、原生 HTML/JS、unittest、JSON 本地文件。

**Spec:** 用户 2026-11-24 需求：“增加一个验证，如果当前没有可以用的登录凭证，弹一个框要求用户先登录；如果有登录凭证需要在 web 页面右上角显示当前用户信息，用户还可以退出登陆。”

## Global Constraints

- 不显示完整 `sid`、`gid`、`clientId`、`source_info`。
- 不接收、不保存密码、短信验证码原文；手机号若展示必须脱敏。
- `inke_runtime_config.local.json` 是唯一有效用户凭证文件。
- `inke_runtime_config.json` 是模板，不得包含真实 `uid/sid/gid`，不得作为登录凭证回退。
- “退出登录”必须同时阻止后续 `/api/start` 采集，不能只删文件。
- `gid=""` 不算失效；首次 TCP 认证时服务端会分配并写回本地配置。
- 首版只做“本地凭证结构可用”判断，不调用服务端 `check_session` 做在线有效性校验。

## Review Focus

- 用户未登录时，点击“连接采集”和热门房间卡片都必须被拦截并弹窗。
- 用户已登录时，右上角必须显示当前账号，且不能泄露 `sid/gid`。
- 用户退出后，即使 `inke_runtime_config.json` 模板里残留旧值，也不能继续采集。
- HTTP 手机号登录和 ADB/root 同步成功后，都必须刷新右上角用户信息。
- 弹窗必须能引导到两种已有登录方式，不能出现密码输入框。

---

### Task 1: 会话状态模块

**Files:**
- Create: `login_session.py`
- Modify: `reverse/references/inke_runtime_config.json`
- Modify: `.gitignore`
- Test: `tests/test_login_session.py`

**Interfaces:**
- Produces:
  - `current_session(config_path=None, meta_path=None) -> dict`
  - `logout(config_path=None, meta_path=None) -> dict`
  - `mark_logged_in(login_method, uid, masked_phone="", gid_status="pending") -> None`
  - `credential_valid(config: dict) -> bool`

- [ ] **Step 1: 写失败测试**

覆盖：

```text
无 local 配置 -> logged_in=False
local 配置缺 uid/sid -> logged_in=False
uid+sid 完整但 gid 为空 -> logged_in=True, gid_status=pending
logout 删除 local 配置和 session meta
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_login_session -v`
Expected: FAIL。

- [ ] **Step 3: 实现 `login_session.py`**

状态返回结构：

```json
{
  "ok": true,
  "logged_in": true,
  "reason": "",
  "user": {
    "uid": 778965813,
    "login_method": "http_sms",
    "phone_masked": "176****9175",
    "gid_status": "ready",
    "logged_at": "2026-11-24 21:30:00"
  }
}
```

未登录时：

```json
{
  "ok": true,
  "logged_in": false,
  "reason": "missing_local_config",
  "user": null
}
```

`credential_valid()` 判定：

```text
uid 非 0 且 sid 非空
```

不要求 `gid` 非空。

- [ ] **Step 4: 把 `inke_runtime_config.json` 改成模板**

清空：

```text
uid
gid
auth.uid
auth.bus_buf.uid
auth.bus_buf.sid
auth.bus_buf.gid
enter_room.uid
enter_room.gid
enter_room.bus_buf.uid
enter_room.bus_buf.gid
```

保留设备/协议模板字段：

```text
cc / smid / dev_name / ik_appid / conn / ua / mtid / cv / lc / devi / mtxid / osversion / aid
```

- [ ] **Step 5: 添加 session meta 忽略项**

`.gitignore` 增加：

```text
reverse/references/login_session.json
```

- [ ] **Step 6: 测试通过**

Run: `python -m unittest tests.test_login_session -v`
Expected: PASS。

---

### Task 2: 后端会话接口与启动门禁

**Files:**
- Modify: `app.py`
- Test: `tests/test_login_gate_api.py`

**Interfaces:**
- Consumes: Task 1 的 `current_session()` / `logout()`
- Produces:
  - `GET /api/session/current`
  - `POST /api/session/logout`
  - `/api/start` 前置门禁

- [ ] **Step 1: 写失败测试**

覆盖：

```text
GET /api/session/current 未登录 -> logged_in=False
GET /api/session/current 已登录 -> user.uid 正确
POST /api/session/logout -> local 配置被删除
未登录 POST /api/start -> ok=False, reason=not_logged_in
已登录 POST /api/start -> 正常进入原有流程
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_login_gate_api -v`
Expected: FAIL。

- [ ] **Step 3: 实现接口**

```python
@app.get("/api/session/current")
@app.post("/api/session/logout")
```

`/api/start` 在获取锁前调用：

```python
session = current_session()
if not session["logged_in"]:
    return {"ok": False, "reason": "not_logged_in", "error": "请先登录映客账号"}
```

- [ ] **Step 4: 登录成功后写入 session meta**

修改：

```text
POST /api/login/http/verify 成功后调用 mark_logged_in("http_sms", uid, masked_phone)
POST /api/login/sync 成功后调用 mark_logged_in("adb_root", uid)
```

- [ ] **Step 5: 测试通过**

Run: `python -m unittest tests.test_login_gate_api -v`
Expected: PASS。

---

### Task 3: 前端登录弹窗与右上角用户面板

**Files:**
- Modify: `static/index.html`
- Test: `tests/test_ui_login_gate.py`

**Interfaces:**
- Consumes:
  - `GET /api/session/current`
  - `POST /api/session/logout`

- [ ] **Step 1: 写失败测试**

用文本断言确认页面包含：

```text
id="loginModal"
id="userChip"
id="logoutBtn"
fetch('/api/session/current')
fetch('/api/session/logout')
```

并确认弹窗没有密码输入框：

```text
loginModal 区块内不含 type="password"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m unittest tests.test_ui_login_gate -v`
Expected: FAIL。

- [ ] **Step 3: 增加右上角用户卡片**

在 `header.controls` 内增加：

```html
<div id="userChip" class="user-chip hidden">...</div>
```

显示：

```text
UID
登录方式
gid 状态
退出登录按钮
```

禁止显示完整敏感字段。

- [ ] **Step 4: 增加登录弹窗**

新增：

```html
<div id="loginModal" class="modal-backdrop hidden">
  <div class="modal">
    ...
    <button id="modalHttpLogin">手机号验证码登录</button>
    <button id="modalAdbLogin">ADB 设备同步</button>
    <button id="modalLater">稍后再说</button>
  </div>
</div>
```

行为：

```text
手机号验证码登录 -> 切到右侧手机号页签并聚焦手机号输入框
ADB 设备同步 -> 切到右侧 ADB 页签
稍后再说 -> 关闭弹窗，但采集仍被门禁拦截
```

- [ ] **Step 5: 前端会话逻辑**

实现：

```javascript
async function refreshSession()
function openLoginModal()
function closeLoginModal()
function renderUserChip(user)
async function logoutCurrentUser()
```

调用点：

```text
页面启动 -> refreshSession()
startSession() -> 先 refreshSession()，未登录则 openLoginModal() 并 return
房间卡片点击 -> 走 startSession()，自动被门禁覆盖
HTTP 登录成功 -> refreshSession()
ADB 同步成功 -> refreshSession()
退出按钮 -> logoutCurrentUser()
```

- [ ] **Step 6: 测试通过**

Run: `python -m unittest tests.test_ui_login_gate -v`
Expected: PASS。

---

### Task 4: 全量验证与文档

**Files:**
- Modify: `README.md`
- Modify: `逆向实战记录_映客.md`

- [ ] **Step 1: 全量测试**

Run:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m py_compile app.py login_session.py inke_tcp_collector.py http_login_web.py
```

Expected: PASS。

- [ ] **Step 2: Web 冒烟**

启动服务后验证：

```text
GET /                -> 200
GET /api/session/current -> JSON
POST /api/start 未登录 -> not_logged_in
```

- [ ] **Step 3: 文档更新**

记录：

```text
首次打开页面的登录门禁
右上角当前用户
退出登录行为
local 配置是唯一凭证源
模板配置不再作为凭证回退
```

---

## Self-Review

- [x] 覆盖无凭证弹窗。
- [x] 覆盖有凭证右上角用户信息。
- [x] 覆盖退出登录。
- [x] 覆盖退出后禁止采集。
- [x] 覆盖 HTTP 登录和 ADB 同步后刷新状态。
- [x] 明确 `gid=""` 不阻塞登录门禁。
- [x] 明确不保存手机号/验证码/完整敏感字段。
- [x] 未加入服务端 `check_session` 在线校验，作为后续增强，不在本计划内。
