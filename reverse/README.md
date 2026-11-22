# 逆向作业区

本目录只放「逆向过程产物」，与运行侧代码解耦。

```
reverse/
├── apks/          # APK 样本（体积大，建议加进 .gitignore）
├── captures/      # 抓包导出：HAR / SAZ / pcap / 二进制消息样本
├── evidence/      # REA 导出的 Evidence bundle（export_evidence_bundle）
└── rea_notes.md   # 分析记录：候选接口、类/方法、签名算法线索、未解问题
```

## 记录原则（沿用 REA 的 Evidence 纪律）

每条结论标注三类身份，避免把猜测当事实：

- **观察（observed）**：REA 工具或抓包直接返回的事实，附 Evidence ID / 抓包文件位置。
- **推断（inferred）**：基于观察的推测，写明依据。
- **未知（unknown）**：静态分析看不到、需动态验证的点（反射、动态加载、so 内部逻辑等）。

## 标准作业顺序

1. **静态先行**：APK 放进 `apks/` → REA `inspect_android_package` → `search_android_classes` → `inspect_android_method` → `trace_android_references`。
2. **缩小范围**：把候选接口 URL / 类名 / 方法名记进 `rea_notes.md`，标清「观察 / 推断」。
3. **动态确认**：真机/模拟器代理抓包，验证候选接口是否真的承载弹幕；导出到 `captures/`。
4. **离线复盘**：用 REA `inspect_web_network_capture` 解析 HAR/SAZ，交叉比对静态候选。
5. **签名攻坚**：so 里的签名优先 Frida hook；拿到结果后回填 `rea_notes.md`，再落到 `../signer.py`。

## REA 使用提示

- Android 工具**不需要**先 `open_binary`，每个调用都自带 APK 路径与选择器。
- 方法重载多时，从 `inspect_android_class` 的清单里选 `overload_index`，不要猜。
- `REA_JADX_MCP_JAR` 与 JDK21 已在 CodeBuddy MCP 注册里显式指定；重启客户端后生效。
- 若 MCP 里看不到 REA 工具：先重启 CodeBuddy；仍不行则 `rea doctor --json` 看注册状态。

## 合规

APK 与抓包可能含个人信息，仅本地研究使用，不要外传。
