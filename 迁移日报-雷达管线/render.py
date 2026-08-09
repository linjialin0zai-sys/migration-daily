# -*- coding: utf-8 -*-
"""渲染日报 HTML（与 PWA 壳同一视觉语言，独立单文件，可直接部署/推送）"""
import html as H

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
footer{margin-top:50px;padding-top:20px;border-top:1px solid var(--line-soft);font-size:12px;color:var(--text3)}
@media(max-width:560px){.row{grid-template-columns:1fr}.src{margin-left:0;flex-basis:100%}}
"""

GROUPS = [
    ("01", "能力边界 · 评测与可靠性", {"能力边界", "评测与可靠性"}),
    ("02", "质量现场 · 应用采用", {"内容生产与质量现场", "应用构建与采用"}),
    ("03", "商业 · 岗位 · 规则", {"商业、岗位与规则"}),
    ("04", "相邻领域", {"相邻领域"}),
]

def card_html(it):
    c = it["card"]
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
</div>"""

def render_daily(picked, oneliner, rejected_sample, day):
    secs = []
    for no, title, topics in GROUPS:
        cards = [c for c in picked if c["topic"] in topics]
        if not cards:
            continue
        secs.append(f'<div class="sec"><h2><span class="n">{no}</span>{title}</h2>'
                    + "".join(card_html(c) for c in cards) + "</div>")
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
<div class="hero"><div class="hero-in"><div class="t">今日一句话</div><p>{H.escape(oneliner)}</p></div></div>
{''.join(secs)}
{skip_block}
<footer>迁移日报 · 既相关，又开放 · 由雷达管线自动生成</footer>
</body></html>"""
