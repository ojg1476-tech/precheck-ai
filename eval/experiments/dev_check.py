"""후보 규칙을 이미 본 데이터 전체(개발용)와 리뷰 오탐으로 점검."""
import csv, re, sys, random
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT))
from precheck import Checker
cand = sys.argv[1]; reviews = sys.argv[2] if len(sys.argv) > 2 else None
v4, vc = Checker(), Checker(str(ROOT / cand))
st = lambda ck, x, t: [f.rule_id for f in ck.check(x, t) if f.grade in ("red", "amber")]
files = ["eval_set.csv", "test2.csv", "test3.csv", "test4.csv", "test5_batches.csv", "test6.csv"]
TV = TA = 0
for f in files:
    rows = list(csv.DictReader(open(ROOT / "data" / f, encoding="utf-8")))
    V = [r for r in rows if r["label"] == "violation"]; A = [r for r in rows if r["label"] == "allowed"]
    a0 = sum(bool(st(v4, r["text"], r["product_type"])) for r in V); a1 = sum(bool(st(vc, r["text"], r["product_type"])) for r in V)
    f0 = [r["text"] for r in A if st(vc, r["text"], r["product_type"])]
    print(f"{f:20} 위반 {a0}->{a1}/{len(V)}  허용 오탐 {len(f0)}/{len(A)} {f0[:4]}")
if reviews:
    COS = re.compile(r"크림|로션|토너|세럼|에센스|앰플|선크림|샴푸|화장품|스킨|클렌징|마스크팩"); FOOD = re.compile(r"맛있|먹|마셔|마시|차가|젤리|간식|과자|음료|영양제|즙|분말|스틱")
    new, by = [], Counter()
    for line in open(reviews, encoding="utf-8"):
        s = line.rstrip("\n").split("\t", 1)[-1]
        t = "cos" if COS.search(s) else "food" if FOOD.search(s) else None
        if not t or st(v4, s, t): continue
        b = st(vc, s, t)
        if b: new.append((t, s, b)); by.update(set(b))
    print("리뷰 새로 표시", len(new), dict(by))
    random.seed(1)
    for t, s, b in random.sample(new, min(40, len(new))): print(" ", t, b, "|", s[:85])
