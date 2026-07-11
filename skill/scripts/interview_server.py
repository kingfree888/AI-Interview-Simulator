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
    m = re.search(r"\[打分\]\s*(\d+)\s*/\s*10", reply)
    if m:
        score = int(m.group(1))
    weak = []
    wm = re.search(r"\[弱点\]\s*([^\n\[]*)", reply)
    if wm:
        for part in re.split(r"[,，/、]", wm.group(1)):
            part = part.strip()
            if part:
                weak.append(normalize_weak(part))
    disp = re.sub(r"\[弱点\][^\n\[]*", "", reply)
    return score, disp, weak


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
:root{--bg:#f8f9fa;--card-bg:#fff;--text:#1a1a2e;--sub:#6b7280;--border:#e5e7eb;--blue:#2563eb;--blue-light:#eff6ff;--green:#16a34a;--red:#dc2626;--orange:#ea580c;--radius:12px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}
.container{max-width:800px;margin:0 auto;padding:20px}
.topbar{display:flex;justify-content:flex-end;margin-bottom:4px}
header{text-align:center;padding:24px 0 8px}
header h1{font-size:24px;font-weight:600}
header p{font-size:14px;color:var(--sub);margin-top:4px}
.card{background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);padding:24px;margin-bottom:16px}
label{display:block;font-size:14px;font-weight:500;margin-bottom:6px}
input,textarea,select{width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:8px;font-size:14px;font-family:inherit;outline:none;autocomplete:off}
input:focus,textarea:focus,select:focus{border-color:var(--blue);box-shadow:0 0 0 3px rgba(37,99,235,.1)}
textarea{resize:vertical;min-height:120px}
.inline-row{display:flex;gap:12px;align-items:flex-end}.inline-row>div{flex:1}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:10px 24px;border-radius:8px;font-size:14px;font-weight:500;cursor:pointer;border:none;transition:all .2s;font-family:inherit}
.btn-primary{background:var(--blue);color:#fff}.btn-primary:hover{background:#1d4ed8}.btn-primary:disabled{opacity:.5;cursor:not-allowed}
.btn-outline{background:var(--card-bg);border:1px solid var(--border);color:var(--text)}.btn-outline:hover{background:var(--bg)}
.btn-sm{padding:6px 14px;font-size:13px}
.chat-area{max-height:55vh;overflow-y:auto;padding:8px 0}
.msg{margin-bottom:16px;animation:fadeIn .3s}
.msg-ai .bubble{background:var(--blue-light);border:1px solid #bfdbfe;border-radius:var(--radius);padding:16px;font-size:14px;white-space:pre-wrap}
.msg-user .bubble{background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);padding:14px;font-size:14px;margin-left:32px}
.msg-ai .bubble:before{content:"面试官";display:block;font-size:12px;color:var(--blue);margin-bottom:4px;font-weight:500}
.msg-user .bubble:before{content:"你";display:block;font-size:12px;color:var(--sub);margin-bottom:4px}
.input-row{display:flex;gap:10px;margin-top:16px}.input-row textarea{flex:1;min-height:60px;padding:10px}
.action-bar{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;justify-content:center}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:500}
.badge-g{background:#dcfce7;color:var(--green)}.badge-r{background:#fef2f2;color:var(--red)}
.badge-o{background:#fff7ed;color:var(--orange)}.badge-b{background:var(--blue-light);color:var(--blue)}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.spinner{display:inline-block;width:16px;height:16px;border:2px solid #e5e7eb;border-top-color:var(--blue);border-radius:50%;animation:spin .6s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.hidden{display:none!important}
.modal{position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;align-items:center;justify-content:center;z-index:100;padding:16px}
.modal-box{background:#fff;border-radius:14px;padding:24px;max-width:680px;width:100%;max-height:84vh;overflow:auto}
.modal-box h3{font-size:18px;font-weight:600}
.modal-box h4{font-size:14px;font-weight:600;margin:14px 0 8px;color:var(--text)}
.weak-bar{height:6px;background:#eef2f7;border-radius:4px;margin-top:4px;overflow:hidden}
.weak-bar>div{height:100%;background:var(--red);border-radius:4px}
.hist-card{border:1px solid var(--border);border-radius:10px;padding:12px;margin-bottom:10px}
.score-pill{color:#fff;padding:3px 10px;border-radius:6px;font-size:13px;font-weight:600}
.warn-box{margin-top:14px;padding:12px;background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;font-size:13px;color:#9a3412;line-height:1.7}
</style>
</head>
<body>
<div class="container">
<div class="topbar"><button class="btn btn-outline btn-sm" onclick="showHistory()">📊 面试历史</button></div>
<header>
<h1>AI面试模拟官</h1>
<p>多类型面试 · 简历诊断 · 追问控制 · 成长追踪</p>
</header>

<div id="setup-card" class="card">
<div class="inline-row">
<div><label>目标岗位</label><input id="position" autocomplete="off" placeholder="如：产品经理..."></div>
<div><label>面试类型</label><select id="interviewType"><option value="biz">业务面</option><option value="hr">HR面</option><option value="boss">总监面</option><option value="stress">压力面</option></select></div>
</div>
<div style="height:12px"></div>
<label>粘贴简历</label><textarea id="resume" autocomplete="off" placeholder="把你的简历粘贴到这里..."></textarea>
<div style="margin-top:16px"><button id="start-btn" class="btn btn-primary" onclick="startFlow()">诊断简历，开始面试</button></div>
</div>

<div id="diagnosis-card" class="card hidden">
<h3 style="margin-bottom:12px">简历分析</h3><div id="diag-content" style="font-size:14px;line-height:1.8"></div>
<div style="margin-top:16px"><button class="btn btn-primary" onclick="confirmStart()">开始面试</button><button class="btn btn-outline btn-sm" style="margin-left:8px" onclick="backToSetup()">返回修改</button></div>
</div>

<div id="interview-card" class="card hidden">
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
<span id="type-badge" class="badge badge-b">业务面</span><span style="font-size:12px;color:var(--sub)" id="round-info"></span></div>
<div class="chat-area" id="chat"></div>
<div id="input-area">
<div class="input-row"><textarea id="answer" autocomplete="off" placeholder="输入你的回答...（Ctrl+Enter 或点「发送回答」）" onkeydown="if(event.ctrlKey&&event.key==='Enter')doAction('answer')"></textarea>
<button id="send-btn" class="btn btn-primary" style="align-self:flex-end;white-space:nowrap" onclick="doAction('answer')">📤 发送回答</button></div>
<div class="action-bar" style="margin-top:12px">
<button class="btn btn-outline btn-sm" onclick="doAction('deep')">深挖追问</button>
<button class="btn btn-outline btn-sm" onclick="doAction('switch')">换方向</button>
<button class="btn btn-outline btn-sm" onclick="doAction('skip')">跳过</button>
<button class="btn btn-outline btn-sm" style="color:var(--red);border-color:#fecaca" onclick="doAction('end')">结束面试</button>
</div>
</div>
</div>

<div id="summary-card" class="card hidden"></div>
</div>

<div id="history-modal" class="modal hidden" onclick="if(event.target===this)hideHistory()">
<div class="modal-box">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
<h3>面试历史</h3><button class="btn btn-outline btn-sm" onclick="event.stopPropagation();hideHistory()">✕ 关闭</button>
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
t=t.replace(/\\[评价\\]/g,'<span class="badge badge-g">评价</span> ');
t=t.replace(/\\[打分\\]\\s*(\\d+)\\/10/g,'<span class="badge badge-o">$1/10</span>');
t=t.replace(/\\[建议\\]/g,'<span class="badge badge-b">建议</span> ');
t=t.replace(/\\[下一题\\]/g,'<span class="badge badge-b">下一题</span>');
d.innerHTML='<div class="bubble">'+t+'</div>';
if(weakArr&&weakArr.length){
  var chip=document.createElement('div');chip.style.marginTop='8px';
  weakArr.forEach(function(w){chip.innerHTML+='<span class="badge badge-r" style="margin-right:6px">'+w+'</span>';});
  d.querySelector('.bubble').appendChild(chip);
}
$('chat').appendChild(d);$('chat').scrollTop=$('chat').scrollHeight;
}
function btnSpin(el,loading){
if(loading){el.setAttribute('data-orig',el.innerHTML);el.innerHTML='<span class="spinner"></span> 加载中';el.disabled=true}
else{el.innerHTML=el.getAttribute('data-orig')||el.innerHTML;el.disabled=false}
}
function api(url,data){
return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}).then(function(r){return r.json()});
}
async function startFlow(){
var p=$('position').value.trim(),r=$('resume').value.trim();
if(!p||!r){alert('请填写岗位和简历');return;}
var btn=$('start-btn');btnSpin(btn,true);
try{
var d=await api('/diagnose',{position:p,resume:r});
$('diag-content').innerHTML=d.diagnosis.replace(/\\n/g,'<br>');
await showWeakWarning();
$('setup-card').classList.add('hidden');
$('diagnosis-card').classList.remove('hidden');
}catch(e){alert('诊断出错: '+e.message)}
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
typeLabel=$('interviewType').selectedOptions[0].text;
$('diagnosis-card').classList.add('hidden');
$('interview-card').classList.remove('hidden');
$('type-badge').textContent=typeLabel;
isWaiting=1;showThinking();
try{
var d=await api('/start',{position:p,resume:r,type:t});
removeThinking();
if(d.error){addMsg('ai','[系统] '+d.error);}
else{sessionId=d.session_id;addMsg('ai',d.message,d.weaknesses);$('round-info').textContent='第1轮';}
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
else if(d.finished){addMsg('ai',d.message);showSummary(d.message);$('input-area').classList.add('hidden')}
else{addMsg('ai',d.message,d.weaknesses);$('round-info').textContent='第'+d.round+'/10轮'}
}catch(e){removeThinking();addMsg('ai','[系统] 网络出错: '+e.message)}
isWaiting=0;setWaiting(false);if(action!=='end')$('answer').focus();
}
function setWaiting(on){var b=$('send-btn');if(b){b.disabled=on;b.innerHTML=on?'<span class="spinner"></span> 思考中…':'📤 发送回答'}}
function showThinking(){if($('thinking'))return;var d=document.createElement('div');d.className='msg msg-ai';d.id='thinking';d.innerHTML='<div class="bubble"><span class="spinner"></span> 面试官正在思考…</div>';$('chat').appendChild(d);$('chat').scrollTop=$('chat').scrollHeight;}
function removeThinking(){var t=$('thinking');if(t)t.remove();}
function showSummary(text){
var c=$('summary-card');c.classList.remove('hidden');
c.innerHTML='<h3 style="margin-bottom:12px">面试总评</h3><div style="font-size:14px;white-space:pre-wrap">'+text+'</div><div style="margin-top:16px"><button class="btn btn-primary" onclick="location.reload()">再来一次</button></div>';
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
      iv.weaknesses.forEach(function(w){html+='<span class="badge badge-r">'+w+'</span>';});
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
            self.send_json({"session_id": sid, "message": disp, "weaknesses": weak, "type_label": TYPE_PROMPTS[t]["label"]})

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
                conv["messages"].append({"role": "user", "content": "面试结束。总结：1.整体 2.优点 3.改进 4.练习方向"})
                try:
                    summary = call_deepseek(conv["messages"])
                except Exception as e:
                    self.send_json({"finished": True, "message": "[系统] 总结生成失败：" + str(e)})
                    return
                conv["summary"] = summary
                finish_record(sid)
                self.send_json({"finished": True, "message": summary})
                return
            content = (inst + answer) if answer else inst
            if content.strip():
                conv["messages"].append({"role": "user", "content": content.strip()})
            conv["round"] += 1
            if conv["round"] > 10:
                conv["finished"] = True
                conv["messages"].append({"role": "user", "content": "面试结束。总结：1.整体 2.优点 3.改进 4.练习方向"})
                try:
                    summary = call_deepseek(conv["messages"])
                except Exception as e:
                    self.send_json({"finished": True, "message": "[系统] 总结生成失败：" + str(e)})
                    return
                conv["summary"] = summary
                finish_record(sid)
                self.send_json({"finished": True, "message": summary})
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
