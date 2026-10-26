"""문구레이더 화면 조각 (HTML). Streamlit 없이도 만들 수 있어 미리보기·테스트가 쉽다.

디자인 방향: 광고 문구 '교정지'. 짙은 녹색(심의 통과·신뢰)이 바탕 색, 빨간색은 고칠 곳에만.
모든 사용자 글은 escape 해서 넣는다.
"""
from __future__ import annotations

from html import escape

from .batch import penalty_text

INK, MUTED, FAINT = "#17211e", "#5d6a65", "#8a958f"
LINE, LINE_SOFT, PAGE = "#dce2df", "#ebefed", "#f1f4f2"
PINE, PINE_TINT = "#0e5a47", "#e3efea"
TIER = {  # 이름: (색, 옅은 색, 설명)
    "높음": ("#d7263d", "#fcebec", "꼭 고칠 표현이 있어요"),
    "중간": ("#b86e00", "#fbf1df", "확인이 필요해요"),
    "확인": ("#2b62a8", "#e6eef8", "증명 자료를 챙기세요"),
    "양호": ("#2e7d4f", "#e4f2e9", "걸린 표현이 없어요"),
    "오류": ("#7a847f", "#eef1ef", "읽지 못했어요"),
}
GRADE = {"red": TIER["높음"][:2], "amber": TIER["중간"][:2], "blue": TIER["확인"][:2]}
SAMPLE_COPY = ("피부 재생 크림, 7일 만에 주름 개선", "cos")

