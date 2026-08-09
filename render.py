# -*- coding: utf-8 -*-
"""渲染日报 HTML（与 PWA 壳同一视觉语言，独立单文件，可直接部署/推送）"""
import html as H
import hashlib

CSS = """
:root{--bg:#060608;--card:#0f0f14;--line:#222228;--line-soft:#1a1a20;--text:#eef0f2;--text2:#a9afb7;--text3:#62676f;
--cyan:#00f0ff;--cyan-dim:rgba(0,240,255,.09);--magenta:#ff2d78;--magenta-dim:rgba(255,45,120,.11);
--serif:"Noto Serif SC","Songti SC",serif;--sans:"PingFang SC","Microsoft YaHei",sans-serif;--mono:monospace}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--sans);line-height:1.75;max-width:720px;margin:0 auto;padding:40px 20px 80px}
.kicker{font-size:11px;letter-spacing:.4em;color:var(--cyan);margin-bottom:14px}
h1{font-family:var(--serif);font-size:34px;text-shadow:-2.5px 0 rgba(255,45,120,.5),2.5px 0 rgba(0,240,255,.5)}
.meta{margin:14px 0 30px;font-size:13px;color:var(--text3)}
.hero{border-radius:16px;padding:1px;background:linear-gradient(120deg,rgba(0,240,255,.55),rgba(255,45,120,.4));margin-bottom:44px}
.hero-in{background:#0a0a0f;border-radius:15px;padding:20px 22px}
.hero-in .t{font-size:11px;letter-spacing:.3em;color:var(--cyan);margin-bottom:8px}
.hero-in p{font-family:var(--serif);font-size:17px}
.sec{margin-top:40px}
.sec h2{font-family:var(--serif);font-size:19px;border-bottom:1px solid var(--line-soft);padding-bottom:8px;margin-bottom:16px}
.sec h2 .n{font-family:var(--mono);color:var(--cyan);font-size:13px;margin-right:8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin-bottom:14px}
.top{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;align-items:center}
.topic{font-size:11px;padding:2px 10px;border-radius:99px;border:1px solid #3a3a44}
.angle{font-size:10px;padding:2px 8px;border-radius:99px;color:var(--cyan);border:1px solid rgba(0,240,255,.3)}
.angle.contra{color:var(--magenta);border-color:rgba(255,45,120,.45);background:var(--magenta-dim)}
.src{font-size:12px;color:var(--cyan);margin-left:auto;text-decoration:none;border-bottom:1px dashed rgba(0,240,255,.35)}
h3{font-family:var(--serif);font-size:17px;margin-bottom:12px;line-height:1.6}
.row{display:grid;grid-template-columns:76px 1fr;gap:4px 14px;font-size:14px;margin-bottom:9px}
.k{color:var(--text3);font-size:11px;letter-spacing:.12em;padding-top:4px;white-space:nowrap}
.v{color:var(--text2)}
.v i{color:var(--magenta);font-style:normal}
.conn{display:inline-block;font-size:10px;padding:1px 8px;border-radius:99px;color:var(--cyan);border:1px solid rgba(0,240,255,.35);margin-right:5px}
.skip{border:1px dashed var(--line);border-radius:12px;padding:14px 18px;font-size:13px;color:var(--text2);margin-bottom:10px}
.skip .r{display:block;font-size:12px;color:var(--text3);margin-top:4px}
/* ── 双轨凭证 ── */
.dual{display:flex;flex-wrap:wrap;gap:6px 16px;margin-top:14px;padding-top:14px;border-top:1px dashed var(--line);font-size:12px;color:var(--text2)}
.dual b{color:var(--cyan);font-weight:600}
.dual .mg b{color:var(--magenta)}
/* ── 卡片交互（一级：本设备 localStorage） ── */
.ops{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;padding-top:12px;border-top:1px dashed var(--line-soft)}
.op-btn{font-size:12px;color:var(--text2);background:none;border:1px solid var(--line);border-radius:99px;
  padding:6px 12px;min-height:36px;cursor:pointer;transition:all .15s;font-family:var(--sans)}
.op-btn:hover{border-color:#3a3a44;color:var(--text)}
.op-btn.on{color:var(--cyan);border-color:rgba(0,240,255,.45);background:var(--cyan-dim)}
.op-btn.calib-tg{margin-left:auto;color:var(--text3)}
.card.muted{opacity:.38;transition:opacity .2s}
.calib{max-height:0;overflow:hidden;transition:max-height .25s ease}
.calib-in{padding:12px 2px 2px;display:flex;gap:8px;flex-wrap:wrap}
.calib .lbl{width:100%;font-size:11px;color:var(--text3);letter-spacing:.1em}
.chip{font-size:11px;color:var(--text2);border:1px solid var(--line);border-radius:99px;padding:5px 11px;
  cursor:pointer;background:none;font-family:var(--sans)}
.chip.on{color:var(--cyan);border-color:rgba(0,240,255,.45);background:var(--cyan-dim)}
footer{margin-top:50px;padding-top:20px;border-top:1px solid var(--line-soft);font-size:12px;color:var(--text3)}
@media(max-width:560px){.row{grid-template-columns:1fr}.src{margin-left:0;flex-basis:100%}}
"""

