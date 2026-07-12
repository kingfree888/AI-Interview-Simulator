import json, urllib.request, time

BASE = "http://localhost:8824"

def post(p, d):
    req = urllib.request.Request(BASE + p, data=json.dumps(d).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())

def gethist():
    with urllib.request.urlopen(BASE + "/history", timeout=20) as r:
        return json.loads(r.read().decode())

# 江奕恒 真实简历（去掉联系方式）
RESUME = """姓名江奕恒，男，23岁，求职意向初级产品经理（工具产品/生活服务ToC）。
XX工业大学 软件工程（互联网产品方向）本科 2020.09-2024.06，GPA 3.45/4.0，专业前22%。
实习1：XX智慧生活科技 产品经理实习生 2023.07-2023.12，本地生活便民工具类APP（千万级用户）。
负责工具模块迭代：对标美团/支付宝做6份竞品分析，收集70+有效需求筛选30条高价值；独立负责便民工具聚合页、权益卡券核销两大模块，输出PRD并参与需求评审、技术答疑、灰度上线全流程；
搭建数据监测体系，迭代后工具模块点击率提升25%、卡券核销转化率提升16%、用户负面反馈下降20%；输出4份迭代复盘报告。
实习2：XX数字科技 产品助理 2022.11-2023.06，整理用户反馈2000+条，协助10+轻量功能优化。
项目：校园一站式便民小程序「校园优享」产品负责人 2022.04-2022.11，4人团队，注册2800+，90天留存41%，功能使用率82%。
技能：Axure/墨刀、Excel数据透视、ToC工具类产品全生命周期。"""

# 三种面试类型的真实感回答（贴合简历内容）
ANSWERS = {
    "biz": [
        "关于核销转化率提升16%，这是我实习中独立推动的。当时发现核销步骤繁琐、权益展示不清晰，我把原来5步的核销路径缩减到2步，新增智能弹窗提醒。我主导了业务流程图、交互原型的输出，跟UI和开发对齐后灰度上线，数据显著才全量。",
        "增长主要来自路径简化和弹窗提醒。我用漏斗拆解出流失最大的是'查看权益'到'发起核销'之间，于是把核销入口前置、权益信息卡片化。同时用户负面反馈下降20%，说明是真实体验改善而非短期刺激。",
        "如果重来，我会更早建立干净的对照组。当时灰度是按城市分批不是严格随机，归因不够严谨。后续我想引入更标准的A/B实验设计，用SQL拉更长周期数据验证效果。",
    ],
    "hr": [
        "我选产品经理是因为实习做便民工具迭代时，发现用产品手段能真实改善千万用户的生活效率，这种落地感很吸引我。规划是先扎实做好功能模块迭代，3年内能独立负责一条产品线。",
        "我的优势是落地能力强、复盘意识突出，两段实习都独立负责过模块上线。劣势是商业深度还不够，对营收模型理解偏浅，正在看行业案例补。",
        "跨团队推进遇到阻力时，我会先对齐目标再小步快跑。比如核销模块排期紧，我跟技术leader提前同步优先级，用最小可用版本先上再补，保证节点不拖。",
    ],
    "stress": [
        "你说功劳是我的？核销模块是跨团队做的，我是实习生，真正写代码的是开发。我的核心贡献是定位了体验痛点、设计了简化方案、输出PRD并推动灰度上线——决策判断是我做的，落地靠团队。",
        "16%确定吗？数据是真实埋点统计的，但灰度按城市批次不是随机对照，严格说不能完全排除季节因素。我承认归因有局限，这也是复盘报告里写明的。",
        "我抗压还行。实习时同时跟两个模块上线，我靠台账和优先级排序扛住了，没让节点延误。压力大的时候我会把问题拆细、每天对齐进度。",
    ],
}

print("=" * 60)
print("用 江奕恒 真实简历 跑三种面试类型，生成真实历史数据")
print("=" * 60)

for itype, label in [("biz", "业务面"), ("hr", "HR面"), ("stress", "压力面")]:
    print(f"\n########## {label} ##########")
    s = post("/start", {"position": "初级产品经理", "resume": RESUME, "type": itype})
    print(f"开场第一问（应无打分）: {s['message'][:90].replace(chr(10),' ')}")
    print(f"  含[打分]? {('[打分]' in s['message'])}")
    for i, ans in enumerate(ANSWERS[itype]):
        a = post("/action", {"session_id": s["session_id"], "action": "answer", "answer": ans})
        if a.get("finished"):
            print(f"  [自动结束] {a['message'][:60]}")
            break
        print(f"  回答{i+1} → [打分]有? {('[打分]' in a['message'])} | 弱点: {a['weaknesses']} | 轮次:{a['round']}")
    e = post("/action", {"session_id": s["session_id"], "action": "end"})
    print(f"  总评生成: 长度{len(e['message'])} | finished:{e['finished']}")
    time.sleep(0.5)

print("\n" + "=" * 60)
print("历史面板汇总")
print("=" * 60)
h = gethist()
sm = h["summary"]
print(f"总场次: {sm['total']}")
print(f"高频薄弱点 Top6:")
for w in sm["top_weak"]:
    print(f"  {w['tag']:<8} 次数{w['count']:<3} 占比{w['pct']}%")
print(f"得分趋势: {sm['score_trend']}")
print(f"历史记录数: {len(h['interviews'])}")
for it in h["interviews"]:
    print(f"  - {it['type']} | 平均分{it['avg_score']} | 轮次{it['rounds']} | 弱点{it['weaknesses']}")
print("\n✅ 真实数据已写入 interview_history.json")
