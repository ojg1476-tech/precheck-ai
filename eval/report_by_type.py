"""제품 종류별 정확도 보고서 (3단계).

비교하는 세 방식
- 금칙어 목록: 시중 '금지어 검사기'처럼 단어 목록에 있으면 표시 (eval/baseline/keyword_list.py, 직접 구성한 기준선)
- 규칙: 지금 사이트의 규칙 (+ 건강기능식품 원료 대조)
- 규칙 + AI: 위에 학습형 AI(뜻 비교)를 더한 것. 시험할 묶음은 학습에서 빼고 잰 결과(eval/report/ai_lobo.json, GitHub Actions)

데이터: 규칙을 만든 뒤에 모은 '처음 보는' 실제 적발 문구 118개(시험 세트 3·4·5·6·7)와 허용 문장 37개,
        평범한 쇼핑 리뷰 23,622개(화장품·식품, 네이버 쇼핑 리뷰 공개 코퍼스)
        + 최종 시험 세트 9·10 (화장품): 고정한 시점의 규칙(수정 전, eval/report/final_rule_prefix.json)과
          그 세트를 학습에 안 쓴 AI(eval/report/ai_final.json)로 잰다. 세트 8은 규칙을 만들며 본 문구라 빼고 잰다.
사용: python eval/report_by_type.py --reviews <naver_shopping.txt>
"""
import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "baseline"))
from precheck import Checker  # noqa: E402
from keyword_list import flag as kw_flag  # noqa: E402

