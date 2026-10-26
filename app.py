"""상세페이지 문구 검수기 — Streamlit 화면.

실행: streamlit run app.py
"""
from html import escape

import streamlit as st

from precheck import Checker, summarize

st.set_page_config(page_title="상세페이지 문구 검수기", page_icon="✅", layout="wide")


@st.cache_resource
def get_checker():
    return Checker()


ck = get_checker()
COLOR = {"red": "#c62828", "amber": "#b26a00", "blue": "#1f5fbf"}

st.title("상세페이지 문구 검수기")
st.caption(f"화장품·식품 광고 문구를 식약처 기준으로 미리 점검해요. 규칙 {len(ck.rules)}개 · 기준일 {ck.version}")

left, right = st.columns([1, 1.2], gap="large")
with left:
    ptype = st.radio("제품 종류", list(ck.product_types), format_func=ck.product_types.get, horizontal=True)
    text = st.text_area("상세페이지 문구", height=320,
                        placeholder="예: 피부 재생 크림! 7일 만에 주름 개선, 피부과 추천 1위")
    go = st.button("검사하기", type="primary", use_container_width=True)

with right:
    if go and text.strip():
        fs = ck.check(text, ptype)
        c = summarize(fs)
        m1, m2, m3 = st.columns(3)
        m1.metric("꼭 고치세요", c["red"])
        m2.metric("한번 확인하세요", c["amber"])
        m3.metric("증명 자료를 챙기세요", c["blue"])

        # 원문에 표시
        html, pos = "", 0
        for f in fs:
            html += escape(text[pos:f.start])
            html += (f'<mark style="background:{COLOR[f.grade]}22;border-bottom:2px solid {COLOR[f.grade]};'
                     f'padding:0 2px">{escape(text[f.start:f.end])}</mark>')
            pos = f.end
        html += escape(text[pos:])
        st.markdown(f'<div style="line-height:1.9;white-space:pre-wrap">{html}</div>', unsafe_allow_html=True)

        for f in sorted(fs, key=lambda x: ({"red": 0, "amber": 1, "blue": 2}[x.grade], x.start)):
            with st.container(border=True):
                st.markdown(f'<span style="color:{COLOR[f.grade]};font-weight:700">{f.grade_name}</span> · {f.label}',
                            unsafe_allow_html=True)
                st.markdown(f"**찾은 표현** “{f.phrase}”")
                st.write(f.why)
                if f.penalty:
                    st.warning(f"**이대로 두면** {f.penalty}")
                st.success(f"**대신 이렇게** {f.alt}")
                st.caption(f"정확한 용어 · {f.term}  \n관련 기준 · {f.law}  \n출처 · {f.source}")
        if not fs:
            st.info("기본 검사에서 걸린 표현은 없어요.")
    else:
        st.info("왼쪽에 문구를 붙여 넣고 ‘검사하기’를 눌러 주세요.")

st.divider()
st.caption("이 도구는 광고 문구 점검을 돕는 참고 자료이며 법률 판단이 아니에요. "
           "실제 광고 전에는 대한화장품협회 광고자문이나 한국건강기능식품협회 표시·광고 심의를 받는 것이 가장 확실해요.")
