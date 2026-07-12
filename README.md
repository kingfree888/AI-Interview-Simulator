# AI面试模拟官 — 使用说明（v2.2）

## 提交仓库结构（本课程结课提交版）

本仓库按结课要求组织为 **Hermes Agent Skill + 配套数据 / 测试 / 迭代记录**：

```
<仓库>/
├── skill/                    # Skill 文件（Hermes Agent）
│   ├── SKILL.md              # 技能定义（含 yaml 前端配置）
│   ├── scripts/
│   │   └── interview_server.py   # 主程序（单文件 Web 应用，零依赖）
│   └── references/
│       ├── config.md         # DeepSeek API Key 配置
│       ├── resume_samples.md # 测试/演示简历样本
│       └── best_practices.md # 使用建议与避坑
├── data/
│   └── test_resumes.json     # 测试数据集（5份简历 + 期望格式 + 用例）
├── tests/
│   ├── test_record.md        # 测试记录（环境/步骤/结果）
│   ├── test_log.txt          # 测试原始输出日志
│   └── submit_test.py        # 自动化测试脚本
├── iteration/
│   └── iteration_log.md      # 5步迭代法升级说明（3次迭代）
├── 痛点分析报告.md            # 痛点测试与迭代依据
├── 面试记录_*.md              # 真实模拟面试记录（迭代验证素材）
└── README.md                 # 本文件
```

> 运行入口：`python skill/scripts/interview_server.py`，浏览器开 `http://localhost:8824`。
> 选题来源：AI个人系统实践课程 · 场景清单 #8「AI面试模拟官」（★★★零门槛）
> 技术栈：Python 标准库 + DeepSeek 免费 API，单文件、零依赖、网页版

## 一、功能总览

- **MVP（基础面试）**：输入岗位+简历 → 面试官先提问 → 你点「📤 发送回答」作答 → AI 针对你的回答实时评价/打分/建议 → 进入下一题 → 面试总评
- **迭代1（AI能力增强）**：
  - 面试类型切换：业务面 / HR面 / 总监面 / 压力面
  - 简历诊断：空简历（<80字）给「零经验应对策略」，非空给「弱点诊断」
  - 追问控制：深挖追问 / 换方向 / 跳过 / 结束
- **迭代2（个性化闭环 · 历史追踪）**：
  - 每次面试结束自动沉淀记录（岗位 / 类型 / 轮次 / 平均分 / 弱点标签）
  - 「面试历史」面板：高频薄弱点 Top6（进度条）、得分趋势、历史记录卡片
  - 诊断页读取历史，提示你的历史高频薄弱点，本次面试重点准备
- **迭代4（弱点自适应闭环 · 历史反哺出题）**：
  - 开新面试时读取历史 Top3 弱点注入面试官 prompt，开场第一问就点名你的历史弱点
  - 前端「🎯 针对性加练」红色徽章，进面试即见本次是专项加练
  - 历史数据真正反哺到下一次出题，从"看板"变"教练"

## 二、快速开始

### 1. 获取 DeepSeek API Key
- 打开 https://platform.deepseek.com/ → 注册（手机号即可）→ 左侧「API Keys」→ 创建 Key
- 学生有免费额度，个人项目完全够用

### 2. 配置 API Key
打开 `interview_server.py`，修改第 7 行左右的 `API_KEY`：
```python
API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

### 3. 运行
```bash
python interview_server.py
```
终端会打印：`AI面试模拟官 v2.2  http://localhost:8824`

### 4. 打开使用（重要：避开白条）
**在自己本机的 Chrome / Edge 地址栏输入 `http://localhost:8824` 打开**（推荐 Ctrl+Shift+N 无痕模式）。
> 白条说明：它是预览面板内置浏览器在 localhost 存了凭据后弹的自动填充，与页面代码无关。
> 只要用你自己本机浏览器（而非工具内的预览面板）打开，就是干净无白条的。

### 5. 使用流程
1. 填目标岗位（如：产品经理）+ 选面试类型 + 粘贴简历
2. 点「诊断简历，开始面试」→ 看简历分析（含历史薄弱点预警）→ 开始面试
3. AI 面试官出题，你输入回答（Ctrl+Enter 发送）
4. 用「深挖追问 / 换方向 / 跳过 / 结束」控制节奏，每轮实时打分+弱点标签
5. 结束后面试总评；点右上角「📊 面试历史」看成长追踪

## 三、课程要求对照

- ✅ 从清单选 1 个系统（#8），1 天内出 MVP
- ✅ 零门槛技术栈（Python 标准库 + 免费大模型 API，单文件 <200 行）
- ✅ 迭代 2 次以上（迭代1 类型/诊断/追问；迭代2 历史追踪闭环）
- ✅ 每个功能都体现 AI 核心价值（多轮追问、针对简历出题、弱点诊断——纯规则代码做不到）

## 四、文件说明

| 文件 | 作用 |
|---|---|
| `interview_server.py` | **主程序（v2.2）**：内嵌 HTML + 单端口 8824 同源托管，含全部功能 |
| `interview_history.json` | 面试历史数据（自动生成，可删除重置） |
| `interview_server_v2_backup.py` | 回滚前的干净 v2 备份 |
| `interview_history_v3demo_backup.json` | 早期 demo 历史数据备份 |
| `面试记录_*.md` / `痛点分析报告.md` | 过程记录与痛点分析（迭代依据） |

## 五、白条根因与解法（踩坑记录）

- **根因**：预览面板内置 webview 的密码管理器，在 localhost 源上保存凭据后，对所有 localhost 页面弹自动填充白条；与页面是否含表单元素无关（已验证 contenteditable 纯 div 照样弹）。
- **解法（铁律）**：HTML 内嵌进 Python、单端口 8824 同源、前端 fetch 走相对路径；演示时在自己本机浏览器开 localhost:8824。
- **不要**在工具预览面板里打开 localhost 链接来看效果，那里必弹白条。
