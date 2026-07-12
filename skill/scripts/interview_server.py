#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI面试模拟官 v2.2 — 内嵌页面 + 单端口同源托管（无白条架构）+ 迭代2历史追踪 + 多线程防卡死

架构铁律（今天踩坑后定下，根治白条）：
  - HTML 内嵌进本文件，单端口 8824 同源托管
  - 前端 fetch 走相对路径（/diagnose /start /action /history），零跨域
  - 白条根因 = preview 面板内置浏览器在 localhost 存凭据后弹自动填充，与页面代码无关
  - 演示时在自己本机 Chrome/Edge 地址栏开 localhost:8824（或无痕），即干净
"""
import json, urllib.request, http.server, re, os, time, threading

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 也可直接填 "sk-你的key"；推荐用环境变量避免泄露
API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"
PORT = 8824
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interview_history.json")

conversations = {}

history_lock = threading.Lock()

TYPE_PROMPTS = {
    "hr": {"label": "HR面", "desc": "综合素质、沟通、职业规划",
        "style": "你是HR面试官，面试「{position}」。简历：{resume}\n风格：温和，考察软素质（沟通/协作/抗压/价值观），适度追问。\n【流程铁律】\n①开场第一轮：必须只输出一个具体的面试问题（以问号结尾），绝对禁止评价简历、禁止出现[评价][打分][建议][弱点][下一题]任何方括号标记。示例开场：'请先做简短自我介绍，并说说你为什么想做{position}？'（开场写出任何方括号标记即严重违规）\n②之后每一轮：先针对用户【刚才的回答】给出评价与打分，再提出下一个问题。\n③每轮只问一题。\n【输出格式（仅第②类轮次使用，必须用方括号标记，绝不可用加粗文字代替）】\n[评价]对你的回答的简评\n[打分]X/10\n[建议]改进建议\n[弱点]标签1,标签2\n[下一题]下一个问题\n（[弱点]标签从以下选1-2个：数据分析/逻辑结构化/用户洞察/量化成果/项目深度/沟通表达/商业思维/抗压能力/自我认知/方法论）"},
    "biz": {"label": "业务面", "desc": "深挖项目、产品思维、数据分析",
        "style": "你是业务负责人，面试「{position}」。简历：{resume}\n风格：深挖项目细节，追问到答不上来，打分严格。\n【流程铁律】\n①开场第一轮：必须只输出一个具体的面试问题（以问号结尾），绝对禁止评价简历、禁止出现[评价][打分][建议][弱点][下一题]任何方括号标记。示例开场：'请先做简短自我介绍，并说说你为什么想做{position}？'（开场写出任何方括号标记即严重违规）\n②之后每一轮：先针对用户【刚才的回答】给出评价与打分，再提出下一个问题。\n③每轮只问一题。\n【输出格式（仅第②类轮次使用，必须用方括号标记，绝不可用加粗文字代替）】\n[评价]对你的回答的简评\n[打分]X/10\n[建议]改进建议\n[弱点]标签1,标签2\n[下一题]下一个问题\n（[弱点]标签从以下选1-2个：数据分析/逻辑结构化/用户洞察/量化成果/项目深度/沟通表达/商业思维/抗压能力/自我认知/方法论）"},
    "boss": {"label": "总监面", "desc": "战略思维、商业sense",
        "style": "你是VP/总监，面试「{position}」。简历：{resume}\n风格：不关心执行细节，考察商业思维和判断力，追问对业务的意义。\n【流程铁律】\n①开场第一轮：必须只输出一个具体的面试问题（以问号结尾），绝对禁止评价简历、禁止出现[评价][打分][建议][弱点][下一题]任何方括号标记。示例开场：'请先做简短自我介绍，并说说你为什么想做{position}？'（开场写出任何方括号标记即严重违规）\n②之后每一轮：先针对用户【刚才的回答】给出评价与打分，再提出下一个问题。\n③每轮只问一题。\n【输出格式（仅第②类轮次使用，必须用方括号标记，绝不可用加粗文字代替）】\n[评价]对你的回答的简评\n[打分]X/10\n[建议]改进建议\n[弱点]标签1,标签2\n[下一题]下一个问题\n（[弱点]标签从以下选1-2个：数据分析/逻辑结构化/用户洞察/量化成果/项目深度/沟通表达/商业思维/抗压能力/自我认知/方法论）"},
    "stress": {"label": "压力面", "desc": "高压追问、质疑施压",
        "style": "你进行压力面试「{position}」。简历：{resume}\n风格：持续质疑（数据确定吗/功劳是你的吗），故意冷淡，打3-7分，看压力下逻辑是否自洽。\n【流程铁律】\n①开场第一轮：必须只输出一个具体的压力问题（以问号结尾），绝对禁止评价简历、禁止出现[评价][打分][建议][弱点][下一题]任何方括号标记（开场写出任何方括号标记即严重违规）\n②之后每一轮：先针对用户【刚才的回答】给出评价与打分，再提出下一个问题。\n③每轮只问一题。\n【输出格式（仅第②类轮次使用，必须用方括号标记，绝不可用加粗文字代替）】\n[评价]对你的回答的简评\n[打分]X/10\n[建议]改进建议\n[弱点]标签1,标签2\n[下一题]下一个问题\n（[弱点]标签从以下选1-2个：数据分析/逻辑结构化/用户洞察/量化成果/项目深度/沟通表达/商业思维/抗压能力/自我认知/方法论）"},
}

# 弱点标准词表：AI 输出的弱点标签归一化到这 10 个维度
KNOWN_WEAK = {
    "数据分析": ["数据", "data", "量化", "指标", "统计"],
    "逻辑结构化": ["逻辑", "结构", "条理", "框架", "拆解"],
    "用户洞察": ["用户", "洞察", "需求", "体验", "同理"],
    "量化成果": ["成果", "结果", "业绩", "产出", "价值", "数据驱动"],
    "项目深度": ["项目", "深度", "细节", "落地", "执行"],
    "沟通表达": ["沟通", "表达", "清晰", "语言", "讲清楚"],
    "商业思维": ["商业", "业务", "战略", "sense", "决策"],
    "抗压能力": ["压力", "抗压", "情绪", "稳定", "心态"],
    "自我认知": ["自我", "认知", "不足", "反思", "复盘"],
    "方法论": ["方法", "方法论", "体系", "流程", "闭环"],
}


def normalize_weak(raw):
    r = raw.strip().lower()
    for label, aliases in KNOWN_WEAK.items():
        if label.lower() == r:
            return label
        for a in aliases:
            if a.lower() in r:
                return label
    return raw.strip()


def call_deepseek(messages):
    if not API_KEY:
        raise RuntimeError("未配置 API Key：请设置环境变量 DEEPSEEK_API_KEY，或把代码里的 API_KEY 直接填成你的 sk- 开头密钥")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    payload = {"model": MODEL, "messages": messages, "temperature": 0.6}
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"模型调用失败：{e}")


def parse_reply(reply):
    """解析 [打分] 和 [弱点]。返回 (分数, 展示文本, 弱点列表)。[弱点] 段从展示文本剥离。"""
    score = None
    m = re.search(r"\[打分\]\s*(\d+(?:\.\d+)?)\s*/\s*(10|100)", reply)
    if m:
        num = float(m.group(1))
        den = int(m.group(2))
        score = round(num / den * 10, 1) if den == 100 else round(num, 1)
    weak = []
    wm = re.search(r"\[弱点\]\s*([^\n\[]*)", reply)
    if wm:
        for part in re.split(r"[,，/、]", wm.group(1)):
            part = part.strip()
            if part:
                weak.append(normalize_weak(part))
    disp = re.sub(r"\[弱点\][^\n\[]*", "", reply)
    return score, disp, weak


def parse_dimensions(reply):
    """解析 [维度] 标记，返回 (维度字典, 干净文本)。JSON 优先（含换行），缺省补 5 分。"""
    default_keys = ["逻辑结构", "表达沟通", "业务深度", "方法论", "应变能力"]
    dims = {k: 5 for k in default_keys}
    idx = reply.find("[维度]")
    if idx < 0:
        return dims, reply.strip()

    rest = reply[idx + len("[维度]"):]
    start = rest.find("{")
    if start >= 0:
        # 括号平衡匹配多行 JSON
        depth, end = 0, -1
        for i in range(start, len(rest)):
            if rest[i] == "{": depth += 1
            elif rest[i] == "}":
                depth -= 1
                if depth == 0: end = i + 1; break
        if end > start:
            try:
                parsed = json.loads(rest[start:end])
                for k in default_keys:
                    if k in parsed:
                        try: dims[k] = min(max(int(float(parsed[k])), 1), 10)
                        except (ValueError, TypeError): pass
                # 去掉 [维度] 及整段 JSON（含 [维度] 到 JSON 前的字符）
                cut_end = idx + len("[维度]") + end
                clean = reply[:idx] + reply[cut_end:]
                return dims, clean.strip()
            except json.JSONDecodeError: pass
    # 回退：取第一行按逗号分隔
    line = rest.split("\n")[0]
    for part in re.split(r"[,，]", line):
        kv = part.split(":", 1)
        if len(kv) == 2:
            key = kv[0].strip().strip('"')
            if key in dims:
                try: dims[key] = min(max(int(float(kv[1].strip())), 1), 10)
                except (ValueError, TypeError): pass
    clean = reply[:idx] + reply[idx + len("[维度]") + len(line):]
    return dims, clean.strip()

# ---------- 历史追踪（迭代2）----------
def load_history():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "interviews" in data:
            return data
    except Exception:
        pass
    return {"interviews": []}


def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def finish_record(sid):
    conv = conversations.get(sid)
    if not conv:
        return
    scores = conv.get("scores", [])
    avg = round(sum(scores) / len(scores), 1) if scores else None
    seen = []
    for w in conv.get("weaknesses", []):
        if w not in seen:
            seen.append(w)
    rec = {
        "position": conv["position"], "type": conv["type"],
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "rounds": conv["round"], "avg_score": avg,
        "weaknesses": seen, "summary": conv.get("summary", ""),
        "dimensions": conv.get("dimensions", {}),
    }
    hist = load_history()
    with history_lock:
        hist = load_history()
        hist["interviews"].append(rec)
        save_history(hist)


def get_weakness_summary(hist):
    interviews = hist.get("interviews", [])
    counter = {}
    for iv in interviews:
        for w in set(iv.get("weaknesses", [])):
            counter[w] = counter.get(w, 0) + 1
    total = len(interviews) or 1
    ranked = sorted(counter.items(), key=lambda x: -x[1])[:6]
    top = [{"tag": t, "count": c, "pct": round(c / total * 100)} for t, c in ranked]
    scores = [iv.get("avg_score") for iv in interviews if iv.get("avg_score") is not None]
    return {"total": len(interviews), "top_weak": top, "score_trend": scores[-10:]}


def get_html():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI面试模拟官</title>
<style>
:root{
  --bg:#f4f5fb; --bg2:#eef0f8;
  --card:#ffffff; --card2:#fbfbfe;
  --text:#1d2130; --sub:#727a8e; --border:#e8eaf2;
  --accent:#6366f1; --accent2:#8b5cf6; --accent-soft:#eef0ff;
  --grad:linear-gradient(135deg,#6366f1 0%,#8b5cf6 100%);
  --ai-bg:#f4f2ff; --ai-border:#e6e1ff;
  --user-bg:#ffffff;
  --good:#16a34a; --warn:#f59e0b; --bad:#ef4444; --blue:#6366f1;
  --radius:18px; --shadow:0 18px 40px -20px rgba(50,46,120,.28);
}
[data-theme="dark"]{
  --bg:#0d0f16; --bg2:#11141d;
  --card:#161a24; --card2:#1b202d;
  --text:#e9ebf5; --sub:#949db3; --border:#262c3a;
  --accent:#818cf8; --accent2:#a78bfa; --accent-soft:#1e2236;
  --ai-bg:#1a1f33; --ai-border:#2d3354;
  --user-bg:#1e2230;
  --good:#22c55e; --warn:#fbbf24; --bad:#f87171; --blue:#818cf8;
  --shadow:0 20px 44px -18px rgba(0,0,0,.7);
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Roboto,sans-serif;
  background:radial-gradient(1200px 600px at 50% -10%,var(--bg2),var(--bg));
  background-attachment:fixed;color:var(--text);line-height:1.65;min-height:100vh;
  -webkit-font-smoothing:antialiased;
}
.container{max-width:820px;margin:0 auto;padding:22px 18px 60px}
.topbar{display:flex;justify-content:flex-end;gap:10px;align-items:center;margin-bottom:6px}
.icon-btn{width:38px;height:38px;border-radius:11px;border:1px solid var(--border);background:var(--card);color:var(--text);cursor:pointer;font-size:16px;display:inline-flex;align-items:center;justify-content:center;transition:.2s}
.icon-btn:hover{border-color:var(--accent);transform:translateY(-1px)}
.hero{text-align:center;padding:26px 0 20px}
.hero-badge{display:inline-block;padding:5px 14px;border-radius:999px;background:var(--accent-soft);color:var(--accent);font-size:12px;font-weight:600;letter-spacing:.5px;margin-bottom:14px}
.hero h1{font-size:32px;font-weight:800;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;letter-spacing:.5px}
.hero p{color:var(--sub);margin-top:10px;font-size:14px}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:26px;margin-bottom:18px;box-shadow:var(--shadow)}
label{display:block;font-size:13px;font-weight:600;margin-bottom:8px;color:var(--text)}
input,textarea,select{width:100%;padding:12px 14px;border:1px solid var(--border);border-radius:12px;font-size:14px;font-family:inherit;outline:none;background:var(--card2);color:var(--text);transition:.18s}
input::placeholder,textarea::placeholder{color:var(--sub);opacity:.8}
input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft);background:var(--card)}
textarea{resize:vertical;min-height:130px}
.inline-row{display:flex;gap:14px;align-items:flex-end}.inline-row>div{flex:1}
.gap{height:16px}
.resume-row{display:flex;gap:8px;align-items:flex-start}.resume-row textarea{flex:1}
.upload-col{display:flex;flex-direction:column;align-items:center;gap:2px}
.start-row{margin-top:18px;display:flex;justify-content:flex-end}
.row-end{margin-top:18px;display:flex;gap:10px;justify-content:flex-end;align-items:center}
.card-head{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.card-head .dot{width:9px;height:9px;border-radius:50%;background:var(--grad);box-shadow:0 0 0 4px var(--accent-soft)}
.card-head h3{font-size:17px;font-weight:700}
.diag{font-size:14px;line-height:1.85;color:var(--text)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;padding:11px 22px;border-radius:12px;font-size:14px;font-weight:600;cursor:pointer;border:1px solid transparent;transition:.2s;font-family:inherit}
.btn-primary{background:var(--grad);color:#fff;box-shadow:0 10px 24px -10px rgba(99,102,241,.7)}
.btn-primary:hover{filter:brightness(1.06);transform:translateY(-1px)}
.btn-primary:disabled{opacity:.55;cursor:not-allowed;transform:none}
.btn-outline{background:var(--card);border:1px solid var(--border);color:var(--text)}
.btn-outline:hover{border-color:var(--accent);color:var(--accent)}
.btn-ghost{background:var(--card2);border:1px solid var(--border);color:var(--text)}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent);transform:translateY(-1px)}
.btn-danger{color:var(--bad)}.btn-danger:hover{border-color:var(--bad);color:var(--bad)}
.btn-sm{padding:8px 14px;font-size:13px}
.iv-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;gap:10px;flex-wrap:wrap}
.iv-tags{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.round-info{font-size:12.5px;color:var(--sub);font-weight:600;white-space:nowrap}
.badge{display:inline-block;padding:4px 11px;border-radius:999px;font-size:12px;font-weight:600}
.badge-b{background:var(--accent-soft);color:var(--accent)}
.badge-focus{background:linear-gradient(135deg,#fef3c7,#fde68a);color:#92400e;box-shadow:0 0 0 3px rgba(251,191,36,.18);animation:pulse 2.2s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 3px rgba(251,191,36,.18)}50%{box-shadow:0 0 0 6px rgba(251,191,36,.05)}}
.progress{height:6px;background:var(--bg2);border-radius:999px;overflow:hidden;margin-bottom:16px}
.progress-fill{height:100%;width:10%;background:var(--grad);border-radius:999px;transition:width .4s ease}
.chat-area{max-height:56vh;overflow-y:auto;padding:6px 2px 4px}
.msg{display:flex;gap:12px;margin-bottom:20px;animation:rise .35s ease both}
.msg-user{flex-direction:row-reverse}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.avatar{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.avatar.ai{background:var(--grad);color:#fff;box-shadow:0 6px 16px -6px rgba(99,102,241,.6)}
.avatar.me{background:var(--card2);border:1px solid var(--border);color:var(--sub);font-size:13px;font-weight:600}
.msg-body{max-width:80%}
.bubble{background:var(--ai-bg);border:1px solid var(--ai-border);border-radius:16px;border-top-left-radius:5px;padding:14px 17px;font-size:14px;line-height:1.8;white-space:pre-wrap;word-break:break-word}
.msg-user .bubble{background:var(--user-bg);border:1px solid var(--border);border-top-right-radius:5px}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.tag{display:inline-block;padding:3px 10px;border-radius:8px;font-size:12px;font-weight:600}
.tag-good{background:#dcfce7;color:var(--good)}
.tag-warn{background:#fef3c7;color:#b45309}
.tag-blue{background:var(--accent-soft);color:var(--accent)}
.tag-bad{background:#fee2e2;color:var(--bad)}
.input-row{display:flex;gap:12px;margin-top:8px;align-items:flex-end}
.input-row textarea{flex:1;min-height:64px;padding:12px}
.action-bar{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap;justify-content:center}
.spinner{display:inline-block;width:15px;height:15px;border:2px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .6s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.hidden{display:none!important}
.modal{position:fixed;inset:0;background:rgba(15,20,35,.5);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:100;padding:16px}
.modal-box{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:26px;max-width:680px;width:100%;max-height:86vh;overflow:auto;box-shadow:var(--shadow);animation:rise .3s ease both}
.modal-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.modal-box h3{font-size:18px;font-weight:700}
.modal-box h4{font-size:14px;font-weight:700;margin:18px 0 10px;color:var(--text)}
.weak-bar{height:7px;background:var(--bg2);border-radius:999px;margin-top:5px;overflow:hidden}
.weak-bar>div{height:100%;background:linear-gradient(90deg,var(--bad),#fb923c);border-radius:999px}
.hist-card{border:1px solid var(--border);border-radius:14px;padding:14px;margin-bottom:12px;background:var(--card2)}
.score-pill{color:#fff;padding:4px 11px;border-radius:9px;font-size:13px;font-weight:700}
.warn-box{margin-top:16px;padding:14px 16px;background:linear-gradient(135deg,#fffbeb,#fef3c7);border:1px solid #fde68a;border-radius:14px;font-size:13.5px;color:#92400e;line-height:1.8}
@media(max-width:560px){.inline-row{flex-direction:column;gap:14px}.hero h1{font-size:26px}.msg-body{max-width:86%}}
</style>
</head>
<body data-theme="light">
<div class="container">
<div class="topbar">
  <button class="icon-btn" id="theme-toggle" onclick="toggleTheme()" title="切换深浅色">🌙</button>
  <button class="btn btn-outline btn-sm" onclick="showHistory()">📊 历史</button>
</div>

<header class="hero">
  <div class="hero-badge">AI · 面试教练</div>
  <h1>AI 面试模拟官</h1>
  <p>多类型面试官 · 简历诊断 · 弱点追踪 · 针对性加练</p>
</header>

<div id="setup-card" class="card">
  <div class="inline-row">
    <div><label>目标岗位</label><input id="position" autocomplete="off" placeholder="如：产品经理 / 后端工程师 ..."></div>
    <div><label>面试类型</label><select id="interviewType"><option value="biz">业务面 · 深挖项目</option><option value="hr">HR面 · 软素质</option><option value="boss">总监面 · 战略思维</option><option value="stress">压力面 · 高压追问</option></select></div>
  </div>
  <div class="gap"></div>
  <label>简历</label>
  <div class="resume-row">
    <textarea id="resume" autocomplete="off" placeholder="粘贴简历，或点击右侧按钮上传 .txt / .md 文件…"></textarea>
    <div class="upload-col">
      <input type="file" id="resume-file" accept=".txt,.md" onchange="uploadResume()" style="display:none">
      <button class="btn btn-outline btn-sm" onclick="document.getElementById('resume-file').click()" title="上传简历文件">📁</button>
      <span id="resume-file-name" style="font-size:10px;color:var(--sub);margin-top:3px;display:none;word-break:break-all"></span>
    </div>
  </div>
  <div class="start-row"><button id="start-btn" class="btn btn-primary" onclick="startFlow()">诊断简历，开始面试 →</button></div>
</div>

<div id="diagnosis-card" class="card hidden">
  <div class="card-head"><span class="dot"></span><h3>简历分析</h3></div>
  <div id="diag-content" class="diag"></div>
  <div class="row-end">
    <button class="btn btn-primary" onclick="confirmStart()">开始面试</button>
    <button class="btn btn-outline btn-sm" onclick="backToSetup()">返回修改</button>
  </div>
</div>

<div id="interview-card" class="card hidden">
  <div class="iv-top">
    <div class="iv-tags">
      <span id="type-badge" class="badge badge-b">业务面</span>
      <span id="focus-badge" class="badge badge-focus" style="display:none"></span>
    </div>
    <span id="round-info" class="round-info">第 1 轮</span>
  </div>
  <div class="progress"><div class="progress-fill" id="round-progress-fill"></div></div>
  <div class="chat-area" id="chat"></div>
  <div id="input-area">
    <div class="input-row">
      <textarea id="answer" autocomplete="off" placeholder="输入你的回答…（Ctrl+Enter 发送）" onkeydown="if(event.ctrlKey&&event.key==='Enter')doAction('answer')"></textarea>
      <button id="send-btn" class="btn btn-primary" onclick="doAction('answer')">📤 发送</button>
    </div>
    <div class="action-bar">
      <button class="btn btn-ghost btn-sm" onclick="doAction('deep')">🔍 深挖追问</button>
      <button class="btn btn-ghost btn-sm" onclick="doAction('switch')">🔃 换方向</button>
      <button class="btn btn-ghost btn-sm" onclick="doAction('skip')">⏭ 跳过</button>
      <button class="btn btn-ghost btn-sm btn-danger" onclick="doAction('end')">⏹ 结束</button>
    </div>
  </div>
</div>

<div id="summary-card" class="card hidden"></div>
</div>

<div id="history-modal" class="modal hidden" onclick="if(event.target===this)hideHistory()">
<div class="modal-box">
<div class="modal-head">
  <h3>面试历史</h3><button class="icon-btn" onclick="event.stopPropagation();hideHistory()">✕</button>
</div>
<div id="history-content"></div>
</div>
</div>

<script>
var sessionId=null,isWaiting=0,typeLabel='';
function $(id){return document.getElementById(id)}
function typeName(t){return {biz:'业务面',hr:'HR面',boss:'总监面',stress:'压力面'}[t]||t}
function addMsg(role,text,weakArr){
var d=document.createElement('div');d.className='msg msg-'+role;
var t=text.replace(/\\n/g,'<br>');
t=t.replace(/\\[评价\\]/g,'<span class="tag tag-good">评价</span> ');
t=t.replace(/\\[打分\\]\\s*(\\d+(?:\\.\\d+)?)\\/10/g,'<span class="tag tag-warn">$1/10</span>');
t=t.replace(/\\[建议\\]/g,'<span class="tag tag-blue">建议</span> ');
t=t.replace(/\\[下一题\\]/g,'<span class="tag tag-blue">下一题</span>');
var av=role==='ai'?'<div class="avatar ai">🎯</div>':'<div class="avatar me">你</div>';
var inner='<div class="bubble">'+t+'</div>';
if(weakArr&&weakArr.length){var chips='<div class="chips">';weakArr.forEach(function(w){chips+='<span class="tag tag-bad">'+w+'</span>';});chips+='</div>';inner+=chips;}
d.innerHTML=av+'<div class="msg-body">'+inner+'</div>';
$('chat').appendChild(d);$('chat').scrollTop=$('chat').scrollHeight;
}
function btnSpin(el,loading){
if(loading){el.setAttribute('data-orig',el.innerHTML);el.innerHTML='<span class="spinner"></span> 加载中';el.disabled=true}
else{el.innerHTML=el.getAttribute('data-orig')||el.innerHTML;el.disabled=false}
}
function api(url,data){
return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(function(r){return r.json()});
}
function uploadResume(){
  var f=$('resume-file').files[0];if(!f)return;
  var reader=new FileReader();
  reader.onload=function(e){
    $('resume').value=e.target.result;
    var nm=$('resume-file-name');nm.textContent=f.name;nm.style.display='';
  };
  reader.onerror=function(){
    alert('文件读取失败，请尝试粘贴文本或换 .txt 格式');
  };
  reader.readAsText(f,'UTF-8');
}
async function startFlow(){
var p=$('position').value.trim(),r=$('resume').value.trim();
if(!p||!r){alert('请填写岗位和简历');return;}
var btn=$('start-btn');btnSpin(btn,true);
try{
var d=await api('/diagnose',{position:p,resume:r});
if(d.error){alert('诊断失败：'+d.error);return;}
if(!d.diagnosis){alert('诊断失败：服务端未返回内容，请重试');return;}
$('diag-content').innerHTML=d.diagnosis.replace(/\\n/g,'<br>');
await showWeakWarning();
$('setup-card').classList.add('hidden');
$('diagnosis-card').classList.remove('hidden');
}catch(e){alert('诊断出错：'+e.message)}
btnSpin(btn,false);
}
function backToSetup(){$('diagnosis-card').classList.add('hidden');$('setup-card').classList.remove('hidden')}
async function showWeakWarning(){
try{
var d=await fetch('/history').then(function(r){return r.json()});
if(d.summary&&d.summary.top_weak&&d.summary.top_weak.length){
  var tags=d.summary.top_weak.map(function(w){return w.tag+'('+w.count+'次)'}).join('、');
  var box='<div class="warn-box">📊 你已完成 <b>'+d.summary.total+'</b> 次模拟，历史高频薄弱点：<b>'+tags+'</b><br>本次面试可重点准备这些方向。</div>';
  $('diag-content').insertAdjacentHTML('beforeend',box);
}
}catch(e){}
}
async function confirmStart(){
var p=$('position').value.trim(),r=$('resume').value.trim(),t=$('interviewType').value;
typeLabel=typeName(t);
$('diagnosis-card').classList.add('hidden');
$('interview-card').classList.remove('hidden');
$('type-badge').textContent=typeLabel;
isWaiting=1;showThinking();
try{
var d=await api('/start',{position:p,resume:r,type:t});
removeThinking();
if(d.error){addMsg('ai','[系统] '+d.error);}
else{sessionId=d.session_id;addMsg('ai',d.message,d.weaknesses);$('round-info').textContent='第 1 轮';updateProgress(1);
if(d.focus){$('focus-badge').style.display='';$('focus-badge').textContent='🎯 针对性加练：'+d.focus;}else{$('focus-badge').style.display='none';}}
}catch(e){removeThinking();addMsg('ai','[系统] 出错: '+e.message)}
isWaiting=0;$('answer').focus();
}
async function doAction(action){
if(isWaiting||!sessionId)return;
var ans=$('answer').value.trim();
if(action==='answer'&&!ans){return;}
if(action==='answer'){addMsg('user',ans);$('answer').value='';}
else if(action==='skip'){addMsg('user','[跳过本题]');}
else if(action==='deep'){addMsg('user','[要求深挖追问]');}
else if(action==='switch'){addMsg('user','[要求换方向]');}
isWaiting=1;setWaiting(true);showThinking();
try{
var d=await api('/action',{session_id:sessionId,action:action,answer:ans});
removeThinking();
if(d.error){addMsg('ai','[系统] '+d.error);}
else if(d.finished){addMsg('ai',d.message);showSummary(d.message,d.dimensions);$('input-area').classList.add('hidden')}
else{addMsg('ai',d.message,d.weaknesses);$('round-info').textContent='第 '+d.round+' / 10 轮';updateProgress(d.round);}
}catch(e){removeThinking();addMsg('ai','[系统] 网络出错: '+e.message)}
isWaiting=0;setWaiting(false);if(action!=='end')$('answer').focus();
}
function setWaiting(on){var b=$('send-btn');if(b){b.disabled=on;b.innerHTML=on?'<span class="spinner"></span> 思考中…':'📤 发送'}}
function showThinking(){if($('thinking'))return;var d=document.createElement('div');d.className='msg msg-ai';d.id='thinking';d.innerHTML='<div class="avatar ai">🎯</div><div class="msg-body"><div class="bubble"><span class="spinner"></span> 面试官正在思考…</div></div>';$('chat').appendChild(d);$('chat').scrollTop=$('chat').scrollHeight;}
function removeThinking(){var t=$('thinking');if(t)t.remove();}
function showSummary(text,dims){
var c=$('summary-card');c.classList.remove('hidden');
var radarHTML='';
if(dims&&Object.keys(dims).length){
  radarHTML='<div style="display:flex;justify-content:center;margin-bottom:20px"><canvas id="radar-canvas" width="320" height="300"></canvas></div>';
}
c.innerHTML='<div class="card-head"><span class="dot"></span><h3>面试总评</h3></div>'+radarHTML+'<div style="font-size:14px;white-space:pre-wrap;line-height:1.85">'+text+'</div><div style="margin-top:18px;display:flex;gap:10px"><button class="btn btn-primary" onclick="location.reload()">再来一次</button></div>';
if(dims&&Object.keys(dims).length)drawRadar('radar-canvas',dims);
window._lastDims=dims||{};
}
function drawRadar(canvasId,dims){
var keys=['逻辑结构','表达沟通','业务深度','方法论','应变能力'];
var n=keys.length,cv=document.getElementById(canvasId);if(!cv)return;
var ctx=cv.getContext('2d'),w=cv.width,h=cv.height,cx=w/2,cy=h/2-5,r=110;
var style=getComputedStyle(document.documentElement);
var clBorder=style.getPropertyValue('--border').trim()||'#d1d5db';
var clSub=style.getPropertyValue('--sub').trim()||'#9ca3af';
var clText=style.getPropertyValue('--text').trim()||'#111827';
var clAccent=style.getPropertyValue('--blue').trim()||'#2563eb';
var vals=keys.map(function(k){return dims[k]||0;});
ctx.clearRect(0,0,w,h);
// 背景网格
for(var lv=5;lv<=10;lv+=1){
  var ratio=lv/10;
  ctx.beginPath();
  for(var i=0;i<n;i++){
    var ang=-Math.PI/2+i*2*Math.PI/n;
    var x=cx+Math.cos(ang)*r*ratio,y=cy+Math.sin(ang)*r*ratio;
    if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
  }
  ctx.closePath();
  ctx.strokeStyle=clBorder;ctx.lineWidth=1;ctx.stroke();
  if(lv%2===0){
    ctx.fillStyle=clSub;ctx.font='10px -apple-system,sans-serif';
    ctx.fillText(lv,cx+8,cy-r*ratio+12);
  }
}
// 轴线
var axisLen=r+18;
for(var i=0;i<n;i++){
  var ang=-Math.PI/2+i*2*Math.PI/n;
  ctx.beginPath();ctx.moveTo(cx,cy);
  ctx.lineTo(cx+Math.cos(ang)*r,cy+Math.sin(ang)*r);
  ctx.strokeStyle=clBorder;ctx.lineWidth=1;ctx.stroke();
  var lx=cx+Math.cos(ang)*axisLen,ly=cy+Math.sin(ang)*axisLen;
  ctx.fillStyle=clText;ctx.font='12px -apple-system,sans-serif';
  ctx.textAlign=i===0?'center':(i<2?'left':(i===3?'right':'center'));
  ctx.fillText(keys[i],lx,ly);
}
// 数据填充
ctx.beginPath();
for(var i=0;i<n;i++){
  var ang=-Math.PI/2+i*2*Math.PI/n;
  var ratio2=vals[i]/10;
  var x=cx+Math.cos(ang)*r*ratio2,y=cy+Math.sin(ang)*r*ratio2;
  if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
}
ctx.closePath();
var grd=ctx.createRadialGradient(cx,cy,0,cx,cy,r);
grd.addColorStop(0,clAccent+'40');
grd.addColorStop(1,clAccent+'0D');
ctx.fillStyle=grd;ctx.fill();
ctx.strokeStyle=clAccent;ctx.lineWidth=2;ctx.stroke();
// 得分点
for(var i=0;i<n;i++){
  var ang3=-Math.PI/2+i*2*Math.PI/n;
  var ratio3=vals[i]/10;
  var x=cx+Math.cos(ang3)*r*ratio3,y=cy+Math.sin(ang3)*r*ratio3;
  ctx.beginPath();ctx.arc(x,y,4,0,2*Math.PI);
  ctx.fillStyle=clAccent;ctx.fill();
  ctx.strokeStyle='#fff';ctx.lineWidth=1.5;ctx.stroke();
  ctx.fillStyle=clText;ctx.font='bold 11px -apple-system,sans-serif';ctx.textAlign='center';
  ctx.fillText(vals[i],x,y-14);
}
}
async function showHistory(){
try{
var d=await fetch('/history').then(function(r){return r.json()});
var h=$('history-content');
var html='<p style="font-size:13px;color:var(--sub);margin-bottom:6px">共完成 <b>'+d.summary.total+'</b> 次模拟面试</p>';
if(d.summary.top_weak&&d.summary.top_weak.length){
  html+='<h4>高频薄弱点</h4>';
  d.summary.top_weak.forEach(function(w){
    html+='<div style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;font-size:13px"><span>'+w.tag+'</span><span style="color:var(--sub)">'+w.count+'次 · '+w.pct+'%</span></div><div class="weak-bar"><div style="width:'+w.pct+'%"></div></div></div>';
  });
}
if(d.summary.score_trend&&d.summary.score_trend.length){
  html+='<h4>得分趋势（最近'+d.summary.score_trend.length+'次）</h4><div style="display:flex;gap:6px;flex-wrap:wrap">';
  d.summary.score_trend.forEach(function(s){
    var c=s>=8?'var(--green)':(s>=6?'var(--orange)':'var(--red)');
    html+='<span class="score-pill" style="background:'+c+'">'+s+'</span>';
  });
  html+='</div>';
}
if(d.interviews&&d.interviews.length){
  html+='<h4>历史记录</h4>';
  d.interviews.slice().reverse().forEach(function(iv){
    var sc=iv.avg_score;if(sc===null||sc===undefined)sc='-';
    var c=sc>=8?'var(--green)':(sc>=6?'var(--orange)':'var(--red)');
    html+='<div class="hist-card"><div style="display:flex;justify-content:space-between;align-items:center"><div><b>'+iv.position+'</b> <span class="badge badge-b">'+typeName(iv.type)+'</span></div><span class="score-pill" style="background:'+c+'">'+sc+'/10</span></div>';
    html+='<div style="font-size:12px;color:var(--sub);margin:4px 0">'+iv.date+' · '+iv.rounds+'轮</div>';
    if(iv.weaknesses&&iv.weaknesses.length){
      html+='<div style="display:flex;gap:6px;flex-wrap:wrap">';
      iv.weaknesses.forEach(function(w){html+='<span class="tag tag-bad">'+w+'</span>';});
      html+='</div>';
    }
    html+='</div>';
  });
}else{
  html+='<p style="font-size:13px;color:var(--sub);margin-top:12px">还没有模拟记录。完成一次面试后，这里会沉淀你的薄弱点与得分趋势。</p>';
}
h.innerHTML=html;
$('history-modal').classList.remove('hidden');
}catch(e){alert('读取历史失败: '+e.message)}
}
function hideHistory(){$('history-modal').classList.add('hidden')}
function updateProgress(round){var f=$('round-progress-fill');if(f)f.style.width=Math.min(round,10)/10*100+'%';}
function toggleTheme(){var b=document.body;var dark=b.dataset.theme==='dark';var next=dark?'light':'dark';b.dataset.theme=next;try{localStorage.setItem('iv-theme',next)}catch(e){}var btn=$('theme-toggle');if(btn)btn.textContent=next==='dark'?'☀️':'🌙';if(window._lastDims)drawRadar('radar-canvas',window._lastDims);}
(function(){try{var t=localStorage.getItem('iv-theme');if(t){document.body.dataset.theme=t;var b=$('theme-toggle');if(b)b.textContent=t==='dark'?'☀️':'🌙';}}catch(e){}})();
document.addEventListener('keydown',function(e){if(e.key==='Escape')hideHistory()})
</script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            html = get_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html;charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        elif self.path == "/history":
            hist = load_history()
            self.send_json({"summary": get_weakness_summary(hist), "interviews": hist.get("interviews", [])})
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8"))

        if self.path == "/diagnose":
            p = body.get("position", "").strip()
            r = body.get("resume", "").strip()
            if not p or not r:
                self.send_json({"error": "不能为空"})
                return
            if len(r) < 80:
                prompt = f"面试教练，候选人面「{p}」但简历很少：{r}\n给策略（200字内）：\n1.面试官最可能问的2个问题+回答方向\n2.弥补简历的方法（举例）\n3.1条真诚话术"
            else:
                prompt = f"面试教练，分析「{p}」简历：{r}\n列出（200字内）：\n1.最明显3个弱点\n2.面试官会追问的2个坑\n3.1条面试前调整建议"
            try:
                diag = call_deepseek([{"role": "user", "content": prompt}])
                self.send_json({"diagnosis": diag})
            except Exception as e:
                self.send_json({"error": str(e)})

        elif self.path == "/start":
            p = body.get("position", "").strip()
            r = body.get("resume", "").strip()
            t = body.get("type", "biz")
            if t not in TYPE_PROMPTS:
                t = "biz"
            if not p or not r:
                self.send_json({"error": "不能为空"})
                return
            sid = str(len(conversations))
            sp = TYPE_PROMPTS[t]["style"].format(position=p, resume=r)
            # 迭代3：弱点自适应闭环——读取历史高频薄弱点，注入面试官 prompt
            focus = ""
            try:
                hist = load_history()
                summ = get_weakness_summary(hist)
                if summ["total"] > 0 and summ["top_weak"]:
                    top_tags = [w["tag"] for w in summ["top_weak"][:3]]
                    focus = "、".join(top_tags)
                    sp += ("\n【针对性加练】该候选人此前已完成 " + str(summ["total"]) +
                           " 次模拟面试，历史高频薄弱点为：" + focus +
                           "。请在本次面试中有意识地围绕这些方向出题，并在开场第一问就点出其中一个方向"
                           "（例如：『我注意到你之前几次面试在X上偏弱，我们先从这块聊』）。"
                           "注意：开场第一问仍只问一题、不评价、不打分、不写任何方括号标记。")
            except Exception:
                focus = ""
            msgs = [{"role": "system", "content": sp}]
            try:
                first = call_deepseek(msgs)
            except Exception as e:
                self.send_json({"error": str(e)})
                return
            msgs.append({"role": "assistant", "content": first})
            sc, disp, weak = parse_reply(first)
            conversations[sid] = {"position": p, "resume": r, "type": t,
                                  "messages": msgs, "round": 0,
                                  "scores": [sc] if sc else [],
                                  "weaknesses": weak, "summary": "", "finished": False}
            self.send_json({"session_id": sid, "message": disp, "weaknesses": weak, "type_label": TYPE_PROMPTS[t]["label"], "focus": focus})

        elif self.path == "/action":
            sid = body.get("session_id", "")
            action = body.get("action", "answer")
            answer = body.get("answer", "").strip()
            conv = conversations.get(sid)
            if not conv or conv.get("finished"):
                self.send_json({"error": "无效"})
                return
            inst = ""
            if action == "deep":
                inst = "（深挖追问）\n"
            elif action == "switch":
                inst = "（换方向）\n"
            elif action == "skip":
                inst = "（跳过此题）\n"
            elif action == "end":
                conv["finished"] = True
                conv["messages"].append({"role": "user", "content": "面试结束。请输出：\n1.整体评价\n2.优点\n3.改进方向\n4.练习建议\n\n最后请严格按以下 JSON 格式输出五维评分（1-10整数），不要换行、不要多余解释：\n[维度] {\"逻辑结构\":X, \"表达沟通\":X, \"业务深度\":X, \"方法论\":X, \"应变能力\":X}"})
                try:
                    summary = call_deepseek(conv["messages"])
                except Exception as e:
                    self.send_json({"finished": True, "message": "[系统] 总结生成失败：" + str(e)})
                    return
                dims, clean = parse_dimensions(summary)
                conv["summary"] = clean
                conv["dimensions"] = dims
                finish_record(sid)
                self.send_json({"finished": True, "message": clean, "dimensions": dims})
                return
            content = (inst + answer) if answer else inst
            if content.strip():
                conv["messages"].append({"role": "user", "content": content.strip()})
            conv["round"] += 1
            if conv["round"] > 10:
                conv["finished"] = True
                conv["messages"].append({"role": "user", "content": "面试结束。请输出：\n1.整体评价\n2.优点\n3.改进方向\n4.练习建议\n\n最后请严格按以下 JSON 格式输出五维评分（1-10整数），不要换行、不要多余解释：\n[维度] {\"逻辑结构\":X, \"表达沟通\":X, \"业务深度\":X, \"方法论\":X, \"应变能力\":X}"})
                try:
                    summary = call_deepseek(conv["messages"])
                except Exception as e:
                    self.send_json({"finished": True, "message": "[系统] 总结生成失败：" + str(e)})
                    return
                dims, clean = parse_dimensions(summary)
                conv["summary"] = clean
                conv["dimensions"] = dims
                finish_record(sid)
                self.send_json({"finished": True, "message": clean, "dimensions": dims})
                return
            try:
                reply = call_deepseek(conv["messages"])
            except Exception as e:
                self.send_json({"finished": False, "message": "[系统] 模型调用失败：" + str(e), "weaknesses": [], "round": conv["round"]})
                return
            conv["messages"].append({"role": "assistant", "content": reply})
            sc, disp, weak = parse_reply(reply)
            if sc is not None:
                conv["scores"].append(sc)
            conv["weaknesses"].extend(weak)
            self.send_json({"finished": False, "message": disp, "weaknesses": weak, "round": conv["round"]})
        else:
            self.send_error(404)

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json;charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"  AI面试模拟官 v2.2  http://localhost:{PORT}")
    http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