TYPES = [("cos", "일반 화장품"), ("fcos", "기능성 화장품"), ("food", "일반 식품"), ("hfood", "건강기능식품")]
HELD = {"test3": "data/test3.csv", "test4": "data/test4.csv", "test5": "data/test5_batches.csv", "test6": "data/test6.csv", "test7": "data/test7.csv"}


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviews")
    a = ap.parse_args()
    ck = Checker()
    strong = lambda t, x: any(f.grade in ("red", "amber") for f in ck.check(x, t))
    ai = json.loads((ROOT / "eval/report/ai_lobo.json").read_text(encoding="utf-8"))
    K = "ai_new" if ai["phrases"] and "ai_new" in ai["phrases"][0] else "ai"   # 화장품·식품 기준값을 따로 쓰는 새 방식
    ai_v = {(p["batch"], p["text"]): p[K] for p in ai["phrases"]}
    ai_a = {(p["batch"], p["text"]): p[K] for p in ai["allowed"]}

    rows = []
    for b, f in HELD.items():
        for r in csv.DictReader(open(ROOT / f, encoding="utf-8")):
            if r["label"] not in ("violation", "allowed"):
                continue
            t, x = r["product_type"], r["text"]
            kw, ru = kw_flag(x), strong(t, x)
            aim = (ai_v if r["label"] == "violation" else ai_a).get((b, x), False) and t not in ("hfood", "fcos")   # 사이트는 건강기능식품·기능성 화장품에 AI를 안 씀
            rows.append({"batch": b, "type": t, "label": r["label"], "text": x, "kw": kw, "rule": ru, "both": ru or aim})

    systems = [("kw", "금칙어 목록"), ("rule", "규칙"), ("both", "규칙 + AI")]
    out = {"types": {}, "systems": dict(systems)}
    for key, name in TYPES + [("all", "전체")]:
        rs = [r for r in rows if key == "all" or r["type"] == key]
        v = [r for r in rs if r["label"] == "violation"]
        al = [r for r in rs if r["label"] == "allowed"]
        d = {"name": name, "n_violation": len(v), "n_allowed": len(al)}
        for s, _ in systems:
            k = sum(r[s] for r in v)
            fp = sum(r[s] for r in al)
            lo, hi = wilson(k, len(v))
            prec_n = k + fp
            d[s] = {"recall": k / len(v) if v else None, "hit": k, "ci": [lo, hi], "fp": fp,
                    "fp_rate": fp / len(al) if al else None, "precision": k / prec_n if prec_n else None}
        out["types"][key] = d
    by_batch = defaultdict(dict)
    for b in HELD:
        v = [r for r in rows if r["batch"] == b and r["label"] == "violation"]
        for s, _ in systems:
            by_batch[b][s] = [sum(r[s] for r in v), len(v)]
    out["batches"] = by_batch

    # 평범한 리뷰에서 '꼭 고치기·확인 필요'로 잘못 표시하는 비율
    if a.reviews:
        COS = re.compile(r"크림|로션|토너|세럼|에센스|앰플|선크림|샴푸|화장품|스킨|클렌징|마스크팩")
        FOOD = re.compile(r"맛있|먹|마셔|마시|차가|젤리|간식|과자|음료|영양제|즙|분말|스틱")
        rv = defaultdict(lambda: {"n": 0, "kw": 0, "rule": 0})
        for line in open(a.reviews, encoding="utf-8"):
            s = line.rstrip("\n").split("\t", 1)[-1]
            t = "cos" if COS.search(s) else "food" if FOOD.search(s) else None
            if not t:
                continue
            rv[t]["n"] += 1
            rv[t]["kw"] += kw_flag(s)
            rv[t]["rule"] += strong(t, s)
        for t in rv:   # AI가 '새로' 표시한 비율은 학습에 안 쓴 리뷰 표본에서 잰 값(ai_lobo.json)을 더한다
            ar = ai["reviews"].get(t)
            an = ar.get("ai_new_new", ar.get("ai_new", 0)) if ar else 0
            rv[t]["both_rate"] = rv[t]["rule"] / rv[t]["n"] + (an / ar["n"] if ar else 0)
        out["reviews"] = rv

    # 최종 시험 (세트 9·10): 고정 시점 규칙 / + AI / 지금 규칙(참고: 이미 본 데이터)
    pre = json.loads((ROOT / "eval/report/final_rule_prefix.json").read_text(encoding="utf-8"))
    fp_ = ROOT / "eval/report/ai_final.json"
    fai = json.loads(fp_.read_text(encoding="utf-8")) if fp_.exists() else {}
    final = {}
    for n in ("test9", "test10", "test11", "test12", "test13"):
        ais = {x["text"]: x["ai"] for x in fai.get(n, [])}
        rs = [r for r in csv.DictReader(open(ROOT / f"data/{n}.csv", encoding="utf-8")) if r["label"] in ("violation", "allowed")]
        d = {}
        for lab in ("violation", "allowed"):
            xs = [r for r in rs if r["label"] == lab]
            d[lab] = {"n": len(xs), "kw": sum(kw_flag(r["text"]) for r in xs), "rule_prefix": sum(pre[n][r["text"]] for r in xs),
                      "both_prefix": sum(pre[n][r["text"]] or (ais.get(r["text"], False) and r["product_type"] not in ("hfood", "fcos")) for r in xs) if ais else None,
                      "rule_now": sum(strong(r["product_type"], r["text"]) for r in xs)}
        final[n] = d
    out["final"] = final

    hf = json.loads((ROOT / "eval/hfood/results.json").read_text(encoding="utf-8"))
    hp = json.loads((ROOT / "eval/hfood/results_products.json").read_text(encoding="utf-8"))
    out["hfood_products"] = {"ingredient": hf, "report_no": hp}
    (ROOT / "eval/report/report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # 글로 된 보고서
    P = lambda x: "-" if x is None else f"{x * 100:.0f}%"
    L = ["# 제품 종류별 정확도 보고서", "",
         "처음 보는 실제 적발 문구(규칙을 만든 뒤 모은 시험 세트 3~7)로 잰 결과예요. 괄호는 95% 신뢰구간이에요.", "",
         "| 제품 종류 | 위반 문구 | 금칙어 목록 | 규칙 | 규칙 + AI | 허용 문장 오탐 (금칙어 / 규칙 / 규칙+AI) |", "|---|---|---|---|---|---|"]
    for key, d in out["types"].items():
        cell = lambda s: f"{P(d[s]['recall'])} ({d[s]['hit']}개, {d[s]['ci'][0] * 100:.0f}~{d[s]['ci'][1] * 100:.0f}%)" if d["n_violation"] else "-"
        fp = " / ".join(f"{d[s]['fp']}" for s, _ in systems) + f" (총 {d['n_allowed']}개)" if d["n_allowed"] else "-"
        L.append(f"| {d['name']} | {d['n_violation']} | {cell('kw')} | {cell('rule')} | {cell('both')} | {fp} |")
    L += ["", "## 최종 시험 (처음 보는 적발 문구, 세트를 고정한 뒤 한 번만 잰 값 — 9·10·13 화장품, 11·12 식품)", "",
          "| 세트 | 위반 문구 | 금칙어 목록 | 규칙 (고정 시점) | 규칙 + AI (고정 시점) | 허용 문장 오탐 (규칙+AI) | 지금 규칙 (참고·이미 본 데이터) |", "|---|---|---|---|---|---|---|"]
    for n, d in final.items():
        v, al = d["violation"], d["allowed"]
        pc = lambda k: f"{k / v['n'] * 100:.0f}% ({k}개)"
        L.append(f"| {n} | {v['n']} | {pc(v['kw'])} | {pc(v['rule_prefix'])} | {pc(v['both_prefix']) if v['both_prefix'] is not None else '-'} | "
                 f"{al['both_prefix'] if al['both_prefix'] is not None else al['rule_prefix']}/{al['n']} | {pc(v['rule_now'])} |")
    if a.reviews:
        L += ["", "| 평범한 쇼핑 리뷰 | 리뷰 수 | 금칙어 목록 | 규칙 | 규칙 + AI |", "|---|---|---|---|---|"]
        for t, nm in (("cos", "화장품 리뷰"), ("food", "식품 리뷰")):
            r = out["reviews"][t]
            L.append(f"| {nm} | {r['n']:,} | {r['kw'] / r['n'] * 100:.1f}% | {r['rule'] / r['n'] * 100:.2f}% | {r['both_rate'] * 100:.2f}% |")
    (ROOT / "eval/report/report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
