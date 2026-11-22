# 映客弹幕实时控制台（还在测试中）

> **项目状态：还在测试中，接口和采集行为可能随时调整。**

这是一个基于 FastAPI + Server-Sent Events 的映客弹幕实时采集与查看工程。  
它尝试从映客的私有 TCP 链路中还原弹幕数据，并提供一个适合本地调试的 Web 控制台。

---

## 项目简介

项目主要解决三件事：

1. **实时采集**：连接映客直播间，解析私有 TCP 流量。
2. **分类整理**：将弹幕、礼物、点赞、进场、关注/分享、排行等消息分类。
3. **可视化**：在 Web 控制台里查看实时消息，并支持导出 CSV。

当前 Web 端已经是深色控制台风格，包含：

- 顶部连接控制区
- 中间实时弹幕流面板
- 右侧会话状态与分类过滤栏
- 热门直播间横向卡片栏
- 消息 DOM 上限，避免长时间采集后页面越来越重

---

## 快速开始

### 1. 安装依赖

```powershell
python -m pip install -r requirements.txt
```

### 2. 启动服务

可以直接双击：

```text
启动弹幕GUI.bat
```

或者手动执行：

```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8801
```

### 3. 打开页面

浏览器访问：

```text
http://127.0.0.1:8801
```

然后在页面里选择热门直播间，或输入主播 UID / 直播间链接 / liveid 后连接。

---

## 主要能力

- 实时弹幕采集
- 分类过滤
- 会话状态展示
- CSV 导出
- 历史文件查看
- 浏览器 UI 冒烟测试
- 私有 TCP 协议探索

---

## 项目结构

```text
.
├── app.py                        # FastAPI 服务与 SSE 接口
├── inke_tcp_collector.py         # TCP 采集器与热门房间接口
├── danmu_client.py               # 弹幕客户端骨架
├── decoder.py                    # 协议解码
├── category.py                   # 消息分类
├── recorder.py                   # CSV 会话录制
├── static/
│   └── index.html                # Web 控制台
├── tests/
│   ├── selftest.py               # 基础自检
│   └── ui_smoke.spec.js          # 浏览器 UI 回归测试
├── docs/
│   ├── architecture/             # 架构文档
│   └── superpowers/              # 设计与实施记录
├── reverse/                      # 逆向研究资料与辅助脚本
└── requirements.txt
```

---

## 本地测试

基础自检：

```powershell
python tests/selftest.py
```

UI 冒烟测试需要本地服务运行在 `http://127.0.0.1:8801`：

```powershell
npx --yes --package @playwright/test playwright test tests/ui_smoke.spec.js --reporter=line
```

---

## 逆向研究说明

项目目录中保留了部分逆向研究文档和辅助脚本，主要用于理解：

- 弹幕链路
- TCP 协议候选
- 鉴权与签名流程
- 消息分类结构

仓库不会提交：

- APK 原始样本
- 反编译输出
- 抓包日志
- 导出数据
- 临时浏览器截图和测试产物

---

## 免责声明

本项目仅供学习与研究使用。  
请遵守目标应用的服务条款，控制访问频率，不要用于骚扰、爬取隐私数据或其他违规用途。

---

## 路线图

- [ ] 继续验证 TCP 长连接与订阅协议
- [ ] 提升消息分类准确率
- [ ] 优化断线重连与会话恢复
- [ ] 增加更完整的自动化测试
- [ ] 支持多房间并行采集
