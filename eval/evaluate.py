"""검사기 정확도 측정.

사용: python eval/evaluate.py [--split dev|test|all] [--rules rules/rules.json] [--out eval/results_<split>.md]

지표
- 위반 탐지율(재현율): 위반 문구 중 검사기가 하나라도 표시한 비율
- 강한 탐지율: 위반 문구 중 '꼭 고치기' 또는 '확인 필요'로 표시한 비율
- 오탐률: 허용 문구 중 '꼭 고치기' 또는 '확인 필요'로 잘못 표시한 비율 ('자료 챙기기'는 오탐으로 세지 않음)
- 정밀도: '꼭 고치기'·'확인 필요'로 표시한 문구 중 실제 위반 비율 (조건부 문구 제외)
- 조건부 알림률: 자료가 있어야 쓰는 문구에 알림을 띄운 비율
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck import Checker  # noqa: E402

DOMAIN = {"cos": "화장품", "fcos": "화장품", "food": "식품", "hfood": "식품"}


def pct(a, b):
    return f"{a / b * 100:.1f}% ({a}/{b})" if b else "-"


def run(split="test", rules=None):
    ck = Checker(rules) if rules else Checker()
    rows = list(csv.DictReader(open(ROOT / "data" / "eval_set.csv", encoding="utf-8")))
    if split != "all":
        rows = [r for r in rows if r["split"] == split]
    res = []
    for r in rows:
        fs = ck.check(r["text"], r["product_type"])
        grades = {f.grade for f in fs}
        res.append({**r, "any": bool(fs), "strong": bool(grades & {"red", "amber"}),
                    "hits": "; ".join(f"{f.phrase}({f.grade_name})" for f in fs)})
    return ck, res


def metrics(res):
    by = defaultdict(list)
    for r in res:
        by[r["label"]].append(r)
    v, a, c = by["violation"], by["allowed"], by["conditional"]
    flagged = [r for r in v + a if r["strong"]]
    return {
        "n": len(res),
        "recall": (sum(r["any"] for r in v), len(v)),
        "strong_recall": (sum(r["strong"] for r in v), len(v)),
        "fp_rate": (sum(r["strong"] for r in a), len(a)),
        "precision": (sum(r["label"] == "violation" for r in flagged), len(flagged)),
        "cond_alert": (sum(r["any"] for r in c), len(c)),
    }


def report(split, ck, res):
    m = metrics(res)
    L = [f"# 검사기 정확도 — {split} 세트", "",
         f"규칙 버전 {ck.version} · 규칙 {len(ck.rules)}개 · 문구 {m['n']}개", "",
         "| 지표 | 전체 | 화장품 | 식품 |", "| --- | --- | --- | --- |"]
    parts = {d: metrics([r for r in res if DOMAIN[r["product_type"]] == d]) for d in ("화장품", "식품")}
    names = [("recall", "위반 탐지율"), ("strong_recall", "강한 탐지율 (꼭 고치기·확인 필요)"),
             ("fp_rate", "오탐률 (허용 문구를 잘못 잡음)"), ("precision", "정밀도"), ("cond_alert", "조건부 알림률")]
    for k, n in names:
        L.append(f"| {n} | {pct(*m[k])} | {pct(*parts['화장품'][k])} | {pct(*parts['식품'][k])} |")
    cat = defaultdict(lambda: [0, 0])
    for r in res:
        if r["label"] == "violation":
            cat[r["category"]][0] += r["any"]
            cat[r["category"]][1] += 1
    L += ["", "## 위반 유형별 탐지율", "", "| 유형 | 탐지율 |", "| --- | --- |"]
    L += [f"| {k} | {pct(*v)} |" for k, v in sorted(cat.items(), key=lambda x: x[1][0] / x[1][1])]
    miss = [r for r in res if r["label"] == "violation" and not r["any"]]
    fps = [r for r in res if r["label"] == "allowed" and r["strong"]]
    L += ["", f"## 놓친 위반 문구 ({len(miss)}개)", ""]
    L += [f"- [{r['product_type']}] {r['text']} — {r['category']}, {r['source']}" for r in miss] or ["- 없음"]
    L += ["", f"## 잘못 잡은 허용 문구 ({len(fps)}개)", ""]
    L += [f"- [{r['product_type']}] {r['text']} → {r['hits']}" for r in fps] or ["- 없음"]
    cm = [r for r in res if r["label"] == "conditional" and not r["any"]]
    L += ["", f"## 알림 없이 지나간 조건부 문구 ({len(cm)}개)", ""]
    L += [f"- [{r['product_type']}] {r['text']}" for r in cm] or ["- 없음"]
    return "\n".join(L) + "\n", m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--rules", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    ck, res = run(a.split, a.rules)
    md, m = report(a.split, ck, res)
    out = Path(a.out) if a.out else ROOT / "eval" / f"results_{a.split}.md"
    out.write_text(md, encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    print(md)