CSS = f"""
<style>
@import url('https://cdn.jsdelivr.net/gh/sun-typeface/SUIT@2/fonts/variable/woff2/SUIT-Variable.css');
html, body, [class*="css"], .stMarkdown, .stTextArea textarea, button, input, select, [data-testid="stWidgetLabel"] {{
  font-family: 'SUIT Variable', 'SUIT', -apple-system, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif !important;
}}
.stApp {{ background: {PAGE}; }}
.block-container {{ padding-top: 3.2rem; max-width: 1160px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 22px; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ height: 42px; padding: 0 2px; font-weight: 700; color: {MUTED}; background: transparent; }}
.stTabs [aria-selected="true"] {{ color: {INK} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {PINE}; height: 3px; }}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{ background: {PINE}; border-color: {PINE}; }}
.stButton > button, .stDownloadButton > button, [data-testid="stPopover"] button {{ border-radius: 8px; font-weight: 700; }}
div[data-testid="stFileUploader"] section {{ border-radius: 10px; background: #fff; border: 1px dashed #c3ccc8; }}
div[data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: {LINE}; border-radius: 10px; }}

/* 첫 화면 */
.mr-hero {{ display: grid; grid-template-columns: 1.05fr 1fr; gap: 28px; align-items: center; padding: 6px 0 22px;
  border-bottom: 1px solid {LINE}; margin-bottom: 6px; }}
@media (max-width: 860px) {{ .mr-hero {{ grid-template-columns: 1fr; }} }}
.mr-brand {{ display: flex; align-items: center; gap: 9px; font-weight: 800; color: {PINE}; font-size: 15px; }}
.mr-mark {{ width: 20px; height: 20px; border-radius: 50%; background: {PINE}; flex: none;
  box-shadow: inset 0 0 0 4px {PINE}, inset 0 0 0 6px #ffffffcc, inset 0 0 0 9px {PINE}, inset 0 0 0 11px #ffffff88; }}
.mr-title {{ margin: 14px 0 0; font-size: 34px; line-height: 1.24; font-weight: 800; color: {INK}; letter-spacing: -0.035em; }}
.mr-lead {{ margin: 12px 0 0; color: {MUTED}; font-size: 15px; line-height: 1.6; max-width: 34em; }}
.mr-facts {{ display: flex; gap: 18px; margin-top: 16px; color: {MUTED}; font-size: 13px; }}
.mr-facts b {{ color: {INK}; font-weight: 800; font-size: 15px; margin-right: 4px; font-variant-numeric: tabular-nums; }}

.mr-proof {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px; padding: 18px 20px; position: relative;
  box-shadow: 0 1px 0 {LINE_SOFT}, 0 12px 28px -18px #17211e40; }}
.mr-proof .cap {{ font-size: 12px; color: {FAINT}; margin-bottom: 10px; }}
.mr-proof .copy {{ font-size: 21px; font-weight: 700; color: {INK}; line-height: 1.6; letter-spacing: -0.02em; }}
.mr-proof .copy s {{ text-decoration: none; background: linear-gradient(transparent 52%, var(--c) 52%, var(--c) 60%, transparent 60%);
  color: {INK}; }}
.mr-proof .copy u {{ text-decoration: underline wavy var(--c); text-underline-offset: 5px; text-decoration-thickness: 1.5px; }}
.mr-proof .notes {{ margin-top: 12px; border-top: 1px solid {LINE_SOFT}; padding-top: 10px; display: grid; gap: 7px; }}
.mr-proof .note {{ display: grid; grid-template-columns: 92px 1fr; gap: 10px; font-size: 13px; color: {MUTED}; align-items: baseline; }}
.mr-proof .note span:first-child {{ color: var(--c); font-weight: 800; }}
.mr-proof .note em {{ font-style: normal; color: {PINE}; font-weight: 700; }}

/* 공통 */
.mr-section {{ font-size: 15px; font-weight: 800; color: {INK}; margin: 18px 0 10px; letter-spacing: -0.01em; }}
.mr-section small {{ font-size: 13px; color: {FAINT}; font-weight: 500; margin-left: 6px; }}
.mr-sub {{ font-size: 13px; font-weight: 700; color: {MUTED}; margin: 0 0 8px; }}
.mr-label {{ font-size: 14px; color: {INK}; font-weight: 700; }}
.mr-hint {{ font-size: 12px; color: {FAINT}; margin: -6px 0 10px; }}
.mr-hint b {{ color: {MUTED}; font-weight: 700; }}
.mr-sq {{ display: inline-block; width: 9px; height: 9px; border-radius: 2px; background: var(--c); margin-right: 6px; }}

/* 요약 */
.mr-board {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px; padding: 18px 20px 16px; }}
.mr-nums {{ display: grid; grid-template-columns: 1.15fr repeat(4, 1fr); }}
.mr-num {{ padding: 0 14px; border-left: 1px solid {LINE_SOFT}; }}
.mr-num:first-child {{ padding-left: 0; border-left: none; }}
.mr-num .k {{ font-size: 13px; color: {MUTED}; display: flex; align-items: center; }}
.mr-num .v {{ font-size: 32px; font-weight: 800; color: {INK}; line-height: 1.15; margin-top: 6px; font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }}
.mr-num .v small {{ font-size: 14px; color: {FAINT}; font-weight: 600; margin-left: 3px; }}
.mr-num .d {{ font-size: 12px; color: {FAINT}; margin-top: 2px; }}
.mr-num.zero .v {{ color: #c3ccc8; }}
.mr-dist {{ display: flex; height: 8px; border-radius: 4px; overflow: hidden; margin: 18px 0 0; background: {LINE_SOFT}; gap: 2px; }}
.mr-dist span {{ display: block; height: 100%; }}

.mr-bars {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px; padding: 12px 20px; }}
.mr-bar {{ display: grid; grid-template-columns: 1fr minmax(60px, 32%) 64px; gap: 12px; align-items: center; padding: 8px 0;
  font-size: 14px; border-bottom: 1px solid {LINE_SOFT}; }}
.mr-bar:last-child {{ border-bottom: none; }}
.mr-bar .t {{ color: {INK}; }}
.mr-bar .track {{ background: {LINE_SOFT}; border-radius: 3px; height: 6px; }}
.mr-bar .fill {{ background: {PINE}; border-radius: 3px; height: 6px; }}
.mr-bar .n {{ color: {MUTED}; text-align: right; font-variant-numeric: tabular-nums; font-size: 13px; }}

/* 표 */
.mr-table-wrap {{ max-height: var(--h, 430px); overflow: auto; background: #fff; border: 1px solid {LINE}; border-radius: 12px; }}
.mr-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
.mr-table th {{ position: sticky; top: 0; z-index: 1; background: #fff; color: {FAINT}; font-weight: 600; font-size: 12.5px;
  text-align: left; padding: 11px 14px; border-bottom: 1px solid {LINE}; white-space: nowrap; }}
.mr-table td {{ padding: 11px 14px; border-bottom: 1px solid {LINE_SOFT}; vertical-align: top; color: {INK}; line-height: 1.5;
  word-break: keep-all; overflow-wrap: anywhere; }}
.mr-table tr:last-child td {{ border-bottom: none; }}
.mr-table tbody tr:hover td {{ background: #f7faf8; }}
.mr-table .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.mr-table .z {{ color: #c3ccc8; }}
.mr-table td.nm {{ min-width: 130px; }}
.mr-table td.nw {{ white-space: nowrap; }}
.mr-table .memo {{ color: {FAINT}; font-size: 13px; min-width: 150px; }}
.mr-tier {{ display: inline-flex; align-items: center; font-weight: 700; color: var(--c); white-space: nowrap; }}

/* 결과 카드 */
.mr-phead {{ display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin: 2px 0 6px; }}
.mr-phead .n {{ font-size: 19px; font-weight: 800; color: {INK}; letter-spacing: -0.02em; }}
.mr-phead .m {{ font-size: 13px; color: {MUTED}; }}
.mr-card {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px; padding: 16px 18px; margin: 10px 0; }}
.mr-card .head {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
.mr-grade {{ font-size: 12px; font-weight: 800; color: var(--c); background: var(--b); border-radius: 4px; padding: 2px 7px; }}
.mr-card .label {{ font-weight: 800; color: {INK}; font-size: 15.5px; letter-spacing: -0.01em; }}
.mr-card .phrase {{ margin: 12px 0 6px; font-size: 16px; color: {INK}; display: flex; flex-wrap: wrap; gap: 6px 14px; }}
.mr-card .phrase u {{ text-decoration: underline wavy var(--c); text-underline-offset: 5px; text-decoration-thickness: 1.5px; font-weight: 700; }}
.mr-card .why {{ color: {MUTED}; font-size: 14.5px; line-height: 1.65; }}
.mr-two {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 0; margin-top: 12px;
  border: 1px solid {LINE_SOFT}; border-radius: 8px; overflow: hidden; }}
.mr-box {{ padding: 11px 14px; font-size: 14px; line-height: 1.6; color: {INK}; }}
.mr-box + .mr-box {{ border-left: 1px solid {LINE_SOFT}; }}
.mr-box b {{ display: block; font-size: 12.5px; margin-bottom: 3px; }}
.mr-risk b {{ color: #b0303f; }}
.mr-alt {{ background: #f6faf8; }}
.mr-alt b {{ color: {PINE}; }}
.mr-checks {{ margin: 12px 0 0; font-size: 13.5px; color: {INK}; }}
.mr-checks b {{ font-size: 12.5px; color: {MUTED}; }}
.mr-checks div {{ margin-top: 5px; padding-left: 22px; position: relative; line-height: 1.55; }}
.mr-checks div::before {{ content: ""; position: absolute; left: 1px; top: 4px; width: 11px; height: 11px; border: 1.5px solid #a9b4af; border-radius: 3px; }}
.mr-foot {{ margin-top: 12px; padding-top: 10px; border-top: 1px solid {LINE_SOFT}; font-size: 12px; color: {FAINT}; line-height: 1.7; }}

.mr-text {{ background: #fff; border: 1px solid {LINE}; border-radius: 12px; padding: 16px 18px; line-height: 2; white-space: pre-wrap; font-size: 15.5px; color: {INK}; }}
.mr-text u {{ text-decoration: underline wavy var(--c); text-underline-offset: 5px; text-decoration-thickness: 1.5px; font-weight: 700; }}
.mr-empty {{ color: {MUTED}; padding: 38px 10px; background: #fff; border: 1px dashed #c3ccc8; border-radius: 12px; text-align: center; font-size: 14.5px; }}
.mr-empty b {{ display: block; color: {INK}; font-size: 16px; margin-bottom: 4px; }}
.mr-note {{ font-size: 12.5px; color: {FAINT}; line-height: 1.6; }}
.mr-note a {{ color: {MUTED}; }}
</style>
"""


