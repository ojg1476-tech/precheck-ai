"""문구레이더 — 상세페이지 광고 일괄 점검 (Streamlit 화면).

실행: streamlit run app.py
이미지 글자 읽기를 켜려면 .streamlit/secrets.toml 에 ANTHROPIC_API_KEY = "..." 를 넣는다.
"""
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from precheck import Checker, check_products, overview, read_table, summarize
from precheck.batch import penalty_text
from precheck.report import TYPE_NAME, build_report

st.set_page_config(page_title="문구레이더 — 상세페이지 광고 일괄 점검", page_icon="📡", layout="wide")
SAMPLE = Path(__file__).parent / "examples" / "sample_products.csv"
COLOR = {"red": "#c62828", "amber": "#b26a00", "blue": "#1f5fbf"}
TIER_ICON = {"높음": "🔴", "중간": "🟠", "확인": "🔵", "양호": "🟢", "오류": "⚪"}


@st.cache_resource
def get_checker():
    return Checker()


def api_key() -> str:
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


def finding_card(f):
    with st.container(border=True):
        st.markdown(f'<span style="color:{COLOR[f.grade]};font-weight:700">{f.grade_name}</span> · {f.label}',
                    unsafe_allow_html=True)
        st.markdown(f"**찾은 표현** “{f.phrase}”")
        st.write(f.why)
        if f.penalty:
            st.warning(f"**이대로 두면** {f.penalty}")
        st.success(f"**대신 이렇게** {f.alt}")
        if f.checks:
            st.markdown("**쓰기 전에 확인할 것**  \n" + "  \n".join(f"☐ {c}" for c in f.checks))
        st.caption(f"정확한 용어 · {f.term}  \n관련 기준 · {f.law}  \n출처 · {f.source}")


ck = get_checker()
st.title("문구레이더")
st.caption(f"상품 상세페이지 광고 문구를 한 번에 점검해 위험한 상품부터 알려드려요. 규칙 {len(ck.rules)}개 · 기준일 {ck.version}")

tab_batch, tab_one = st.tabs(["여러 상품 한 번에", "한 개 검사"])

