"""시험 세트 7: 규칙 v6 후보를 고정(커밋 1bfcf81)한 뒤 모은 실제 적발 문구. 기존 데이터와 겹치는 것은 뺀다."""
import csv
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
U = {"col20": "https://www.cncnews.co.kr/mobile/article.html?no=5372", "mkt21": "https://medigatenews.com/news/1038170911",
     "nutri17": "https://www.dailypharm.com/user/news/102510", "cos25": "https://www.nocutnews.co.kr/news/6381268",
     "hf25": "https://biz.sbs.co.kr/amp/article/20000239077", "diet15": "https://www.medicaldaily.co.kr/news/7540"}
V = [("food", "밤 사이 촉촉하게 채워 생기있고", "col20"), ("food", "얼굴이 푸석푸석한 분", "col20"),
     ("food", "피부 탄력, 피부 보습을 지키고 싶은신 분", "col20"), ("food", "콜라겐은 피부지탱 역할, 피부의 수분을 유지하고 단단하게 하는 역할", "col20"),
     ("food", "셀럽들이 몰래 먹는 탱탱피부 비밀", "col20"),
     ("food", "체중감량", "mkt21"), ("food", "피로회복", "mkt21"), ("food", "면역력 강화", "mkt21"), ("food", "항산화", "mkt21"), ("food", "피부개선", "mkt21"),
     ("food", "붓기차", "mkt21"), ("food", "모유촉진", "mkt21"), ("food", "골다공증", "mkt21"), ("food", "생리통", "mkt21"), ("food", "변비", "mkt21"),
     ("food", "질염", "mkt21"), ("food", "부종", "mkt21"), ("food", "다이어트약", "mkt21"), ("food", "이뇨제", "mkt21"), ("food", "식욕억제제", "mkt21"),
     ("hfood", "100% 천연원료비타민", "nutri17"), ("hfood", "모유에서 찾은 한국인 맞춤 유산균", "nutri17"), ("hfood", "無화학첨가물", "nutri17"),
     ("hfood", "화학적 첨가물을 0.1%도 사용하지 않았습니다", "nutri17"),
     ("cos", "소염작용", "cos25"), ("cos", "염증완화에 도움", "cos25"), ("cos", "피부(세포) 재생", "cos25"), ("cos", "진피층 침투", "cos25"),
     ("cos", "피부 내 근막 성분 전달", "cos25"), ("food", "체지방감소·변비개선", "hf25"),
     ("food", "대한민국 모델들의 몸매 관리 비법", "diet15"), ("food", "뛰어난 지방 분해력", "diet15"), ("food", "하체 지방 감소효과", "diet15"),
     ("food", "뛰어난 지방 분해", "diet15"), ("food", "8일 토털 프로그램", "diet15")]
norm = lambda s: s.replace(" ", "").replace(",", "").replace("·", "")
seen = set()
for f in ["eval_set.csv", "test2.csv", "test3.csv", "test4.csv", "test5_batches.csv", "test6.csv"]:
    seen |= {norm(r["text"]) for r in csv.DictReader(open(ROOT / "data" / f, encoding="utf-8"))}
seen |= {norm(r["text"]) for r in csv.DictReader(open(ROOT / "data/enforcement/phrases.csv", encoding="utf-8"))}
rows, dup = [], []
for t, x, k in V:
    if norm(x) in seen: dup.append(x); continue
    seen.add(norm(x))
    rows.append({"id": f"T{len(rows) + 1:03d}", "split": "test7", "product_type": t, "label": "violation", "category": "", "text": x,
                 "source": "식약처 적발 보도", "source_url": U[k]})
w = csv.DictWriter(open(ROOT / "data/test7.csv", "w", newline="", encoding="utf-8"), fieldnames=list(rows[0]))
w.writeheader(); w.writerows(rows)
print("겹쳐서 뺌", len(dup), "| 위반", len(rows))
