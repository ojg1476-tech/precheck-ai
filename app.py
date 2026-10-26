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
                if f.checks:
                    st.markdown("**쓰기 전에 확인할 것**  \n" + "  \n".join(f"☐ {c}" for c in f.checks))
                st.caption(f"정확한 용어 · {f.term}  \n관련 기준 · {f.law}  \n출처 · {f.source}")
        if not fs:
            st.info("기본 검사에서 걸린 표현은 없어요.")
    else:
        st.info("왼쪽에 문구를 붙여 넣고 ‘검사하기’를 눌러 주세요.")

st.divider()
with st.expander("ChatGPT에 물어보는 것과 무엇이 다른가요?"):
    st.markdown(
        "- **써도 된다는 말로 끝내지 않아요.** 건강기능식품 인정 문구처럼 조건이 붙는 표현은, "
        "쓰기 전에 확인할 서류와 절차를 함께 알려드려요.\n"
        "- **처벌 정보는 AI가 지어내지 않아요.** 법령 원문에서 확인한 표로 안내하고, 근거 조문과 출처를 같이 보여드려요.\n"
        "- **같은 문구에는 늘 같은 결과가 나와요.** ‘대신 이렇게’ 문구는 정해진 표에서 나오고, "
        "모두 같은 기준으로 다시 검사해 통과한 표현이에요.")
    st.caption("2026년 10월 비교 실험(실제 적발 문구 등 46개)에서, 기준 없이 AI에 물었을 때는 확인이 필요한 건강기능식품 문구 "
               "5개를 모두 ‘허용’으로만 답했고 처벌 정보는 25개 중 3개가 원문과 달랐어요. 위반 문구를 찾아낸 비율은 AI가 100%, "
               "이 앱의 규칙 검사가 59%로 AI가 더 높았어요. 문구 수가 적은 실험이라 참고용이에요. "
               "[실험 기록 보기](https://github.com/ojg1476-tech/precheck-ai/blob/main/eval/history.md)")
st.caption("이 도구는 광고 문구 점검을 돕는 참고 자료이며 법률 판단이 아니에요. "
           "실제 광고 전에는 대한화장품협회 광고자문이나 한국건강기능식품협회 표시·광고 심의를 받는 것이 가장 확실해요.")
