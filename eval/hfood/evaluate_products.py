"""신고번호·제품명 대조 평가: 실제 신고 제품(식품안전나라 C003 표본 2,996개)으로 잰다.

 1. 번호로 찾기 — 원고 끝에 '품목제조신고번호 …'를 붙였을 때
    · 그 제품이 신고한 문구 → '신고하지 않은 기능성'(꼭 고치기)이 나오면 오탐
    · 그 제품이 신고하지 않은 기능의 '~에 도움' 문구(다른 제품 것) → 꼭 고치기·확인 필요로 알리면 적발
 2. 상품명으로 찾기 — 쇼핑몰식으로 꾸민 상품명('[무료배송] 제품명 60정 2박스')에서 맞는 제품을 찾는 비율, 다른 제품을 고른 비율
원재료 목록은 넣지 않는다(원료 기준 대조와 섞이지 않게). 사용: python eval/hfood/evaluate_products.py
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from precheck.engine import Checker  # noqa: E402
from precheck.hfood import find_funcs  # noqa: E402

ck = Checker()
kb = ck.hfood
P = ck.products
parents = {f["id"]: [p for p in f["parent"].split(",") if p] for f in kb["funcs"]}
rows = json.loads((ROOT / "data/hfood/raw/C003_sample.json").read_text(encoding="utf-8"))
rnd = random.Random(3)


def tags(t):
    s = set()
    for f in find_funcs(t, kb):
        s.add(f["id"]); s.update(parents[f["id"]])
    return s


prods = [P.items[P.by_no[re.sub(r"\D", "", r["PRDLST_REPORT_NO"])]] for r in rows if re.sub(r"\D", "", r["PRDLST_REPORT_NO"]) in P.by_no]
pool = [c for p in prods for c in p["c"] if "도움" in c]
own_n = own_fp = oth_n = oth_red = oth_any = 0
for p in prods:
    tail = f". 품목제조신고번호 {p['no']}"
    for c in p["c"][:3]:
        own_n += 1
        own_fp += any(f.rule_id == "H6" for f in ck.check(c + tail, "hfood"))
    ptags = set().union(*(tags(c) for c in p["c"])) if p["c"] else set()
    for _ in range(50):
        c = rnd.choice(pool)
        if tags(c) and not (tags(c) & ptags):
            break
    else:
        continue
    oth_n += 1
    fs = ck.check(c + tail, "hfood")
    oth_red += any(f.rule_id == "H6" for f in fs)
    oth_any += any(f.rule_id in ("H6", "H7") for f in fs)

DECOR = [("[무료배송] ", " 60정 2박스"), ("", " 30포"), ("(1+1) ", ""), ("", " 3개월분 선물세트"), ("", "")]
name_ok = name_wrong = name_none = 0
wrong_ex, none_ex = [], []
for p in prods:
    a, b = rnd.choice(DECOR)
    hit = P.find("", a + p["n"] + b)
    if not hit:
        name_none += 1
        if len(none_ex) < 15:
            none_ex.append(a + p["n"] + b)
    elif any(P.items[i]["no"] == p["no"] for i in hit):
        name_ok += 1
    else:
        name_wrong += 1
        if len(wrong_ex) < 15:
            wrong_ex.append((a + p["n"] + b, [P.items[i]["n"] for i in hit][:2]))
n = len(prods)
res = {"products": n, "own_claims": own_n, "own_fp": own_fp, "own_fp_rate": own_fp / own_n,
       "other_claims": oth_n, "other_red": oth_red, "other_red_rate": oth_red / oth_n, "other_any_rate": oth_any / oth_n,
       "name_ok_rate": name_ok / n, "name_wrong_rate": name_wrong / n, "name_none_rate": name_none / n}
(ROOT / "eval/hfood/results_products.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
if "-v" in sys.argv:
    print("다른 제품을 고름:", *wrong_ex, sep="\n  ")
    print("못 찾음:", *none_ex, sep="\n  ")