def hero(rule_count: int, version: str, checker=None) -> str:
    proof = ""
    if checker is not None:
        text, ptype = SAMPLE_COPY
        fs = checker.check(text, ptype)
        out, pos = "", 0
        for f in fs:
            c = GRADE[f.grade][0]
            tag = "s" if f.grade == "red" else "u"
            out += escape(text[pos:f.start]) + f'<{tag} style="--c:{c}">{escape(text[f.start:f.end])}</{tag}>'
            pos = f.end
        out += escape(text[pos:])
        notes = "".join(
            f'<div class="note" style="--c:{GRADE[f.grade][0]}"><span>{escape(f.phrase)}</span><span>{escape(f.label)}'
            + (f' · 대신 <em>{escape(f.alt.split(" / ")[0])}</em>' if not f.alt.startswith("(") else "") + "</span></div>"
            for f in sorted(fs, key=lambda x: x.grade != "red"))
        proof = (f'<div class="mr-proof"><div class="cap">이렇게 찾아드려요 (일반 화장품 상세페이지 예시)</div>'
                 f'<div class="copy">{out}</div><div class="notes">{notes}</div></div>')
    return f"""<div class="mr-hero"><div>
<div class="mr-brand"><span class="mr-mark"></span>문구레이더</div>
<div class="mr-title">상세페이지 광고 문구,<br>식약처에 걸리기 전에 찾아드려요</div>
<p class="mr-lead">화장품, 식품, 건강기능식품 상품 목록을 올리면 위반 소지가 있는 표현을 찾아 위험한 상품부터 보여주고, 고칠 문장과 처벌 수위를 엑셀로 정리해 드려요.</p>
<div class="mr-facts"><span><b>{rule_count}</b>개 규칙</span><span><b>25</b>건 단속 발표 분석</span><span>{escape(version)} 기준</span></div>
</div>{proof}</div>"""


