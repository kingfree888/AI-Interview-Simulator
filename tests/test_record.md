# 测试记录

## 一、测试环境

| 项 | 值 |
|---|---|
| OS | Windows 11 (win32) |
| Python | 3.13.12 |
| 大模型 | DeepSeek `deepseek-chat` |
| 服务 | `interview_server.py`，单端口 8824，`ThreadingHTTPServer` |
| 依赖 | 零第三方依赖（仅 Python 标准库） |
| 测试时间 | 2026-07-11 |

## 二、测试数据

来源：`data/test_resumes.json`，含 5 份简历样本 + 期望输出格式 + 5 个测试用例（TC1–TC5）：

- A：产品经理（2 年，数据驱动）
- B：后端工程师（3 年，高并发）
- C：跨行转产品（营销背景）
- D：零实习应届生
- E：空简历（< 80 字，走零经验策略分支）

## 三、测试步骤

```bash
# 1. 启动服务（按 references/config.md 配置 DeepSeek Key）
python skill/scripts/interview_server.py

# 2. 另开终端运行测试脚本（自动清空历史后跑全链路，输出见 test_log.txt）
python tests/submit_test.py
```

原始输出日志：`tests/test_log.txt`

## 四、执行结果

| 用例 | 输入 | 验证点 | 结果 |
|---|---|---|---|
| TC1 | 简历A / 业务面 / 3轮+结束 | 开场无[打分]；每轮含[打分]+弱点；end 生成总评 | ✅ 开场="请先做简短自我介绍，并说说你为什么想做产品经理？"（无打分）；answer1-3 打分 5/3/1；弱点正确解析；总评 285 字 |
| TC2 | 简历B / 压力面 / 2轮 | 压力面打分偏低、弱点解析 | ✅ 打分 5/3，弱点（数据分析/抗压能力等） |
| TC3 | 简历C / HR面 / diagnose+start | 非空分支诊断；HR 开场无[评价] | ✅ 诊断走非空弱点分支；HR 开场="请先做简短自我介绍，并说说你为什么想做产品经理？"（无[评价]，v2.2 修复后复测通过） |
| TC4 | 简历E / 空简历<80字 / diagnose | 走零经验策略分支 | ✅ diagnose 输出以"高频问题+回答方向"开头，符合空简历策略逻辑 |
| TC5 | history 汇总 | total / top_weak / score_trend | ✅ total=1，top_weak 4 项各 100%，score_trend=[3.0] |

## 五、关键验证结论

1. **开场纯净**：所有面试类型开场第一问均为纯问题。修复前 HR 面曾误带 `[评价]`，已在 v2.2 用强化提示词（"开场必须只输出以问号结尾的问题、禁止任何方括号标记"）修复并复测通过。
2. **简历诊断分层正确**：非空简历走"弱点诊断"，< 80 字走"零经验应对策略"。
3. **弱点标签归一化**：返回标签落在 10 个标准维度（数据分析/逻辑结构化/用户洞察/量化成果/项目深度/沟通表达/商业思维/抗压能力/自我认知/方法论）内，可聚合。
4. **历史闭环可用**：面试结束自动写 `interview_history.json`，汇总接口返回 `total` / `top_weak` / `score_trend`。
5. **并发不卡死**：`ThreadingHTTPServer` 保证一次 LLM 长调用期间，页面其它请求不阻塞（详见 `iteration/iteration_log.md` 迭代 3）。

## 六、备注

- 原始日志：`tests/test_log.txt`（与本文档同目录）
- 测试会向 `interview_history.json` 写入数据，如需干净起点可删除该文件（服务会自动重建为空）。
