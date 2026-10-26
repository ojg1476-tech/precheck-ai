"""이미지 읽기 시험용 페이지 3장 (전처리 개선 작업 전에 고정).

기존 6장(개발용)과 문장·모양을 다르게: 어두운 배경 흰 글씨, 색 박스, 그라데이션 사진 위 글씨, 작은 표 글씨, 둥근 말풍선 후기.
출력: eval/page_test/pages/test_*.html (+ shoot_pages.js로 png), truth_test.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "page_test"
V, A = "violation", "allowed"
PAGES = {
 "test_t1_serum": {"type": "cos", "title": "앰플 (일반 화장품)", "c": ("#111827", "#f9fafb", "#d4a373"), "blocks": [
   ("dark", "바르는 순간 피부재생이 시작돼요", V), ("box", "가볍게 스며드는 워터 제형", A),
   ("photo", "보톡스 화장품으로 불리는 앰플", V), ("bubble", "아침마다 손이 가는 순한 향이에요", A),
   ("dark", "모발굵기 개선까지 한 번에", V), ("table", "용량 30ml · 제조국 대한민국 · 사용기한 개봉 후 12개월", A),
   ("box", "염증개선 완화 효과", V), ("tiny", "눈에 들어갔을 때에는 즉시 씻어 내세요", A)]},
 "test_t2_granola": {"type": "food", "title": "그래놀라 (일반 식품)", "c": ("#3f2a14", "#fff7ed", "#ea580c"), "blocks": [
   ("photo", "당뇨에 좋은 아침 그래놀라", V), ("box", "통귀리와 견과류를 듬뿍 넣었어요", A),
   ("dark", "갱년기 영양제 대신 매일 한 그릇", V), ("bubble", "아이 간식으로도 잘 먹어요", A),
   ("box", "항산화 영양제 못지않은 베리 토핑", V), ("table", "내용량 500g · 원재료 귀리, 아몬드, 꿀 · 알레르기 땅콩 함유", A),
   ("dark", "피로회복 영양제처럼 든든하게", V), ("tiny", "개봉 후 밀봉하여 서늘한 곳에 보관하세요", A)]},
 "test_t3_tea": {"type": "food", "title": "보리차 (일반 식품)", "c": ("#14532d", "#f0fdf4", "#16a34a"), "blocks": [
   ("dark", "혈행개선 영양제 부럽지 않은 차", V), ("photo", "볶은 보리의 고소한 향", A),
   ("box", "당뇨개선제 대신 하루 두 잔", V), ("bubble", "물 대신 마시기 좋아요", A),
   ("box", "염증치료를 돕는 한 잔", V), ("table", "티백 1.5g × 30개 · 국내산 보리 100%", A),
   ("dark", "간 건강이 걱정되는 분께", V), ("tiny", "뜨거운 물에 3분간 우려 드세요", A)]},
}
CSS = """*{box-sizing:border-box}body{margin:0;width:900px;font-family:'Noto Sans CJK KR',sans-serif;background:%(bg)s}
.sec{padding:80px 50px;text-align:center}
.dark{background:%(dk)s;color:#fff;font-size:38px;font-weight:700;letter-spacing:-.02em}
.box{padding:60px 90px}.box div{background:%(ac)s;color:#fff;font-size:30px;font-weight:600;padding:34px;border-radius:24px}
.photo{height:900px;display:flex;align-items:flex-end;justify-content:center;padding-bottom:120px;color:#fff;font-size:36px;font-weight:800;
  text-shadow:0 2px 6px #0008;background:radial-gradient(circle at 70%% 30%%,%(ac)s 0,transparent 45%%),linear-gradient(200deg,%(dk)s,%(ac)s 60%%,%(bg)s)}
.bubble div{display:inline-block;background:#fff;border:2px solid %(ac)s;border-radius:40px 40px 40px 4px;padding:26px 40px;font-size:24px;color:#444}
.table div{display:inline-block;border-top:2px solid #999;border-bottom:2px solid #999;padding:16px 10px;font-size:16px;color:#666}
.tiny{font-size:13px;color:#b0b0b0;padding:24px 50px;text-align:left}
.gap{height:700px;background:repeating-linear-gradient(45deg,%(ac)s22 0 20px,transparent 20px 40px),%(bg)s}"""
truth = {}
for pid, p in PAGES.items():
    dk, bg, ac = p["c"]
    parts = []
    for i, (st, text, label) in enumerate(p["blocks"]):
        inner = f"<div>{text}</div>" if st in ("box", "bubble", "table") else text
        parts.append(f'<div class="sec {st}">{inner}</div>')
        if i in (1, 4):
            parts.append('<div class="gap"></div>')
    html = f"<!doctype html><meta charset=utf-8><style>{CSS % {'bg': bg, 'dk': dk, 'ac': ac}}</style>" + "".join(parts)
    (OUT / "pages" / f"{pid}.html").write_text(html, encoding="utf-8")
    truth[pid] = {"type": p["type"], "title": p["title"], "blocks": [{"text": t, "label": l} for (_, t, l) in p["blocks"]]}
(OUT / "truth_test.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok")