def kpis(ov: dict) -> str:
    total = ov["total"] or 1
    cells = [f'<div class="mr-num"><div class="k">점검한 상품</div><div class="v">{ov["total"]}<small>개</small></div>'
             f'<div class="d">위험도 순으로 정렬했어요</div></div>']
    for t in ("높음", "중간", "확인", "양호"):
        c, _, desc = TIER[t]
        n = ov["tiers"][t]
        cells.append(f'<div class="mr-num{" zero" if not n else ""}"><div class="k"><span class="mr-sq" style="--c:{c}"></span>{t}</div>'
                     f'<div class="v">{n}</div><div class="d">{desc}</div></div>')
    dist = "".join(f'<span style="width:{ov["tiers"][t] / total * 100:.2f}%;background:{TIER[t][0]}" '
                   f'title="{t} {ov["tiers"][t]}개"></span>' for t in TIER if ov["tiers"].get(t))
    return f'<div class="mr-board"><div class="mr-nums">{"".join(cells)}</div><div class="mr-dist">{dist}</div></div>'


def common_bars(ov: dict) -> str:
    if not ov["common"]:
        return ""
    top = ov["total"] or 1
    rows = "".join(f'<div class="mr-bar"><span class="t">{escape(name)}</span>'
                   f'<span class="track"><span class="fill" style="display:block;width:{n / top * 100:.1f}%"></span></span>'
                   f'<span class="n">{n}개 상품</span></div>' for name, n in ov["common"])
    return f'<div class="mr-bars">{rows}</div>'


def tier_pill(tier: str) -> str:
    c = TIER[tier][0]
    return f'<span class="mr-tier" style="--c:{c}"><span class="mr-sq" style="--c:{c}"></span>{tier}</span>'


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
    risk = f'<div class="mr-box mr-risk"><b>이대로 두면</b>{escape(f.penalty)}</div>' if f.penalty else ""
    checks = ""
    if f.checks:
        checks = '<div class="mr-checks"><b>쓰기 전에 확인할 것</b>' + "".join(
            f"<div>{escape(x)}</div>" for x in f.checks) + "</div>"
    return f"""<div class="mr-card" style="--c:{c};--b:{b}">
<div class="head"><span class="mr-grade">{escape(f.grade_name)}</span><span class="label">{escape(f.label)}</span></div>
<div class="phrase">{"".join(f"<u>{escape(p)}</u>" for p in phrases)}</div>
<div class="why">{escape(f.why)}</div>
<div class="mr-two">{risk}<div class="mr-box mr-alt"><b>대신 이렇게</b>{escape(f.alt)}</div></div>
{checks}
<div class="mr-foot">정확한 용어: {escape(f.term)}<br>관련 기준: {escape(f.law)}<br>출처: {escape(f.source)}</div>
</div>"""


