"""문구레이더 — 상세페이지 광고 일괄 점검 (Streamlit 화면).

실행: streamlit run app.py
이미지 글자 읽기: tesseract(packages.txt)가 있으면 무료로, .streamlit/secrets.toml 에 ANTHROPIC_API_KEY 가 있으면 AI로 읽는다.
화면 조각(HTML·CSS)은 precheck/ui.py 에 있다.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from precheck import Checker, check_products, overview, read_table, summarize, ui
from precheck.report import TYPE_NAME, build_report

st.set_page_config(page_title="문구레이더 — 상세페이지 광고 일괄 점검", page_icon="📡", layout="wide")
SAMPLE = Path(__file__).parent / "examples" / "sample_products.csv"
TIER_ICON = {"높음": "🔴", "중간": "🟠", "확인": "🔵", "양호": "🟢", "오류": "⚪"}
REPO = "https://github.com/ojg1476-tech/precheck-ai"
PANEL = 430  # 표·카드 목록 상자 높이(px). 넘치면 상자 안에서 스크롤


@st.cache_resource
def get_checker():
    return Checker()


@st.cache_resource
def free_ocr_ready() -> bool:
    from precheck import ocr
    return ocr.free_available()


def api_key() -> str:
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        return ""


def html(s: str):
    st.markdown(s, unsafe_allow_html=True)


def section(title: str):
    html(f'<div class="mr-section">{title}</div>')


ck = get_checker()
html(ui.CSS)
html(ui.hero(len(ck.rules), ck.version))

tab_batch, tab_one, tab_about = st.tabs(["📋 여러 상품 한 번에", "✏️ 한 개 검사", "📊 기준과 성능"])

# ── 여러 상품 한 번에 ─────────────────────────────────────
with tab_batch:
    c_up, c_img = st.columns([3.2, 1], vertical_alignment="bottom")
    with c_up:
        c_lbl, c_try, c_dl = st.columns([2.2, 1, 1], vertical_alignment="center", gap="small")
        with c_lbl:
            html('<div class="mr-label">상품 목록 파일 (CSV · 엑셀)</div>')
        with c_try:
            use_sample = st.button("예시로 해보기", type="tertiary", use_container_width=True,
                                   help="파일 없이 예시 상품 11개로 결과를 미리 볼 수 있어요.")
        with c_dl:
            st.download_button("⬇️ 입력 양식 받기", SAMPLE.read_bytes(), file_name="문구레이더_입력양식.csv",
                               mime="text/csv", use_container_width=True)
        up = st.file_uploader("상품 목록 파일 (CSV · 엑셀)", type=["csv", "xlsx"], key="list_upload",
                              label_visibility="collapsed")
    with c_img:
        with st.popover("🖼️ 이미지로 검사", use_container_width=True):
            key = api_key()
            free = free_ocr_ready()
            if not key and not free:
                st.info("이미지 속 글자 읽기를 지금 쓸 수 없어요. 상세페이지 글을 목록 파일의 ‘상세문구’ 칸에 넣어 주세요.")
            else:
                from precheck import ocr
                if key:
                    st.caption("AI로 이미지 속 글자를 읽어요 (사용료가 들어요).")
                else:
                    st.caption("무료 글자 읽기 프로그램(Tesseract)으로 읽어요. 시험용 상세페이지에서 글자의 89%를 맞게 읽었어요. "
                               "사진 위에 얹힌 글씨는 놓칠 수 있으니, 결과의 ‘읽어 낸 글’ 탭에서 꼭 확인하세요.")
                img_type = st.selectbox("제품 종류", list(ck.product_types), format_func=ck.product_types.get)
                imgs = st.file_uploader("상세페이지 이미지 (한 파일 = 한 상품, 파일 이름이 상품명이 돼요)",
                                        type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
                if imgs:
                    if key:
                        est = ocr.estimate([f.getvalue() for f in imgs])
                        st.caption(f"예상 AI 사용료: 약 ${est['usd']:.3f} (상품 {len(imgs)}개)")
                    if st.button("이미지 글자 읽고 검사하기", type="primary"):
                        items, cost, texts = [], 0.0, {}
                        bar = st.progress(0.0, text="이미지를 읽는 중이에요")
                        for i, f in enumerate(imgs, 1):
                            name = Path(f.name).stem
                            try:
                                if key:
                                    r = ocr.read_text([f.getvalue()], key)
                                    cost += r.usd
                                    text = r.text
                                else:
                                    text = ocr.read_text_free([f.getvalue()])
                                texts[name] = text
                                items.append({"row": i, "name": name, "type": img_type, "text": text})
                            except Exception as e:  # 한 상품이 실패해도 나머지는 계속
                                items.append({"row": i, "name": name, "type": img_type, "text": "", "_err": str(e)})
                            bar.progress(i / len(imgs), text=f"{i}/{len(imgs)} 읽음")
                        st.session_state["results"] = check_products(items, ck)
                        st.session_state["ocr_texts"] = texts
                        st.session_state["source"] = (f"이미지 {len(imgs)}장 · AI 사용료 약 ${cost:.3f}" if key
                                                      else f"이미지 {len(imgs)}장 · 무료 글자 읽기")

    html('<div class="mr-hint">필수 칸: <b>상품명 · 제품종류 · 상세문구</b> (칸 이름은 첫 줄에) · 다른 칸이 더 있어도, 순서가 달라도 '
         '괜찮아요 · 제품종류는 일반 화장품 / 기능성 화장품 / 일반 식품 / 건강기능식품</div>')

    data_name = None
    if up is not None:
        data, data_name = up.getvalue(), up.name
    elif use_sample:
        data, data_name = SAMPLE.read_bytes(), "예시 목록"
    if data_name:
        try:
            st.session_state["results"] = check_products(read_table(data, data_name if up is not None else SAMPLE.name), ck)
            st.session_state["source"] = data_name
            st.session_state.pop("ocr_texts", None)
        except ValueError as e:
            st.error(f"파일을 읽지 못했어요. {e}")

    results = st.session_state.get("results")
    if not results:
        html(ui.empty("📂", "상품 목록 파일을 올리면 위험한 상품부터 보여드려요."))
    else:
        ov = overview(results, ck)
        top, dl = st.columns([3, 1], vertical_alignment="center")
        with top:
            section(f"점검 결과 · {st.session_state.get('source', '')} · 상품 {ov['total']}개")
        with dl:
            st.download_button("⬇️ 엑셀 리포트 받기", build_report(results, ck), type="primary", use_container_width=True,
                               file_name="문구레이더_점검리포트.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        ocr_texts = st.session_state.get("ocr_texts")
        names = ["요약", "위험 순서", "상품별 자세히"] + (["읽어 낸 글"] if ocr_texts else [])
        t_sum, t_rank, t_detail, *t_ocr = st.tabs(names)
        if t_ocr:
            with t_ocr[0]:
                st.caption("이미지에서 읽어 낸 글이에요. 잘못 읽은 곳이 있으면 글을 고쳐 목록 파일로 다시 검사하세요.")
                with st.container(height=PANEL - 40):
                    for name, text in ocr_texts.items():
                        st.markdown(f"**{name}**")
                        st.text(text or "(읽은 글 없음)")

        with t_sum:
            c1, c2 = st.columns([1.1, 1], gap="large")
            with c1:
                html(ui.kpis(ov))
            with c2:
                if ov["common"]:
                    html('<div class="mr-sub">여러 상품에서 반복된 문제</div>' + ui.common_bars(ov))
                else:
                    html(ui.empty("✅", "여러 상품에서 반복된 문제는 없어요."))

        with t_rank:
            html(ui.rank_table(results, TYPE_NAME, PANEL))

        with t_detail:
            flagged = [(i, r) for i, r in enumerate(results, 1) if r.findings]
            if not flagged:
                html(ui.empty("✅", "걸린 표현이 있는 상품이 없어요."))
            else:
                left, right = st.columns([1, 2.2], gap="medium")
                with left:
                    with st.container(height=PANEL, border=True):
                        pick = st.radio("상품", [i for i, _ in flagged], label_visibility="collapsed",
                                        format_func=lambda i: f"{TIER_ICON[results[i - 1].tier]} {i}. {results[i - 1].name}")
                r = results[pick - 1]
                with right:
                    with st.container(height=PANEL, border=False):
                        html(ui.product_head(pick, r) + ui.finding_cards(r.findings))

# ── 한 개 검사 ───────────────────────────────────────────
with tab_one:
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        ptype = st.radio("제품 종류", list(ck.product_types), format_func=ck.product_types.get, horizontal=True)
        text = st.text_area("상세페이지 문구", height=PANEL - 90,
                            placeholder="예: 피부 재생 크림! 7일 만에 주름 개선, 피부과 추천 1위")
        go = st.button("검사하기", type="primary", use_container_width=True)
    with right:
        if go and text.strip():
            fs = ck.check(text, ptype)
            html(ui.one_summary(summarize(fs)))
            if fs:
                o1, o2 = st.tabs(["고칠 곳", "문구에서 찾은 곳"])
                with o1:
                    with st.container(height=PANEL - 120, border=False):
                        html(ui.finding_cards(fs))
                with o2:
                    with st.container(height=PANEL - 120, border=False):
                        html(ui.highlighted(text, fs))
            else:
                html(ui.empty("✅", "기본 검사에서 걸린 표현은 없어요."))
        else:
            html(ui.empty("✏️", "왼쪽에 문구를 붙여 넣고 ‘검사하기’를 눌러 주세요."))

# ── 기준과 성능 ─────────────────────────────────────────
with tab_about:
    section("이 검사기는 어떻게 만들었나요")
    st.markdown(
        "- **식약처 단속 데이터에서 출발했어요.** 점검 발표 25건(2021~2026)을 분석해 많이 걸리는 유형과 새로 떠오른 표현을 "
        "규칙에 넣었어요. 식품은 ‘건강기능식품처럼’ 광고(2025년 적발의 51%), 화장품은 ‘약처럼’ 광고(69%)가 가장 많아요.\n"
        "- **처벌 정보는 법령 원문에서만 가져와요.** 화장품법·식품표시광고법과 시행규칙 별표를 직접 확인해 표로 만들었어요.\n"
        "- **규칙을 만들 때 보지 않은 실제 적발 문구로 성능을 쟀어요.**")
    perf = pd.DataFrame([
        {"시험": "시험 세트 3 (2024~2026 새 적발 발표 6건)", "위반을 찾은 비율": "67.9% (19/28)", "멀쩡한 문장을 잘못 잡은 비율": "0% (0/17)"},
        {"시험": "시험 세트 2 (v3 작업 전 고정)", "위반을 찾은 비율": "59.3% (16/27)", "멀쩡한 문장을 잘못 잡은 비율": "0% (0/14)"},
        {"시험": "이미지 글자 읽기 (무료, 시험 페이지 3장)", "위반을 찾은 비율": "10/11", "멀쩡한 문장을 잘못 잡은 비율": "0"},
    ])
    st.dataframe(perf, hide_index=True, use_container_width=True)
    section("ChatGPT에 물어보는 것과 무엇이 다른가요")
    st.markdown(
        "- **상품 전체를 한 번에, 위험한 순서로 봐요.** 한 개씩 묻지 않아도 돼요.\n"
        "- **써도 된다는 말로 끝내지 않아요.** 건강기능식품 인정 문구처럼 조건이 붙는 표현은 쓰기 전에 확인할 서류와 절차를 알려드려요.\n"
        "- **처벌 정보는 AI가 지어내지 않아요.** 법령 원문에서 확인한 표로 안내하고, 근거 조문과 출처를 같이 보여드려요.\n"
        "- **같은 문구에는 늘 같은 결과가 나와요.** ‘대신 이렇게’ 문구는 정해진 표에서 나오고, 같은 기준으로 다시 검사해 통과한 표현이에요.")
    st.caption("비교 실험(실제 적발 문구 등 46개)에서 기준 없이 AI에 물었을 때는 확인이 필요한 건강기능식품 문구 5개를 모두 "
               "‘허용’으로만 답했고 처벌 정보는 25개 중 3개가 원문과 달랐어요. 위반 문구를 찾아낸 비율은 AI가 더 높았어요(100% 대 59%). "
               f"[실험 기록과 코드 보기]({REPO}/blob/main/eval/history.md)")

st.divider()
html('<div class="mr-note">이 도구는 광고 문구 점검을 돕는 참고 자료이며 법률 판단이 아니에요. 실제 광고 전에는 대한화장품협회 '
     '광고자문이나 한국건강기능식품협회 표시·광고 심의를 받는 것이 가장 확실해요. · '
     f'<a href="{REPO}" target="_blank">GitHub</a></div>')
