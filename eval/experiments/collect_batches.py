"""규칙 v5 후보를 고정(커밋 b60cd6d)한 뒤 모은 실제 적발 문구 묶음.
기존 데이터(개발용·시험 2~4·적발 문구 108개)와 겹치는 문구는 뺀다. 결과: data/test5_batches.csv"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U = {
 "cos22": "https://cosinkorea.com/mobile/article.html?no=46940",
 "kid23": "https://www.newsis.com/view/NISX20230316_0002228624",
 "cos24": "https://v.daum.net/v/20241224101112626",
 "mix24": "https://www.todayebnews.com/news/articleView.html?idxno=7327",
 "q10_24": "https://www.newsis.com/view/NISX20240927_0002902223",
 "cos25a": "https://www.nocutnews.co.kr/news/6327536",
 "cos25b": "https://www.sisaweek.com/news/articleView.html?idxno=225665",
 "live25": "https://m.dailypharm.com/user/news/4925",
 "f2606a": "https://biz.sbs.co.kr/amp/article/20000314622",
 "f2606b": "https://www.foodtoday.or.kr/news/article.html?no=205551",
 "f2609": "https://biz.sbs.co.kr/amp/article/20000333938",
}
B = [  # (묶음, 제품 종류, 문구, 출처 키)
 ("A_2022-23", "cos", "의사가 추천하는 화장품", "cos22"), ("A_2022-23", "cos", "아토피", "cos22"),
 ("A_2022-23", "food", "어린이 키성장", "kid23"), ("A_2022-23", "food", "아이키", "kid23"),
 ("A_2022-23", "food", "키성장 영양제, 키크는 영양제", "kid23"), ("A_2022-23", "hfood", "어린이 키크는", "kid23"),
 ("A_2022-23", "food", "소아비만 및 성조숙증을 예방", "kid23"), ("A_2022-23", "food", "변비, 감기 등 아이들에게 좋다", "kid23"),
 ("A_2022-23", "food", "저희딸 96센치에서 지금 무려 104.8센치 됐거든요", "kid23"),
 ("B_2024", "cos", "지방분해", "cos24"), ("B_2024", "cos", "셀룰라이트 제거", "cos24"), ("B_2024", "cos", "체지방 감소", "cos24"),
 ("B_2024", "cos", "체중감량", "cos24"), ("B_2024", "cos", "노폐물 배출", "cos24"), ("B_2024", "cos", "부종에 도움", "cos24"),
 ("B_2024", "cos", "스테로이드 성분 없음", "cos24"), ("B_2024", "cos", "피부재생, 염증 개선", "mix24"),
 ("B_2024", "cos", "피부과 전문의 추천 제품", "mix24"), ("B_2024", "food", "갱년기영양제", "mix24"), ("B_2024", "food", "피로회복", "mix24"),
 ("B_2024", "food", "심혈관 질환, 고혈압, 당뇨병, 암 등의 질환을 앓고 있는 경우에도 보충이 도움이 될 수 있다", "q10_24"),
 ("C_2025", "cos", "세포재생, 지방세포 증식", "cos25a"), ("C_2025", "cos", "모발성장촉진", "cos25a"), ("C_2025", "cos", "탈모방지", "cos25a"),
 ("C_2025", "cos", "00의사 추천", "cos25b"), ("C_2025", "cos", "병원 전용 화장품", "cos25b"), ("C_2025", "cos", "병원추천", "cos25b"),
 ("C_2025", "cos", "피부 염증 감소", "cos25b"), ("C_2025", "cos", "주름개선", "cos25b"),
 ("C_2025", "food", "난임", "live25"), ("C_2025", "food", "염증치료", "live25"), ("C_2025", "cos", "필러크림", "live25"),
 ("C_2025", "cos", "피부과전문의가 개발한 제품", "live25"),
 ("D_2026", "food", "비염 완화", "f2606a"), ("D_2026", "food", "면역력 증진", "f2606a"), ("D_2026", "food", "감기예방", "f2606a"),
 ("D_2026", "food", "두드러기·건선·아토피 등 관리", "f2606a"), ("D_2026", "food", "면역력 피로 개선", "f2606a"),
 ("D_2026", "food", "혈당관리", "f2606a"), ("D_2026", "food", "코막힘 감기", "f2606a"), ("D_2026", "food", "목에 좋은 차", "f2606a"),
 ("D_2026", "food", "속 편한", "f2609"), ("D_2026", "food", "소화가 잘되는", "f2609"),
 ("D_2026", "food", "면역력 강화", "f2606b"), ("D_2026", "food", "역류성식도염", "f2606b"), ("D_2026", "food", "다이어트약", "f2606b"),
 ("D_2026", "food", "간장약", "f2606b"), ("D_2026", "food", "피부탄력", "f2606b"), ("D_2026", "food", "붓기관리", "f2606b"),
]

norm = lambda s: s.replace(" ", "").replace(",", "").replace("·", "")
seen = set()
for f in ["eval_set.csv", "test2.csv", "test3.csv", "test4.csv"]:
    seen |= {norm(r["text"]) for r in csv.DictReader(open(ROOT / "data" / f, encoding="utf-8"))}
seen |= {norm(r["text"]) for r in csv.DictReader(open(ROOT / "data/enforcement/phrases.csv", encoding="utf-8"))}
rows, dup = [], 0
for b, t, x, k in B:
    if norm(x) in seen:
        dup += 1
        continue
    seen.add(norm(x))
    rows.append({"id": f"V{len(rows) + 1:03d}", "split": b, "product_type": t, "label": "violation", "category": "", "text": x,
                 "source": "식약처 적발 보도", "source_url": U[k]})
w = csv.DictWriter(open(ROOT / "data/test5_batches.csv", "w", newline="", encoding="utf-8"), fieldnames=list(rows[0]))
w.writeheader(); w.writerows(rows)
from collections import Counter
print("겹쳐서 뺀 문구", dup, "| 묶음별", dict(Counter(r["split"] for r in rows)))
