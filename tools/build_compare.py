"""비교 실험 페이지(그냥 AI vs 규칙 vs 규칙+기준표 AI) HTML 생성.

data/test2.csv + tools/rules_web.js 를 페이지에 넣는다.
출력: 스크래치 경로 인자 (기본 ./compare.html)
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "compare.html"

# 정답 처벌(형사처벌 최대치). 확인된 것만 넣고 불확실하면 None
PEN_TRUTH = {
    ("cos", None): (1, 10_000_000), ("fcos", None): (1, 10_000_000),
    ("food", "질병 예방·치료"): (10, 100_000_000), ("food", "의약품 오인"): (10, 100_000_000),
    ("food", "건강기능식품 오인"): (10, 100_000_000),
    ("food", "거짓·과장"): (5, 50_000_000), ("food", "체험기 기만"): (5, 50_000_000),
    ("hfood", "질병 예방·치료"): (10, 100_000_000),
}
rows = []
for r in csv.DictReader(open(ROOT / "data" / "test2.csv", encoding="utf-8")):
    t = None
    if r["label"] == "violation":
        t = PEN_TRUTH.get((r["product_type"], None)) or PEN_TRUTH.get((r["product_type"], r["category"]))
    rows.append({"id": r["id"], "type": r["product_type"], "text": r["text"], "label": r["label"],
                 "category": r["category"], "source": r["source"], "pen": t})

rules_js = (ROOT / "tools" / "rules_web.js").read_text(encoding="utf-8")
html = (ROOT / "tools" / "compare_template.html").read_text(encoding="utf-8")
html = html.replace("/*__RULES__*/", rules_js).replace("/*__DATA__*/[]", json.dumps(rows, ensure_ascii=False))
out.write_text(html, encoding="utf-8")
print(len(rows), "rows →", out)