# ── 여러 상품 한 번에 ─────────────────────────────────────
with tab_batch:
    st.markdown("상품 목록 파일(CSV·엑셀)을 올리면 모든 상품을 검사해서 **위험한 상품 순서**로 보여드리고, "
                "상품별로 고칠 곳과 확인할 것을 정리한 **엑셀 리포트**를 만들어 드려요.")
    a, b = st.columns([2, 1])
    with a:
        up = st.file_uploader("상품 목록 (첫 줄: 상품명 · 제품종류 · 상세문구)", type=["csv", "xlsx"])
    with b:
        st.download_button("예시 목록 받기 (CSV)", SAMPLE.read_bytes(), file_name="문구레이더_예시목록.csv", mime="text/csv",
                           use_container_width=True)
        use_sample = st.button("예시 목록으로 해보기", use_container_width=True)
        st.caption("제품종류: 일반 화장품 · 기능성 화장품 · 일반 식품 · 건강기능식품")

    with st.expander("상세페이지가 이미지인가요?"):
        key = api_key()
        if not key:
            st.info("이미지 속 글자 읽기는 AI 사용료가 들어서 아직 켜 두지 않았어요. 지금은 상세페이지 글을 목록 파일의 "
                    "‘상세문구’ 칸에 넣어 주세요.")
        else:
            from precheck import ocr
            img_type = st.selectbox("제품 종류", list(ck.product_types), format_func=ck.product_types.get)
            imgs = st.file_uploader("상세페이지 이미지 (한 파일 = 한 상품, 파일 이름이 상품명이 돼요)",
                                    type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
            if imgs:
                est = ocr.estimate([f.getvalue() for f in imgs])
                st.caption(f"예상 AI 사용료: 약 ${est['usd']:.3f} (상품 {len(imgs)}개)")
                if st.button("이미지 글자 읽고 검사하기", type="primary"):
                    items, cost = [], 0.0
                    bar = st.progress(0.0, text="이미지를 읽는 중이에요")
                    for i, f in enumerate(imgs, 1):
                        try:
                            r = ocr.read_text([f.getvalue()], key)
                            cost += r.usd
                            items.append({"row": i, "name": Path(f.name).stem, "type": img_type, "text": r.text})
                        except Exception as e:  # 한 상품이 실패해도 나머지는 계속
                            items.append({"row": i, "name": Path(f.name).stem, "type": img_type, "text": "", "_err": str(e)})
                        bar.progress(i / len(imgs), text=f"{i}/{len(imgs)} 읽음")
                    st.session_state["results"] = check_products(items, ck)
                    st.session_state["source"] = f"이미지 {len(imgs)}장 (AI 사용료 약 ${cost:.3f})"

    data_name = None
    if up is not None:
        data, data_name = up.getvalue(), up.name
    elif use_sample:
        data, data_name = SAMPLE.read_bytes(), SAMPLE.name
    if data_name:
        try:
            st.session_state["results"] = check_products(read_table(data, data_name), ck)
            st.session_state["source"] = data_name
        except ValueError as e:
            st.error(str(e))

    results = st.session_state.get("results")
    if results:
        ov = overview(results, ck)
        st.divider()
        st.subheader(f"점검 결과 · {st.session_state.get('source', '')}")
        cols = st.columns(5)
        cols[0].metric("점검한 상품", ov["total"])
        for col, t in zip(cols[1:], ["높음", "중간", "확인", "양호"]):
            col.metric(f"{TIER_ICON[t]} 위험도 {t}", ov["tiers"][t])
        if ov["common"]:
            st.markdown("**여러 상품에서 반복된 문제** · " + " · ".join(f"{n} ({c}개 상품)" for n, c in ov["common"][:3]))

        table = pd.DataFrame([{
            "순위": i, "상품명": r.name, "제품 종류": TYPE_NAME.get(r.product_type, "-"),
            "위험도": f"{TIER_ICON[r.tier]} {r.tier}", "가장 무거운 형사처벌(최대)": penalty_text(r.max_penalty),
            "꼭 고치기": r.counts["red"], "확인 필요": r.counts["amber"], "자료 챙기기": r.counts["blue"], "메모": r.error,
        } for i, r in enumerate(results, 1)])
        st.dataframe(table, hide_index=True, use_container_width=True)

        st.download_button("엑셀 리포트 받기", build_report(results, ck), type="primary",
                           file_name="문구레이더_점검리포트.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.markdown("#### 상품별 자세히")
        for i, r in enumerate(results, 1):
            if not r.findings:
                continue
            with st.expander(f"{i}. {TIER_ICON[r.tier]} {r.name} — 꼭 고치기 {r.counts['red']} · 확인 필요 {r.counts['amber']} · "
                             f"자료 챙기기 {r.counts['blue']}"):
                for f in sorted(r.findings, key=lambda x: ({"red": 0, "amber": 1, "blue": 2}[x.grade], x.start)):
                    finding_card(f)

# ── 한 개 검사 ───────────────────────────────────────────
with tab_one:
    left, right = st.columns([1, 1.2], gap="large")
    with left:
        ptype = st.radio("제품 종류", list(ck.product_types), format_func=ck.product_types.get, horizontal=True)
        text = st.text_area("상세페이지 문구", height=320, placeholder="예: 피부 재생 크림! 7일 만에 주름 개선, 피부과 추천 1위")
        go = st.button("검사하기", type="primary", use_container_width=True)
    with right:
        if go and text.strip():
            fs = ck.check(text, ptype)
            c = summarize(fs)
            m1, m2, m3 = st.columns(3)
            m1.metric("꼭 고치세요", c["red"])
            m2.metric("한번 확인하세요", c["amber"])
            m3.metric("증명 자료를 챙기세요", c["blue"])
            html, pos = "", 0
            for f in fs:
                html += escape(text[pos:f.start])
                html += (f'<mark style="background:{COLOR[f.grade]}22;border-bottom:2px solid {COLOR[f.grade]};'
                         f'padding:0 2px">{escape(text[f.start:f.end])}</mark>')
                pos = f.end
            html += escape(text[pos:])
            st.markdown(f'<div style="line-height:1.9;white-space:pre-wrap">{html}</div>', unsafe_allow_html=True)
            for f in sorted(fs, key=lambda x: ({"red": 0, "amber": 1, "blue": 2}[x.grade], x.start)):
                finding_card(f)
            if not fs:
                st.info("기본 검사에서 걸린 표현은 없어요.")
        else:
            st.info("왼쪽에 문구를 붙여 넣고 ‘검사하기’를 눌러 주세요.")

st.divider()
with st.expander("ChatGPT에 물어보는 것과 무엇이 다른가요?"):
    st.markdown(
        "- **상품 전체를 한 번에, 위험한 순서로 봐요.** 한 개씩 묻지 않아도 돼요.\n"
        "- **써도 된다는 말로 끝내지 않아요.** 건강기능식품 인정 문구처럼 조건이 붙는 표현은 쓰기 전에 확인할 서류와 절차를 알려드려요.\n"
        "- **처벌 정보는 AI가 지어내지 않아요.** 법령 원문에서 확인한 표로 안내하고, 근거 조문과 출처를 같이 보여드려요.\n"
        "- **같은 문구에는 늘 같은 결과가 나와요.** ‘대신 이렇게’ 문구는 정해진 표에서 나오고, 같은 기준으로 다시 검사해 통과한 표현이에요.")
    st.caption("2026년 10월 비교 실험(실제 적발 문구 등 46개)에서, 기준 없이 AI에 물었을 때는 확인이 필요한 건강기능식품 문구 "
               "5개를 모두 ‘허용’으로만 답했고 처벌 정보는 25개 중 3개가 원문과 달랐어요. 위반 문구를 찾아낸 비율은 AI가 100%, "
               "이 앱의 규칙 검사가 59%로 AI가 더 높았어요. 문구 수가 적은 실험이라 참고용이에요. "
               "[실험 기록 보기](https://github.com/ojg1476-tech/precheck-ai/blob/main/eval/history.md)")
st.caption("이 도구는 광고 문구 점검을 돕는 참고 자료이며 법률 판단이 아니에요. "
           "실제 광고 전에는 대한화장품협회 광고자문이나 한국건강기능식품협회 표시·광고 심의를 받는 것이 가장 확실해요.")
