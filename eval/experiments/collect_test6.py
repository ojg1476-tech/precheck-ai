"""시험 세트 6: 규칙 v5b 후보를 고정(커밋 7271690)한 뒤 모은 실제 적발 문구. 기존 데이터와 겹치는 것은 뺀다."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
U = {"exam23": "https://dailypharm.com/user/news/22787", "sleep23": "https://m.dailypharm.com/user/news/32071",
     "botox25": "https://m.dailypharm.com/user/news/7712", "hair25": "https://dailypharm.com/user/news/6743",
     "brow25": "https://www.kpinews.kr/newsView/1065573908398647", "infl23": "https://www.dailypharm.com/user/news/29091",
     "dm24": "https://dailypharm.com/user/news/16649"}
V = [("food", "기억력 개선", "exam23"), ("food", "집중력 강화", "exam23"), ("food", "뇌 영양제", "exam23"),
     ("hfood", "집중력 영양제", "exam23"), ("hfood", "기억력 개선 영양제", "exam23"), ("hfood", "두뇌 건강", "exam23"),
     ("food", "불면증 완화·수면유도제", "sleep23"), ("cos", "바르는 보톡스·필러 시술", "botox25"),
     ("food", "탈모 예방", "hair25"), ("food", "탈모에 좋은", "hair25"), ("food", "탈모 개선", "hair25"), ("food", "머리카락 나는 약", "hair25"),
     ("fcos", "눈썹염색", "brow25"), ("fcos", "흰 눈썹 염색약", "brow25"), ("fcos", "눈썹 탈색제", "brow25"),
     ("fcos", "눈썹 인중 염색약", "brow25"), ("fcos", "속눈썹을 염색하는 제품", "brow25"), ("fcos", "머리색이랑 똑같은 눈썹을 얻었어요", "brow25"),
     ("food", "벌써 체중이 2kg 빠졌어요", "infl23"), ("food", "Before & After", "infl23"), ("food", "습진", "infl23"),
     ("food", "아토피 발생 완화효과", "infl23"), ("food", "탈모 방지", "infl23"), ("food", "성인병 예방", "infl23"),
     ("cos", "이마가 봉긋하게 채워져요", "infl23"), ("cos", "여드름 흉터가 없어졌어요", "infl23"), ("cos", "피부 재생까지 케어하네요", "infl23")]
A = [("hfood", "식후 혈당상승 억제에 도움을 줄 수 있음", "dm24")]   # 식약처가 인정한 건강기능식품 기능성 문구 (기사에 적법 예시로 인용)
norm = lambda s: s.replace(" ", "").replace(",", "").replace("·", "")
seen = set()
for f in ["eval_set.csv", "test2.csv", "test3.csv", "test4.csv", "test5_batches.csv"]:
    seen |= {norm(r["text"]) for r in csv.DictReader(open(ROOT / "data" / f, encoding="utf-8"))}
seen |= {norm(r["text"]) for r in csv.DictReader(open(ROOT / "data/enforcement/phrases.csv", encoding="utf-8"))}
rows, dup = [], []
for lab, items in (("violation", V), ("allowed", A)):
    for t, x, k in items:
        if norm(x) in seen: dup.append(x); continue
        seen.add(norm(x))
        rows.append({"id": f"S{len(rows) + 1:03d}", "split": "test6", "product_type": t, "label": lab, "category": "", "text": x,
                     "source": "식약처 적발 보도" if lab == "violation" else "식약처 인정 기능성 문구(보도 인용)", "source_url": U[k]})
w = csv.DictWriter(open(ROOT / "data/test6.csv", "w", newline="", encoding="utf-8"), fieldnames=list(rows[0]))
w.writeheader(); w.writerows(rows)
print("겹쳐서 뺌:", dup)
print("위반", sum(r["label"] == "violation" for r in rows), "허용", sum(r["label"] == "allowed" for r in rows))
