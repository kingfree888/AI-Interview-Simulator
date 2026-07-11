import json, urllib.request, re, time

BASE = "http://localhost:8824"

def post(p, d):
    req = urllib.request.Request(BASE + p, data=json.dumps(d).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def get(p):
    with urllib.request.urlopen(BASE + p, timeout=20) as r:
        return json.loads(r.read().decode())

def score_of(msg):
    m = re.search(r"\[打分\]\s*(\d+)/10", msg)
    return m.group(1) if m else "?"

# ---- TC1: 简历A 业务面 3轮 + 结束 ----
print("=" * 60)
print("TC1  简历A(产品经理) / 业务面 / 3轮 + 结束")
A = "某电商互联网公司 产品经理（2年经验）。主导首页信息流推荐改版项目，负责需求分析、PRD撰写、跨研发/设计/运营推进落地。独立设计一次推荐策略A/B实验：对20%用户调整内容曝光频次，点击率提升12%、GMV提升3%。日常用SQL自助取数，每周输出数据周报。带过1名实习生完成竞品分析。熟悉Axure/Figma，擅长用户调研与需求优先级排序（RICE模型），对增长和留存有实操经验。"
d = post("/diagnose", {"position": "产品经理", "resume": A})
print("  [diagnose] 非空分支? 含'弱点'或'策略':", ("弱点" in d["diagnosis"] or "策略" in d["diagnosis"]), "| 首句:", d["diagnosis"][:40].replace("\n", " "))
s = post("/start", {"position": "产品经理", "resume": A, "type": "biz"})
print("  [start] 开场含[打分]? (应False):", "[打分]" in s["message"], "| 首问:", s["message"][:70].replace("\n", " "))
sid = s["session_id"]
for i in range(3):
    a = post("/action", {"session_id": sid, "action": "answer",
        "answer": "我先做用户分层，用RICE模型排优先级。A/B实验选20%用户做对照，看曝光频次调整后的点击率和GMV，跑一周确认显著才全量。"})
    print(f"  [answer{i+1}] round={a['round']} 打分={score_of(a['message'])} 弱点={a['weaknesses']}")
e = post("/action", {"session_id": sid, "action": "end"})
print("  [end] finished:", e["finished"], "| 总评长度:", len(e["message"]))

# ---- TC2: 简历B 压力面 2轮 ----
print("=" * 60)
print("TC2  简历B(后端) / 压力面 / 2轮")
B = "后端工程师，3年经验。主导过电商订单系统高并发改造，用Redis做缓存、MySQL分库分表扛住大促峰值（峰值QPS 8万）。做过一次接口耗时优化，P99从800ms降到200ms。熟悉微服务（Spring Cloud）、消息队列（Kafka）。带过2人小组。"
s2 = post("/start", {"position": "后端工程师", "resume": B, "type": "stress"})
for i in range(2):
    a = post("/action", {"session_id": s2["session_id"], "action": "answer",
        "answer": "QPS 8万是用Redis缓存+分库分表扛的，压测用JMeter。P99优化靠异步化和连接池调优。"})
    print(f"  [answer{i+1}] 打分={score_of(a['message'])} 弱点={a['weaknesses']}")

# ---- TC3: 简历C 转行 HR面 diagnose ----
print("=" * 60)
print("TC3  简历C(转行) / HR面 / diagnose+start")
C = "5年互联网运营经验，做过学习打卡活动（付费转化率5%）、用户分层运营（按流失天数分群做差异化push，7日留存提升2个点）。做过一次竞品分析推动产品改版（客诉中30%归为界面问题，提给产品团队）。现在想转产品经理，正在自学Axure和SQL。"
d3 = post("/diagnose", {"position": "产品经理", "resume": C})
print("  [diagnose C] 非空分支首句:", d3["diagnosis"][:50].replace("\n", " "))
s3 = post("/start", {"position": "产品经理", "resume": C, "type": "hr"})
print("  [start C] HR面首问:", s3["message"][:60].replace("\n", " "))

# ---- TC4: 简历E 空简历(<80字) diagnose 走策略分支 ----
print("=" * 60)
print("TC4  简历E(空简历<80字) / diagnose 策略分支")
E = "应届生，想做产品经理，暂无实习经历。"
d4 = post("/diagnose", {"position": "产品经理", "resume": E})
print("  [diagnose E] 走零经验策略分支? 含'零经验'或'策略':", ("零经验" in d4["diagnosis"] or "策略" in d4["diagnosis"]))
print("  [diagnose E] 首句:", d4["diagnosis"][:60].replace("\n", " "))

# ---- TC5: history 汇总 ----
print("=" * 60)
print("TC5  历史汇总")
h = get("/history")
print("  total:", h["summary"]["total"])
print("  top_weak:", [(w["tag"], w["count"], w["pct"]) for w in h["summary"]["top_weak"]])
print("  score_trend:", h["summary"]["score_trend"])
print("\n=== 全部测试用例执行完毕 ===")