def highlighted(text: str, findings) -> str:
    out, pos = "", 0
    for f in findings:
        out += escape(text[pos:f.start]) + f'<u style="--c:{GRADE[f.grade][0]}">{escape(text[f.start:f.end])}</u>'
        pos = f.end
    out += escape(text[pos:])
    return f'<div class="mr-text">{out}</div>'


def one_summary(counts: dict) -> str:
    items = [("red", "꼭 고치기", "기준에 금지로 적힌 표현"), ("amber", "확인 필요", "맥락에 따라 위반"),
             ("blue", "자료 챙기기", "증명 자료가 있어야 써요")]
    cells = "".join(f'<div class="mr-num{" zero" if not counts[g] else ""}"><div class="k"><span class="mr-sq" style="--c:{GRADE[g][0]}">'
                    f'</span>{name}</div><div class="v">{counts[g]}</div><div class="d">{d}</div></div>' for g, name, d in items)
    return f'<div class="mr-board"><div class="mr-nums" style="grid-template-columns:repeat(3,1fr)">{cells}</div></div>'


def empty(title: str, text: str = "") -> str:
    return f'<div class="mr-empty"><b>{escape(title)}</b>{escape(text)}</div>'


def product_head(i: int, r) -> str:
    c = r.counts
    pen = f" · 최대 {penalty_text(r.max_penalty)}" if r.max_penalty else ""
    return (f'<div class="mr-phead"><span class="n">{escape(r.name)}</span>{tier_pill(r.tier)}'
            f'<span class="m">꼭 고치기 {c["red"]}, 확인 필요 {c["amber"]}, 자료 챙기기 {c["blue"]}{pen}</span></div>')


def product_title(i: int, r) -> str:
    """접기 상자 제목 (일반 글자만 들어감)."""
    c = r.counts
    return f"{i}. {r.name}  ·  위험도 {r.tier}  ·  꼭 고치기 {c['red']} · 확인 필요 {c['amber']} · 자료 챙기기 {c['blue']}"


def penalty_short(p) -> str:
    """표에 넣는 짧은 처벌 표기: 징역 10년, 벌금 1억"""
    if not p:
        return "-"
    years, won = p
    money = f"{won // 100_000_000}억" if won >= 100_000_000 else f"{won // 10_000:,}만"
    return f"징역 {years}년 / 벌금 {money}"


def rank_table(results, type_names: dict, height: int = 430) -> str:
    """위험 순서 표. 긴 글은 칸 안에서 줄바꿈되고, 표가 높이를 넘으면 상자 안에서 스크롤된다."""
    def num(n):
        return f'<td class="num{" z" if not n else ""}">{n}</td>'
    rows = []
    for i, r in enumerate(results, 1):
        c = r.counts
        rows.append(f"<tr><td class='num'>{i}</td><td class='nm'><b>{escape(r.name)}</b></td>"
                    f"<td class='nw'>{escape(type_names.get(r.product_type, '-'))}</td><td>{tier_pill(r.tier)}</td>"
                    f"{num(c['red'])}{num(c['amber'])}{num(c['blue'])}"
                    f"<td style='white-space:nowrap'>{escape(penalty_short(r.max_penalty))}</td>"
                    f"<td class='memo'>{escape(r.error)}</td></tr>")
    head = ("<tr><th>순위</th><th>상품명</th><th>제품 종류</th><th>위험도</th><th class='num'>꼭 고치기</th>"
            "<th class='num'>확인 필요</th><th class='num'>자료 챙기기</th><th>최대 처벌</th><th>메모</th></tr>")
    return (f'<div class="mr-table-wrap" style="--h:{height}px"><table class="mr-table"><thead>{head}</thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')
