"""가상 상세페이지 이미지 3장과 정답표 만들기 (이미지·긴 페이지 실험용).

각 블록: (스타일, 문장, 라벨, 핵심 표현, 분류)
라벨: violation / conditional / allowed. 핵심 표현은 채점 때 이 문장을 찾았는지 판단하는 기준.
출력: eval/page_test/pages/*.html, *.png, truth.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "page_test"
(OUT / "pages").mkdir(parents=True, exist_ok=True)
V, C, A = "violation", "conditional", "allowed"

PAGES = {
 "p1_cream": {"type": "cos", "title": "수분 크림 (일반 화장품)", "theme": ("#e8f1f4", "#1d4f63"), "blocks": [
   ("hero", "피부과 전문의가 직접 개발한 수분 크림", V, "전문의가 직접 개발", "C3"),
   ("lead", "건조한 피부에 수분을 채워 하루 종일 촉촉하게", A, "", ""),
   ("banner", "피부 속 깊숙이 침투하는 마이크로 캡슐 공법", V, "피부 속 깊숙이 침투", "C4"),
   ("body", "끈적임 없이 산뜻하게 마무리되는 젤 크림 제형", A, "", ""),
   ("point", "염증과 트러블을 진정시켜 줘요", V, "염증", "C1"),
   ("body", "은은한 허브 향으로 기분까지 편안하게", A, "", ""),
   ("point", "아토피 피부도 안심하고 쓰세요", V, "아토피", "C1"),
   ("banner", "주름 개선과 미백을 한 번에", V, "주름 개선", "C2"),
   ("badge", "인체적용시험 완료 · 4주 사용 후 피부 수분량 32% 증가", C, "32% 증가", "CP"),
   ("body", "피부 노폐물까지 깨끗하게 정돈해요", A, "", ""),
   ("small", "스테로이드 성분 무첨가", V, "스테로이드", "C4"),
   ("howto", "세안 후 적당량을 덜어 얼굴 전체에 부드럽게 펴 발라 주세요", A, "", ""),
   ("fine", "사용 중 이상이 있는 경우 사용을 중지하고 전문의와 상담하세요", A, "", ""),
 ]},
 "p2_tea": {"type": "food", "title": "레몬 생강차 (일반 식품)", "theme": ("#fbf1e1", "#7a3e0b"), "blocks": [
   ("hero", "환절기 감기 예방에 좋은 생강차", V, "감기 예방", "F1"),
   ("lead", "국내산 생강과 레몬을 그대로 담았어요", A, "", ""),
   ("banner", "면역력 강화로 겨울을 건강하게", V, "면역력 강화", "F3"),
   ("howto", "따뜻한 물 200ml에 1포를 넣고 저어 드세요", A, "", ""),
   ("point", "붓기 빠지는 아침 루틴", V, "붓기 빠지는", "F4"),
   ("review", "먹는 날마다 몸이 가벼워졌어요 — 구매자 김○○님", V, "몸이 가벼워졌어요", "F5"),
   ("body", "개별 스틱 포장으로 언제 어디서나 간편하게", A, "", ""),
   ("point", "목에 좋은 따뜻한 차 한 잔", V, "목에 좋은", "F4"),
   ("banner", "천연 해독 디톡스 차", V, "디톡스", "F3"),
   ("body", "아이부터 어른까지 온 가족이 즐기는 맛", A, "", ""),
   ("badge", "약사 추천 차", V, "약사 추천", "F6"),
   ("fine", "직사광선을 피해 서늘한 곳에 보관하세요", A, "", ""),
 ]},
 "p3_omega": {"type": "hfood", "title": "오메가3 (건강기능식품)", "theme": ("#e9f0fb", "#173f7a"), "blocks": [
   ("hero", "혈중 중성지질 개선·혈행 개선에 도움을 줄 수 있음", C, "혈행 개선", "HF"),
   ("banner", "심혈관 질환 예방", V, "심혈관 질환 예방", "F1"),
   ("lead", "알약이 작아 삼키기 편해요", A, "", ""),
   ("point", "콜레스테롤 약 대신 오메가3", V, "약 대신", "F2"),
   ("howto", "1일 1회 1캡슐, 물과 함께 섭취하세요", A, "", ""),
   ("point", "기억력 향상과 치매 예방까지", V, "치매 예방", "F1"),
   ("review", "먹고 나서 혈압 수치가 정상이 됐어요 — 후기", V, "혈압 수치가 정상", "F5"),
   ("body", "어류 원료의 비린 맛을 줄였어요", A, "", ""),
   ("fine", "임산부, 수유부는 섭취 전 전문가와 상담하세요", A, "", ""),
   ("fine", "건강기능식품 표시·광고 심의필", A, "", ""),
 ]},
}

CSS = """*{box-sizing:border-box}body{margin:0;width:860px;font-family:'Noto Sans CJK KR',sans-serif;background:%(bg)s;color:#222}
.sec{padding:60px 56px;text-align:center}
.hero{font-size:46px;font-weight:900;line-height:1.3;color:%(fg)s;padding:120px 56px 70px}
.lead{font-size:28px;color:#444}
.banner{background:%(fg)s;color:#fff;font-size:34px;font-weight:800;padding:48px 56px}
.body{font-size:24px;color:#555;background:#fff}
.point{font-size:32px;font-weight:700;color:%(fg)s}
.point::before{content:'POINT';display:block;font-size:16px;letter-spacing:.3em;color:#999;margin-bottom:10px}
.badge{display:flex;justify-content:center;padding:50px}.badge span{display:inline-block;border:3px solid %(fg)s;border-radius:999px;padding:22px 34px;font-size:22px;font-weight:700;color:%(fg)s;background:#fff}
.review{background:#fff;font-size:22px;color:#333;font-style:italic}.review span{display:inline-block;border-left:6px solid %(fg)s;padding:14px 22px;text-align:left}
.small{font-size:17px;color:#777}
.howto{font-size:22px;color:#333;background:#fff}.howto::before{content:'HOW TO USE';display:block;font-size:15px;letter-spacing:.3em;color:#aaa;margin-bottom:8px}
.fine{font-size:14px;color:#8a8a8a;text-align:left;padding:18px 56px;background:#f7f7f7}
.photo{height:260px;margin:0 56px;border-radius:16px;background:linear-gradient(135deg,%(fg)s22,%(fg)s55)}"""

truth = {}
for pid, p in PAGES.items():
    bg, fg = p["theme"]
    parts = []
    for i, (style, text, label, key, cat) in enumerate(p["blocks"]):
        inner = f"<span>{text}</span>" if style in ("badge", "review") else text
        parts.append(f'<div class="sec {style}">{inner}</div>')
        if i in (1, 5):
            parts.append('<div class="photo"></div>')
    html = f"<!doctype html><meta charset=utf-8><style>{CSS % {'bg': bg, 'fg': fg}}</style>" + "".join(parts)
    (OUT / "pages" / f"{pid}.html").write_text(html, encoding="utf-8")
    truth[pid] = {"type": p["type"], "title": p["title"],
                  "blocks": [{"text": t, "label": l, "key": k, "cat": c} for (_, t, l, k, c) in p["blocks"]]}
(OUT / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
print({k: sum(b["label"] == "violation" for b in v["blocks"]) for k, v in truth.items()}, "violations per page")
