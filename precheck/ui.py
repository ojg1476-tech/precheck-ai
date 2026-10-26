"""문구레이더 화면 조각 (HTML). Streamlit 없이도 만들 수 있어 미리보기·테스트가 쉽다.

모든 사용자 글은 escape 해서 넣는다.
"""
from __future__ import annotations

from html import escape

from .batch import penalty_text

BRAND = "#3b5bdb"
TIER = {  # 이름: (글자색, 배경색, 설명)
    "높음": ("#c92a2a", "#fff5f5", "꼭 고칠 표현이 있어요"),
    "중간": ("#d9480f", "#fff4e6", "확인이 필요해요"),
    "확인": ("#1864ab", "#e7f5ff", "증명 자료를 챙기세요"),
    "양호": ("#2b8a3e", "#ebfbee", "걸린 표현이 없어요"),
    "오류": ("#868e96", "#f1f3f5", "읽지 못했어요"),
}
GRADE = {"red": ("#c92a2a", "#fff5f5"), "amber": ("#d9480f", "#fff4e6"), "blue": ("#1864ab", "#e7f5ff")}

CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
html, body, [class*="css"], .stMarkdown, .stTextArea textarea, button, input, select {
  font-family: 'Pretendard', -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif !important;
}
.block-container { padding-top: 2rem; max-width: 1180px; }
h1, h2, h3, h4 { letter-spacing: -0.02em; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid #e6e8ef; }
.stTabs [data-baseweb="tab"] { height: 44px; padding: 0 18px; border-radius: 10px 10px 0 0; font-weight: 600; }
.stTabs [aria-selected="true"] { color: #3b5bdb !important; }
div[data-testid="stExpander"] { border: 1px solid #e6e8ef; border-radius: 14px; background: #fff; }
.stButton > button, .stDownloadButton > button { border-radius: 10px; font-weight: 600; }
div[data-testid="stFileUploader"] section { border-radius: 14px; }

.mr-hero { background: linear-gradient(120deg, #eef2ff 0%, #f8f9ff 55%, #fff4e6 100%); border: 1px solid #e3e8fb;
  border-radius: 20px; padding: 28px 30px; margin-bottom: 18px; display: flex; gap: 20px; align-items: center; }
.mr-logo { width: 56px; height: 56px; border-radius: 16px; background: #3b5bdb; color: #fff; display: grid; place-items: center;
  font-size: 28px; flex: none; box-shadow: 0 6px 16px rgba(59,91,219,.25); }
.mr-hero h1 { margin: 0; padding: 0; font-size: 30px; font-weight: 800; color: #1b2430; }
.mr-hero p { margin: 4px 0 10px; color: #4a5160; font-size: 15.5px; }
.mr-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.mr-chip { background: #fff; border: 1px solid #dfe3f0; color: #4a5160; border-radius: 999px; padding: 3px 11px; font-size: 12.5px; }
.mr-chip b { color: #3b5bdb; }

.mr-section { font-size: 13px; font-weight: 700; color: #6b7280; letter-spacing: .04em; margin: 22px 0 8px; }
.mr-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
.mr-kpi { background: #fff; border: 1px solid #e6e8ef; border-radius: 16px; padding: 14px 16px; position: relative; overflow: hidden; }
.mr-kpi::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 5px; background: var(--c); }
.mr-kpi .k { font-size: 13px; color: #6b7280; }
.mr-kpi .v { font-size: 30px; font-weight: 800; color: #1b2430; line-height: 1.2; margin-top: 2px; font-variant-numeric: tabular-nums; }
.mr-kpi .d { font-size: 12px; color: var(--c); font-weight: 600; }
.mr-dist { display: flex; height: 12px; border-radius: 999px; overflow: hidden; margin: 12px 0 4px; background: #f1f3f5; }
.mr-dist span { display: block; height: 100%; }
.mr-legend { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12.5px; color: #6b7280; }
.mr-legend i { display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 5px; vertical-align: middle; }

.mr-bars { background: #fff; border: 1px solid #e6e8ef; border-radius: 16px; padding: 14px 18px; }
.mr-bar { display: grid; grid-template-columns: minmax(120px, 34%) 1fr 76px; gap: 12px; align-items: center; padding: 6px 0; font-size: 14px; }
.mr-bar .t { color: #1b2430; }
.mr-bar .track { background: #f1f3f5; border-radius: 999px; height: 10px; }
.mr-bar .fill { background: #3b5bdb; border-radius: 999px; height: 10px; }
.mr-bar .n { color: #6b7280; text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; }

.mr-pill { display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 12.5px; font-weight: 700; color: var(--c); background: var(--b); }
.mr-card { background: #fff; border: 1px solid #e6e8ef; border-left: 5px solid var(--c); border-radius: 14px; padding: 16px 18px; margin: 10px 0; }
.mr-card .head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.mr-card .label { font-weight: 700; color: #1b2430; font-size: 15.5px; }
.mr-card .phrase { margin: 10px 0 6px; font-size: 15px; color: #1b2430; }
.mr-card .phrase mark { background: var(--b); color: var(--c); padding: 1px 6px; border-radius: 6px; font-weight: 700; }
.mr-card .why { color: #4a5160; font-size: 14.5px; line-height: 1.6; }
.mr-two { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; margin-top: 10px; }
.mr-box { border-radius: 12px; padding: 10px 12px; font-size: 14px; line-height: 1.55; }
.mr-box b { display: block; font-size: 12px; letter-spacing: .03em; margin-bottom: 2px; }
.mr-risk { background: #fff8f0; color: #7a3a00; }
.mr-alt { background: #ebfbee; color: #1e5f2c; }
.mr-checks { margin: 10px 0 0; padding: 10px 12px; background: #f8f9fc; border-radius: 12px; font-size: 13.5px; color: #374151; }
.mr-checks b { font-size: 12px; color: #6b7280; }
.mr-checks div { margin-top: 4px; padding-left: 22px; position: relative; line-height: 1.5; }
.mr-checks div::before { content: ""; position: absolute; left: 2px; top: 3px; width: 12px; height: 12px; border: 1.5px solid #adb5bd; border-radius: 4px; }
.mr-foot { margin-top: 10px; font-size: 12px; color: #868e96; line-height: 1.6; }

.mr-text { background: #fff; border: 1px solid #e6e8ef; border-radius: 14px; padding: 16px 18px; line-height: 1.95; white-space: pre-wrap; font-size: 15px; }
.mr-text mark { padding: 1px 3px; border-radius: 4px; }
.mr-empty { text-align: center; color: #6b7280; padding: 34px 10px; background: #fff; border: 1px dashed #d5d9e3; border-radius: 16px; }
.mr-empty .big { font-size: 30px; }
.mr-note { font-size: 12.5px; color: #868e96; line-height: 1.6; }
</style>
"""


def hero(rule_count: int, version: str) -> str:
    return f"""<div class="mr-hero"><div class="mr-logo">📡</div><div>
<h1>문구레이더</h1>
<p>상세페이지 광고 문구를 식약처 기준으로 한 번에 점검하고, 위험한 상품부터 알려드려요.</p>
<div class="mr-chips"><span class="mr-chip">규칙 <b>{rule_count}개</b></span>
<span class="mr-chip">기준일 <b>{escape(version)}</b></span>
<span class="mr-chip">식약처 단속 데이터 반영</span><span class="mr-chip">화장품 · 식품 · 건강기능식품</span></div>
</div></div>"""


def kpis(ov: dict) -> str:
    total = ov["total"] or 1
    cards = [f'<div class="mr-kpi" style="--c:{BRAND}"><div class="k">점검한 상품</div><div class="v">{ov["total"]}</div>'
             f'<div class="d">상품</div></div>']
    for t in ("높음", "중간", "확인", "양호"):
        c, _, desc = TIER[t]
        n = ov["tiers"][t]
        cards.append(f'<div class="mr-kpi" style="--c:{c}"><div class="k">위험도 {t}</div><div class="v">{n}</div>'
                     f'<div class="d">{desc}</div></div>')
    dist = "".join(f'<span style="width:{ov["tiers"][t] / total * 100:.2f}%;background:{TIER[t][0]}" '
                   f'title="{t} {ov["tiers"][t]}"></span>' for t in TIER if ov["tiers"].get(t))
    legend = "".join(f'<span><i style="background:{TIER[t][0]}"></i>{t} {ov["tiers"][t]} '
                     f'({ov["tiers"][t] / total:.0%})</span>' for t in TIER if ov["tiers"].get(t))
    return (f'<div class="mr-kpis">{"".join(cards)}</div>'
            f'<div class="mr-dist">{dist}</div><div class="mr-legend">{legend}</div>')


def common_bars(ov: dict) -> str:
    if not ov["common"]:
        return ""
    top = ov["total"] or 1
    rows = "".join(f'<div class="mr-bar"><span class="t">{escape(name)}</span>'
                   f'<span class="track"><span class="fill" style="display:block;width:{n / top * 100:.1f}%"></span></span>'
                   f'<span class="n">{n}개 상품</span></div>' for name, n in ov["common"])
    return f'<div class="mr-bars">{rows}</div>'


def tier_pill(tier: str) -> str:
    c, b, _ = TIER[tier]
    return f'<span class="mr-pill" style="--c:{c};--b:{b}">위험도 {tier}</span>'


def finding_cards(findings) -> str:
    """같은 규칙에 걸린 표현은 카드 하나로 묶는다 (설명·처분·대안이 같으므로). 심각한 등급 먼저."""
    groups: dict = {}
    for f in sorted(findings, key=lambda x: ({"red": 0, "amber": 1, "blue": 2}[x.grade], x.start)):
        groups.setdefault((f.rule_id, f.grade), []).append(f)
    return "".join(finding_card(fs) for fs in groups.values())


def finding_card(fs) -> str:
    fs = fs if isinstance(fs, list) else [fs]
    f = fs[0]
    c, b = GRADE[f.grade]
    phrases = list(dict.fromkeys(x.phrase for x in fs))
    risk = (f'<div class="mr-box mr-risk"><b>이대로 두면</b>{escape(f.penalty)}</div>' if f.penalty else "")
    checks = ""
    if f.checks:
        checks = '<div class="mr-checks"><b>쓰기 전에 확인할 것</b>' + "".join(
            f"<div>{escape(x)}</div>" for x in f.checks) + "</div>"
    return f"""<div class="mr-card" style="--c:{c};--b:{b}">
<div class="head"><span class="mr-pill" style="--c:{c};--b:{b}">{escape(f.grade_name)}</span><span class="label">{escape(f.label)}</span></div>
<div class="phrase">찾은 표현 {" ".join(f"<mark>“{escape(p)}”</mark>" for p in phrases)}</div>
<div class="why">{escape(f.why)}</div>
<div class="mr-two">{risk}<div class="mr-box mr-alt"><b>대신 이렇게</b>{escape(f.alt)}</div></div>
{checks}
<div class="mr-foot">정확한 용어 · {escape(f.term)}<br>관련 기준 · {escape(f.law)}<br>출처 · {escape(f.source)}</div>
</div>"""


def highlighted(text: str, findings) -> str:
    out, pos = "", 0
    for f in findings:
        c, b = GRADE[f.grade]
        out += escape(text[pos:f.start])
        out += f'<mark style="background:{b};color:{c};border-bottom:2px solid {c}">{escape(text[f.start:f.end])}</mark>'
        pos = f.end
    out += escape(text[pos:])
    return f'<div class="mr-text">{out}</div>'


def one_summary(counts: dict) -> str:
    items = [("red", "꼭 고치세요"), ("amber", "한번 확인하세요"), ("blue", "증명 자료를 챙기세요")]
    cards = "".join(f'<div class="mr-kpi" style="--c:{GRADE[g][0]}"><div class="k">{name}</div>'
                    f'<div class="v">{counts[g]}</div></div>' for g, name in items)
    return f'<div class="mr-kpis">{cards}</div>'


def empty(icon: str, text: str) -> str:
    return f'<div class="mr-empty"><div class="big">{icon}</div>{escape(text)}</div>'


def product_title(i: int, r) -> str:
    """접기 상자 제목 (일반 글자만 들어감)."""
    c = r.counts
    return (f"{i}. {r.name}  ·  위험도 {r.tier}  ·  꼭 고치기 {c['red']} · 확인 필요 {c['amber']} · 자료 챙기기 {c['blue']}"
            f"  ·  최대 {penalty_text(r.max_penalty)}" if r.max_penalty else
            f"{i}. {r.name}  ·  위험도 {r.tier}  ·  꼭 고치기 {c['red']} · 확인 필요 {c['amber']} · 자료 챙기기 {c['blue']}")