GROUPS = [
    ("01", "能力边界 · 评测与可靠性", {"能力边界", "评测与可靠性"}),
    ("02", "质量现场 · 应用采用", {"内容生产与质量现场", "应用构建与采用"}),
    ("03", "商业 · 岗位 · 规则", {"商业、岗位与规则"}),
    ("04", "相邻领域", {"相邻领域"}),
]

CALIB_TAGS = ["太宽泛", "与我无关", "我已经知道", "证据不够", "想要更多此类"]

def card_html(it):
    c = it["card"]
    cid = hashlib.md5(it["link"].encode()).hexdigest()[:10]  # 稳定卡片ID，localStorage 状态靠它对应
    angles = "".join(
        f'<span class="angle{" contra" if a=="反例与挑战" else ""}">{H.escape(a)}</span>'
        for a in (it.get("angles") or []))
    conns = "".join(f'<span class="conn">{H.escape(x)}</span>' for x in c.get("connections", []))
    open_v = c.get("open_question", "")
    if "反例与挑战" in (it.get("angles") or []):
        open_v = f"<i>{H.escape(open_v)}</i>"
    else:
        open_v = H.escape(open_v)
    return f"""
<div class="card">
  <div class="top">
    <span class="topic">{H.escape(it['topic'])}</span>{angles}
    <a class="src" href="{H.escape(it['link'])}">{H.escape(it.get('evidence_type','来源'))} · {H.escape(it.get('published',''))} ↗</a>
  </div>
  <h3>{H.escape(c['title'])}</h3>
  <div class="row"><span class="k">为什么值得看</span><span class="v">{H.escape(c.get('worth',''))}</span></div>
  <div class="row"><span class="k">与我的可能连接</span><span class="v">{conns}{H.escape(c.get('connect_text',''))}</span></div>
  <div class="row"><span class="k">打开的问题</span><span class="v">{open_v}</span></div>
  <div class="ops" data-cid="{cid}">
    <button class="op-btn" data-op="fav">☆ 收藏</button>
    <button class="op-btn" data-op="spark">✎ 线索</button>
    <button class="op-btn" data-op="track">⌖ 追踪</button>
    <button class="op-btn" data-op="muted">✕ 忽略</button>
    <button class="op-btn calib-tg">校准这条 ▸</button>
  </div>
  <div class="calib"><div class="calib-in">
    <span class="lbl">这条为什么不对（点选，帮助明天调准）</span>
    {''.join(f'<button class="chip" data-tag="{t}">{t}</button>' for t in CALIB_TAGS)}
  </div></div>
</div>"""

