"""두 번째 시험 세트(data/test2.csv) — 규칙 v3를 만들기 전에 확정한다.

기존 eval_set.csv에 없는 문구만 넣었다. 규칙을 고칠 때 이 파일은 보지 않는다.
라벨 규칙은 build_eval_set.py와 같다 (violation / allowed / conditional).
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
U = {
    "c2607": "https://www.k-health.com/news/articleView.html?idxno=100282",
    "c2607b": "https://www.etoday.co.kr/news/view/2606966",
    "f2506": "https://www.sedaily.com/article/14077089",
    "f2305": "https://www.sedaily.com/article/13684717",
    "h2505": "https://www.newspim.com/news/view/20250502000739",
}
rows = []


def add(ptype, label, cat, src, url, *texts):
    for t in texts:
        rows.append(dict(product_type=ptype, label=label, category=cat, text=t, source=src, source_url=url))


V, A, C = "violation", "allowed", "conditional"
# 화장품 — 식약처·대한화장품협회 합동점검 178건 (2026.7)
add("cos", V, "의약품 오인", "식약처 적발(2026.7)", U["c2607b"],
    "질염 예방", "가려움 완화", "질건조증 개선", "관절염 치료", "염증·근육 이완", "피로 회복", "통증 완화",
    "여드름 치료", "소염 효과")
add("cos", V, "전문가 추천 오인", "식약처 적발(2026.7)", U["c2607"], "산부인과 전문의 개발")
add("cos", V, "범위 일탈", "식약처 적발(2026.7)", U["c2607"], "바르는 질 유산균")
add("fcos", V, "심사 효능과 다른 광고", "식약처 적발(2026.7)", U["c2607b"], "여드름 예방")
# 식품 — 합동점검 236건 (2025.6)
add("food", V, "건강기능식품 오인", "식약처 적발(2025.6)", U["f2506"], "체지방 감소")
add("food", V, "질병 예방·치료", "식약처 적발(2025.6)", U["f2506"], "변비개선도움")
add("food", V, "거짓·과장", "식약처 적발(2025.6)", U["f2506"], "긴장완화", "붓기차")
add("food", V, "원재료 효능 오인", "식약처 적발(2025.6)", U["f2506"], "알부민 효능·효과")
add("food", V, "의약품 오인", "식약처 적발(2025.6)", U["f2506"], "비염한약비염", "한약")
add("food", V, "체험기 기만", "식약처 적발(2025.6)", U["f2506"], "제품을 먹고 키가 컸다")
# 식품 — 185건 (2023.5)
add("food", V, "질병 예방·치료", "식약처 적발(2023.5)", U["f2305"], "감기차")
add("food", V, "의약품 오인", "식약처 적발(2023.5)", U["f2305"], "피로회복제", "철분약")
add("food", V, "거짓·과장", "식약처 적발(2023.5)", U["f2305"], "눈에 좋은")
add("food", V, "체험기 기만", "식약처 적발(2023.5)", U["f2305"], "마신 날은 좀 덜 피로한 것 같아요")
# 건강기능식품 — 104건 (2025.5, 기사 설명 속 예시)
add("hfood", V, "질병 예방·치료", "식약처 적발(2025.5)", U["h2505"], "골다공증 예방")
add("hfood", V, "인정되지 않은 기능성", "식약처 적발(2025.5)", U["h2505"], "기관지 보호")
# 건강기능식품 — 고시형 원료의 인정 기능성 문구 (자료 확인 알림이 맞음)
add("hfood", C, "인정 기능성 문구", "건강기능식품 기능성 원료 인정 문구 형식", "",
    "노화로 인해 감소될 수 있는 황반색소밀도를 유지하여 눈 건강에 도움을 줄 수 있음",
    "유산균 증식 및 유해균 억제에 도움을 줄 수 있음", "배변활동 원활에 도움을 줄 수 있음",
    "면역력 증진에 도움을 줄 수 있음", "혈중 중성지질 개선에 도움을 줄 수 있음")
# 평범한 상세페이지 문구 (새로 쓴 합성 문구, 오탐 측정용)
add("cos", A, "평범한 문구", "synthetic", "",
    "끈적임 없는 가벼운 제형이에요", "메이크업 전 피부결을 매끈하게 정돈해요", "자기 전 듬뿍 바르면 아침까지 촉촉해요",
    "피부 노폐물을 깨끗하게 씻어내요", "건조한 겨울철에 꼭 챙기는 크림", "100ml 대용량에 튜브형 용기", "상처가 있는 부위에는 사용하지 마세요")
add("food", A, "평범한 문구", "synthetic", "",
    "갓 볶은 원두의 깊은 향", "아이 간식으로 좋아요", "저녁 식사에 곁들이기 좋은 반찬", "제주산 감귤로 만든 상큼한 주스",
    "물에 타서 마시는 간편한 분말", "명절 선물로 좋은 한과 세트", "위에 견과류를 뿌려 드시면 더 고소해요")

old = {(r["product_type"], r["text"]) for r in csv.DictReader(open(ROOT / "data" / "eval_set.csv", encoding="utf-8"))}
dup = [r["text"] for r in rows if (r["product_type"], r["text"]) in old]
assert not dup, f"기존 정답표와 겹침: {dup}"
for i, r in enumerate(rows, 1):
    r["id"] = f"T{i:03d}"
    r["split"] = "test2"
with open(ROOT / "data" / "test2.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["id", "split", "product_type", "label", "category", "text", "source", "source_url"])
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows")
