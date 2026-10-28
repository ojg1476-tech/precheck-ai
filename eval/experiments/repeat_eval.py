"""규칙 v5 후보 반복 실험: 서로 다른 데이터 묶음에서 v4와 비교한다.

1. 위반 문구 묶음: 시험 세트 4, 고정 이후 모은 2022~23 / 2024~26 묶음
2. 묶음을 합친 처음 보는 문구 전체에 대한 부트스트랩 95% 구간
3. 오탐 스트레스: 네이버 쇼핑 리뷰(공개 코퍼스, bab2min/corpus)에서 화장품·식품 리뷰를 골라
   새 규칙 때문에 새로 표시되는 문장이 얼마나 되는지

    python eval/experiments/repeat_eval.py --reviews <naver_shopping.txt 경로>
"""
import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from precheck import Checker  # noqa: E402

CAND = ROOT / "eval/experiments/rules_v5_candidate.json"


def strong(ck, text, t):
    return [f for f in ck.check(text, t) if f.grade in ("red", "amber")]


def rate(ck, rows):
    v = [r for r in rows if r["label"] == "violation"]
    a = [r for r in rows if r["label"] == "allowed"]
    hv = [bool(strong(ck, r["text"], r["product_type"])) for r in v]
    ha = [bool(strong(ck, r["text"], r["product_type"])) for r in a]
    return hv, ha


def boot(x0, x1, n=5000, seed=7):
    rnd, k, d = random.Random(seed), len(x0), []
    for _ in range(n):
        idx = [rnd.randrange(k) for _ in range(k)]
        d.append((sum(x1[i] for i in idx) - sum(x0[i] for i in idx)) / k)
    d.sort()
    return d[int(n * .025)], d[int(n * .975)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews")
    a = ap.parse_args()
    v4, v5 = Checker(), Checker(str(CAND))
    sets = {"시험 세트 4": list(csv.DictReader(open(ROOT / "data/test4.csv", encoding="utf-8")))}
    for r in csv.DictReader(open(ROOT / "data/test5_batches.csv", encoding="utf-8")):
        sets.setdefault("묶음 " + ("2022~23" if r["split"].startswith("A") else "2024~26"), []).append(r)
    print("| 데이터 | 위반 문구 수 | v4 탐지 | v5 후보 탐지 | 허용 문장 오탐 (v4 → v5) |")
    print("| --- | --- | --- | --- | --- |")
    pool0, pool1 = [], []
    for name, rows in sets.items():
        h0, a0 = rate(v4, rows)
        h1, a1 = rate(v5, rows)
        pool0 += h0; pool1 += h1
        fp = f"{sum(a0)}/{len(a0)} → {sum(a1)}/{len(a1)}" if a0 else "-"
        print(f"| {name} | {len(h0)} | {sum(h0) / len(h0) * 100:.1f}% ({sum(h0)}) | {sum(h1) / len(h1) * 100:.1f}% ({sum(h1)}) | {fp} |")
    lo, hi = boot(pool0, pool1)
    print(f"| **합계 (처음 보는 문구)** | {len(pool0)} | {sum(pool0) / len(pool0) * 100:.1f}% | {sum(pool1) / len(pool1) * 100:.1f}% | |")
    print(f"\n탐지율 차이 95% 부트스트랩 구간: {lo * 100:+.1f}%p ~ {hi * 100:+.1f}%p")
    # 개발용 데이터 회귀 확인
    dev = list(csv.DictReader(open(ROOT / "data/eval_set.csv", encoding="utf-8")))
    h0, a0 = rate(v4, dev); h1, a1 = rate(v5, dev)
    print(f"개발용 데이터: 탐지 {sum(h0)}/{len(h0)} → {sum(h1)}/{len(h1)}, 오탐 {sum(a0)}/{len(a0)} → {sum(a1)}/{len(a1)}")

    if a.reviews:
        COS = re.compile(r"크림|로션|토너|세럼|에센스|앰플|선크림|샴푸|화장품|스킨|클렌징|마스크팩")
        FOOD = re.compile(r"맛있|먹|마셔|마시|차가|젤리|간식|과자|음료|영양제|즙|분말|스틱")
        revs = []
        for line in open(a.reviews, encoding="utf-8"):
            s = line.rstrip("\n").split("\t", 1)[-1]
            if COS.search(s): revs.append(("cos", s))
            elif FOOD.search(s): revs.append(("food", s))
        print(f"\n리뷰 {len(revs)}개 (화장품 {sum(t == 'cos' for t, _ in revs)}, 식품 {sum(t == 'food' for t, _ in revs)})")
        new, by = [], Counter()
        for t, s in revs:
            f0, f1 = strong(v4, s, t), strong(v5, s, t)
            if not f0 and f1:
                new.append((t, s, [f.rule_id for f in f1]))
                by.update({f.rule_id for f in f1})
        print(f"새 규칙 때문에 새로 표시된 리뷰: {len(new)}개 ({len(new) / len(revs) * 100:.2f}%) | 규칙별 {dict(by)}")
        rnd = random.Random(3)
        out = ROOT / "eval/experiments/review_new_hits.json"
        out.write_text(json.dumps(rnd.sample(new, min(60, len(new))), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"검토용 표본 {min(60, len(new))}개 → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
