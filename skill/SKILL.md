---
name: interview-simulator
description: AI 面试模拟官——输入目标岗位和简历，AI 化身不同风格面试官（业务/HR/总监/压力）逐轮追问、针对回答实时评价打分、指出薄弱点并给改进建议，面试结束自动沉淀历史记录追踪进步。当用户需要练习面试、做求职模拟面试训练、针对简历做 AI 模拟面试、或想要一个"多轮对话+实时评分+弱点诊断"的 AI 应用时使用。触发词：面试模拟、模拟面试、AI面试官、面试练习、简历面试、求职准备、面试复盘。
agent_created: true
---

# AI 面试模拟官（Interview Simulator）

## 何时使用

- 用户要**练面试**：求职前用 AI 当面试官模拟实战，降低真实面试的陌生感。
- 用户要**针对简历出题**：贴一份简历，AI 围绕简历里的项目逐轮深挖、挑漏洞。
- 用户要**知道差在哪**：每轮实时打分 + 弱点标签，面试后看高频薄弱点和进步趋势。
- 用户想看一个**体现 AI 核心价值的例子**：多轮追问、针对输入动态生成、实时评价——纯规则代码做不到。

## 核心功能

- **MVP（基础面试）**：输入岗位 + 简历 → AI 面试官出题 → 用户作答 → AI 针对回答实时评价 / 打分 / 建议 → 下一题 → 面试总评。
- **迭代 1（AI 能力增强）**：
  - 面试类型切换：业务面（深挖项目）/ HR 面（软素质）/ 总监面（战略思维）/ 压力面（高压追问）
  - 简历诊断分层：空简历（< 80 字）给「零经验应对策略」，非空给「弱点诊断」
  - 追问控制：深挖追问 / 换方向 / 跳过 / 结束，用户掌控节奏
- **迭代 2（个性化闭环 · 历史追踪）**：
  - 每次面试结束自动写 `interview_history.json`（岗位 / 类型 / 轮次 / 平均分 / 弱点标签）
  - 「面试历史」面板：高频薄弱点 Top6（进度条）、得分趋势、历史记录卡片
  - 诊断页读取历史，提示「你历史高频薄弱点是 X（N 次），本次重点准备」

## 如何运行

主程序在 `scripts/interview_server.py`（单文件、零依赖、网页版）。

```bash
# 1. 配置 DeepSeek API Key（见 references/config.md，两种方式任选）
# 2. 运行
python skill/scripts/interview_server.py
# 3. 在自己本机浏览器（推荐无痕）地址栏打开
http://localhost:8824
```

> ⚠️ 不要用工具内的预览面板打开 localhost 链接，那里会弹「白条」（预览面板内置浏览器凭据自动填充），与本工具代码无关。用自己本机 Chrome/Edge 打开即干净。

## 架构要点（可复用范式）

- **内嵌单端口同源**：HTML/CSS/JS 全部内嵌进 `interview_server.py` 一个文件，后端用 `http.server` 单端口（8824）托管前端，`fetch` 走相对路径（`/start`、`/action`），根治前后端分离跨域白屏。
- **防卡死**：必须用 `ThreadingHTTPServer`（非单线程 `HTTPServer`），否则一次 LLM 调用阻塞全站。
- **AI 输出结构化**：系统提示强制方括号标记 `[评价][打分]X/10[建议][弱点]标签[下一题]`，后端正则解析弱点标签（10 个标准维度）用于历史聚合。

## 目录结构

```
skill/
├── SKILL.md                      # 本文件
├── scripts/
│   └── interview_server.py       # 主程序（单文件 Web 应用）
└── references/
    ├── config.md                 # DeepSeek API Key 配置
    ├── resume_samples.md         # 测试/演示用简历样本
    └── best_practices.md         # 使用建议与避坑
```

## 参考文件

- `references/config.md`：如何获取并配置 DeepSeek API Key（环境变量或改代码两种）
- `references/resume_samples.md`：可直接复制粘贴的简历样本（产品经理 / 后端 / 转行）
- `references/best_practices.md`：面试类型怎么选、如何避开白条、如何用历史面板追踪进步
