# Web 弹幕控制台美化实施计划

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重排映客弹幕 Web 控制台，使弹幕流有明确边界且整体更美观。

**Architecture:** 保留现有 API 与事件流，重写单页 HTML/CSS 布局为三区 shell，JS 只调整渲染与列表上限。

**Tech Stack:** FastAPI + 原生 HTML/CSS/JS + Playwright UI smoke test。

**Spec:** docs/superpowers/specs/2026-11-22-web-danmu-ui-design.md

## Global Constraints
- 不修改后端接口。
- 不引入前端框架或运行时依赖。
- 弹幕列表必须有内部滚动边界。

## Tasks
### Task 1: UI 回归测试
- Create: tests/ui_smoke.spec.js
- Step 1: 写断言：120 条弹幕后 `#list` 高度 < 视口高度 80%，页面无横向溢出。
- Step 2: 在旧页面上运行并确认失败。
- Step 3: 不提交；等待修复后重跑。

### Task 2: 控制台布局实现
- Modify: static/index.html
- Step 1: 实现 header / workspace / side-panel 布局和直播间控制台风格。
- Step 2: 保留 SSE、房间点击、分类过滤、导出、历史行为。
- Step 3: 限制 DOM 消息数量到 300 条。
- Step 4: 运行 UI 测试和项目自检。

### Task 3: 真实浏览器验证
- Step 1: Playwright 打开本地 8801 页面。
- Step 2: 截屏保存 `.playwright-cli/`。
- Step 3: 确认无 console 错误，除已知 favicon 404 将通过内联图标消除。
