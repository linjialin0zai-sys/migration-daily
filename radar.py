# -*- coding: utf-8 -*-
"""
迁移日报 · 每日管线
用法：
    export MOONSHOT_API_KEY=sk-...        # 或任何 OpenAI 兼容 key
    python3 radar.py                      # 跑完整流程
    python3 radar.py --mock               # 不调用 LLM，用启发式假评分跑通流程（调试渲染用）

流程：抓取 RSS → 去重 → LLM 四维评分 → 双轨配额选取 → 主编一句话 → 渲染 HTML 日报页 + 更新存档索引
"""
import argparse, json, os, re, sys, time
from datetime import datetime, date, timezone, timedelta

def bj_today():
    """按北京时间取日期（GitHub Actions 跑在 UTC，直接 date.today() 会差一天）"""
    return datetime.now(timezone(timedelta(hours=8))).date()
from pathlib import Path

import feedparser  # pip install feedparser pyyaml requests
import yaml

try:
    import requests
except ImportError:
    requests = None

ROOT = Path(__file__).parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

# ───────────────────────── 配置 ─────────────────────────
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.moonshot.cn/v1")
LLM_API_KEY  = os.environ.get("MOONSHOT_API_KEY") or os.environ.get("LLM_API_KEY", "")
LLM_MODEL    = os.environ.get("LLM_MODEL", "kimi-k2.5")

TOPIC_POOL = {
    "A": ("能力边界", "能力边界_评测与可靠性"),
    "B": ("评测与可靠性", "能力边界_评测与可靠性"),
    "C": ("内容生产与质量现场", "质量现场_应用采用"),
    "D": ("应用构建与采用", "质量现场_应用采用"),
    "E": ("商业、岗位与规则", "商业岗位与规则"),
    "F": ("相邻领域", "相邻领域"),
}

# ───────────────────────── 抓取 ─────────────────────────
def load_sources():
    with open(ROOT / "sources.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _fetch_feed(url, timeout=15):
    """带 UA 和超时的抓取，防止个别源挂起拖死管线"""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "migration-radar/0.1"})
    data = urllib.request.urlopen(req, timeout=timeout).read()
    return feedparser.parse(data)

def fetch_items(cfg, hours=30):
    """抓取各信源最近 hours 小时的条目"""
    items, cutoff = [], time.time() - hours * 3600
    for src in cfg["sources"]:
        try:
            feed = _fetch_feed(src["url"])
            for e in feed.entries[:25]:
                ts = None
                for k in ("published_parsed", "updated_parsed"):
                    if getattr(e, k, None):
                        ts = time.mktime(getattr(e, k)); break
                if ts and ts < cutoff:
                    continue
                snippet = re.sub(r"<[^>]+>", " ", getattr(e, "summary", "") or "")
                snippet = re.sub(r"\s+", " ", snippet).strip()[:600]
                items.append({
                    "title": (e.get("title") or "").strip(),
                    "link": e.get("link", ""),
                    "published": datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else "",
                    "snippet": snippet,
                    "source_name": src["name"], "source_type": src["type"],
                })
            print(f"  ✓ {src['name']}: {len(feed.entries)} 条原始条目")
        except Exception as ex:
            print(f"  ✗ {src['name']}: {ex}")
    # 标题级去重
    seen, dedup = set(), []
    for it in items:
        key = re.sub(r"\W+", "", it["title"].lower())[:60]
        if key and key not in seen:
            seen.add(key); dedup.append(it)
    return dedup

# ───────────────────────── LLM ─────────────────────────
def llm(system, user, json_mode=True):
    """OpenAI 兼容调用；返回解析后的 JSON 或原文"""
    if not LLM_API_KEY:
        raise RuntimeError("未设置 MOONSHOT_API_KEY / LLM_API_KEY")
    body = {"model": LLM_MODEL, "temperature": 0.2,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(f"{LLM_BASE_URL}/chat/completions", json=body,
                      headers={"Authorization": f"Bearer {LLM_API_KEY}"}, timeout=90)
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    if json_mode:
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0))
    return text