JS = """
const KEY='md-ops-v1';
let st={};try{st=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}};
document.querySelectorAll('.card').forEach(card=>{
  const ops=card.querySelector('.ops');if(!ops)return;
  const cid=ops.dataset.cid, rec=st[cid]=st[cid]||{}, calib=card.querySelector('.calib');
  const sync=()=>{
    ops.querySelectorAll('[data-op]').forEach(b=>b.classList.toggle('on',!!rec[b.dataset.op]));
    card.classList.toggle('muted',!!rec.muted);
    calib.querySelectorAll('.chip').forEach(c=>c.classList.toggle('on',(rec.tags||[]).includes(c.dataset.tag)));
  };
  ops.querySelectorAll('[data-op]').forEach(b=>b.addEventListener('click',()=>{
    rec[b.dataset.op]=!rec[b.dataset.op];save();sync();}));
  const tg=ops.querySelector('.calib-tg');let open=false;
  tg.addEventListener('click',()=>{open=!open;
    calib.style.maxHeight=open?calib.scrollHeight+'px':'0px';
    tg.textContent=open?'收起校准 ▾':'校准这条 ▸';});
  calib.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{
    const t=c.dataset.tag;rec.tags=rec.tags||[];
    rec.tags=rec.tags.includes(t)?rec.tags.filter(x=>x!==t):[...rec.tags,t];save();sync();}));
  sync();
});
"""

DEEP_TOPICS = {"能力边界", "评测与可靠性", "内容生产与质量现场", "应用构建与采用"}
ORIG_KEYS = ("一手", "开源", "官方", "论文", "原始")

def render_daily(picked, oneliner, rejected_sample, day):
    secs = []
    for no, title, topics in GROUPS:
        cards = [c for c in picked if c["topic"] in topics]
        if not cards:
            continue
        secs.append(f'<div class="sec"><h2><span class="n">{no}</span>{title}</h2>'
                    + "".join(card_html(c) for c in cards) + "</div>")
    # 双轨凭证统计
    deep = sum(1 for p in picked if p["topic"] in DEEP_TOPICS)
    ext = len(picked) - deep
    contra = sum(1 for p in picked if "反例与挑战" in (p.get("angles") or []))
    orig = sum(1 for p in picked if any(k in p.get("evidence_type", "") for k in ORIG_KEYS))
    rate = round(orig / len(picked) * 100) if picked else 0
    dual = (f'<div class="dual"><span>双轨凭证：深耕 <b>{deep}</b> / 扩展 <b>{ext}</b></span>'
            f'<span class="mg">反例角度 <b>{contra}</b></span>'
            f'<span>原始来源率 <b>{rate}%</b></span></div>') if picked else ""
    skips = "".join(
        f'<div class="skip">✕ {H.escape(s["title"])}<span class="r">原因：{H.escape(s.get("reject_reason","未达入选线"))}</span></div>'
        for s in rejected_sample)
    skip_block = (f'<div class="sec"><h2><span class="n">05</span>今日拦截抽样</h2>{skips}</div>' if skips else "")
    return f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>今日雷达 · {day}</title>
<style>{CSS}</style></head><body>
<div class="kicker">MIGRATION DAILY · 今日雷达</div>
<h1>今日雷达</h1>
<div class="meta">{day} · 入选 {len(picked)} 条</div>
<div class="hero"><div class="hero-in"><div class="t">今日一句话</div><p>{H.escape(oneliner)}</p>{dual}</div></div>
{''.join(secs)}
{skip_block}
<footer>迁移日报 · 既相关，又开放 · 由雷达管线自动生成<br>
<span style="font-size:11px">卡片的收藏/线索/追踪/忽略与校准状态保存在本设备浏览器；反馈闭环（影响明日选稿）将在 V2 接通。</span></footer>
<script>{JS}</script>
</body></html>"""