# ───────────────────────── 评分 ─────────────────────────
def score_items(items, mock=False):
    from prompts import SCORING_SYSTEM, SCORING_USER
    kept, rejected = [], []
    for i, it in enumerate(items):
        if mock:
            s = mock_score(it)
        else:
            try:
                s = llm(SCORING_SYSTEM, SCORING_USER.format(**it))
            except Exception as ex:
                print(f"  ✗ 评分失败 [{it['title'][:20]}…]: {ex}"); continue
        it.update(s)
        (kept if s.get("verdict") == "keep" else rejected).append(it)
        if not mock and (i + 1) % 10 == 0:
            print(f"  … 已评分 {i+1}/{len(items)}")
    return kept, rejected

def mock_score(it):
    """无 LLM 时的启发式假评分，仅供调试渲染"""
    t = (it["title"] + it["snippet"]).lower()
    topic = "B" if any(w in t for w in ["benchmark", "eval", "评估", "评测"]) else \
            "F" if it["source_type"] == "相邻" else \
            "A" if any(w in t for w in ["model", "video", "生成", "diffusion"]) else "D"
    return {"verdict": "keep", "topic": TOPIC_POOL[topic][0],
            "angles": ["方法变化"], "entity": None, "evidence_type": it["source_type"],
            "scores": {"资讯价值": 6, "专业相关性": 5, "写作与案例潜力": 5, "认知扩展性": 5},
            "card": {"title": it["title"][:40], "worth": "（mock）待 LLM 生成",
                     "connections": ["工作"], "connect_text": "（mock）", "open_question": "（mock）"}}

# ───────────────────────── 双轨配额选取 ─────────────────────────
def select_daily(kept, cfg):
    """按配额选取：资讯价值是门槛，四维加权排序，配额保证双轨并存"""
    q = cfg["quota"]
    def rank(it):
        s = it["scores"]
        return s["资讯价值"] * 3 + s["专业相关性"] * 2 + s["写作与案例潜力"] * 1.5 + s["认知扩展性"] * 1.5

    # 门槛：资讯价值 ≥ 5 才进入候选（宁缺毋滥）
    pool = [it for it in kept if it["scores"]["资讯价值"] >= 5]
    pool.sort(key=rank, reverse=True)

    picked, entity_count = [], {}
    def try_take(it, force=False):
        ent = (it.get("entity") or "").lower()
        if ent and entity_count.get(ent, 0) >= cfg["dedup"]["same_entity_max_per_day"]:
            return False
        if not force and it in picked:
            return False
        picked.append(it)
        if ent: entity_count[ent] = entity_count.get(ent, 0) + 1
        return True

    def fill(pool_key, n_min, n_max):
        n = 0
        for it in pool:
            if n >= n_max: break
            p = next((v[1] for k, v in TOPIC_POOL.items() if v[0] == it["topic"]), None)
            if p == pool_key and it not in picked and try_take(it):
                n += 1
        return n >= n_min

    fill("能力边界_评测与可靠性", 2, 2)
    fill("质量现场_应用采用", *q["质量现场_应用采用"])
    fill("商业岗位与规则", *q["商业岗位与规则"])
    fill("相邻领域", 1, 1)
    # 反例角度：有合格者保底 1 条（可挤占第 7 席）
    if not any("反例与挑战" in (it.get("angles") or []) for it in picked):
        contra = next((it for it in pool
                       if "反例与挑战" in (it.get("angles") or [])
                       and it["scores"]["资讯价值"] >= 7 and it not in picked), None)
        if contra: try_take(contra, force=True)

    lo, hi = q["total"]
    picked = picked[:hi]
    return picked

# ───────────────────────── 主编一句话 ─────────────────────────
def make_oneliner(picked, mock=False):
    from prompts import ONELINER_SYSTEM, ONELINER_USER
    if not picked:
        return "今天没有足以改变视野边界的重大新信号。"
    if mock:
        return "（mock）这里是主编一句话，接入 LLM 后生成。"
    cards = json.dumps([p["card"]["title"] + " | " + "、".join(p.get("angles") or [])
                        for p in picked], ensure_ascii=False, indent=1)
    try:
        return llm(ONELINER_SYSTEM, ONELINER_USER.format(cards_json=cards), json_mode=False).strip()
    except Exception:
        return "今天没有足以改变视野边界的重大新信号。"

# ───────────────────────── 渲染 ─────────────────────────
def render_html(picked, oneliner, rejected_sample, day):
    from render import render_daily
    return render_daily(picked, oneliner, rejected_sample, day)

# ───────────────────────── 主流程 ─────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="不调用 LLM，调试渲染")
    ap.add_argument("--hours", type=int, default=30, help="抓取最近多少小时")
    args = ap.parse_args()

    print("① 载入信源…"); cfg = load_sources()
    print("② 抓取…"); items = fetch_items(cfg, args.hours)
    print(f"   去重后 {len(items)} 条候选")
    if not items: print("今日无候选，结束。"); return

    print("③ 评分…"); kept, rejected = score_items(items, mock=args.mock)
    print(f"   保留 {len(kept)} / 淘汰 {len(rejected)}")

    print("④ 双轨选取…"); picked = select_daily(kept, cfg)
    for p in picked:
        print(f"   · [{p['topic']}|{'+'.join(p.get('angles') or [])}] {p['card']['title']}")

    print("⑤ 主编一句话…"); oneliner = make_oneliner(picked, mock=args.mock)
    print(f"   {oneliner}")

    print("⑥ 渲染…")
    rejected_sample = rejected[:2]
    html = render_html(picked, oneliner, rejected_sample, bj_today())
    fname = OUT / f"{bj_today().isoformat()}.html"
    fname.write_text(html, encoding="utf-8")
    print(f"   已生成 {fname}")
    update_index()
    print("   已更新 output/index.html 存档索引")

def update_index():
    """扫描 output/ 下所有日报，生成存档索引页（GitHub Pages 的落地页）"""
    days = sorted((p for p in OUT.glob("2*.html")), reverse=True)
    rows = "\n".join(
        f'<a class="day" href="{p.name}"><b>{p.stem}</b><span>打开 →</span></a>'
        for p in days)
    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>迁移日报 · 存档</title>
<style>
body{{background:#060608;color:#eef0f2;font-family:"PingFang SC","Microsoft YaHei",sans-serif;max-width:640px;margin:0 auto;padding:48px 20px}}
h1{{font-family:"Noto Serif SC","Songti SC",serif;text-shadow:-2px 0 rgba(255,45,120,.5),2px 0 rgba(0,240,255,.5)}}
.kicker{{font-size:11px;letter-spacing:.4em;color:#00f0ff;margin-bottom:14px}}
.day{{display:flex;justify-content:space-between;align-items:center;background:#0f0f14;border:1px solid #222228;border-radius:12px;
padding:16px 20px;margin-bottom:10px;color:inherit;text-decoration:none;font-size:15px}}
.day:hover{{border-color:#2e2e38}}
.day span{{color:#62676f;font-size:13px}}
footer{{margin-top:40px;font-size:12px;color:#62676f}}
</style></head><body>
<div class="kicker">MIGRATION DAILY · ARCHIVE</div><h1>迁移日报 · 存档</h1>
<p style="color:#62676f;font-size:13px;margin:10px 0 26px">每天 07:30 自动更新 · 共 {len(days)} 期</p>
{rows}
<footer>迁移日报 · 既相关，又开放 · 由雷达管线自动生成</footer>
</body></html>"""
    (OUT / "index.html").write_text(page, encoding="utf-8")

if __name__ == "__main__":
    main()
