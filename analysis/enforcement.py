"""식약처 온라인 부당광고 단속 데이터 분석.

입력: data/enforcement/{inspections,yearly,yearly_types,phrases}.csv
출력: analysis/out/summary.json (대시보드용), analysis/out/report.md (사람이 읽는 요약)
실행: python analysis/enforcement.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck import Checker  # noqa: E402

D = ROOT / "data" / "enforcement"
OUT = ROOT / "analysis" / "out"
TYPES = ["질병예방치료", "의약품오인", "건기식오인", "거짓과장", "체험기기만", "심의위반", "기능성오인", "소비자오인", "기타"]
SEASON = {12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄", 6: "여름", 7: "여름", 8: "여름",
          9: "가을", 10: "가을", 11: "가을"}


def load(name):
    with open(D / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(x):
    return int(x) if str(x).strip() else 0


def yearly_trend(yearly):
    """연도별 적발 건수. 진행 중인 해는 12개월로 환산한 값도 같이 (환산값은 추정)."""
    out = defaultdict(list)
    for r in yearly:
        v, m = int(r["violations"]), int(r["months"])
        out[r["domain"]].append({"year": int(r["year"]), "months": m, "violations": v,
                                 "annualized": round(v * 12 / m) if m < 12 else v, "partial": m < 12})
    for rows in out.values():
        rows.sort(key=lambda x: x["year"])
        for a, b in zip(rows, rows[1:]):
            b["yoy_pct"] = round((b["annualized"] / a["annualized"] - 1) * 100, 1)
    return dict(out)


def type_mix(insp):
    """점검 발표 단위 유형 구성비. 유형이 공개된 발표만 쓴다(합계와 유형 합이 같은 것)."""
    agg = defaultdict(Counter)   # (domain_group, year) -> Counter
    used = []
    for r in insp:
        s = sum(num(r[t]) for t in TYPES)
        if not s or s != num(r["total"]):
            continue
        g = "화장품" if r["domain"] == "화장품" else "식품·건기식"
        y = r["date"][:4]
        for t in TYPES:
            agg[(g, y)][t] += num(r[t])
        used.append(r["id"])
    mix = []
    for (g, y), c in sorted(agg.items()):
        tot = sum(c.values())
        mix.append({"group": g, "year": y, "total": tot,
                    "share": {t: round(c[t] / tot * 100, 1) for t in TYPES if c[t]}})
    return mix, used


def themes(insp):
    rows = []
    for r in insp:
        m = int(r["date"][5:7])
        rows.append({"id": r["id"], "date": r["date"], "season": SEASON[m], "domain": r["domain"],
                     "theme": r["theme"], "media": r["media"], "total": num(r["total"]),
                     "checked": num(r["checked"]) or None,
                     "hit_rate": round(num(r["total"]) / num(r["checked"]) * 100, 1) if num(r["checked"]) else None})
    return rows


def coverage(phrases, ck, old=None):
    """실제 적발 문구를 지금 규칙이 잡는지. 유형·연도별. old = 분석 전 규칙(v3.1)으로 잡았는지."""
    res, by_cat, by_year = [], defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for p in phrases:
        fs = ck.check(p["text"], p["product_type"])
        hit = bool(fs)
        res.append({**p, "hit": hit, "hit_before": bool(old.check(p["text"], p["product_type"])) if old else None,
                    "grade": fs[0].grade if fs else "", "rule": fs[0].label if fs else ""})
        by_cat[p["category"]][0] += hit
        by_cat[p["category"]][1] += 1
        by_year[p["year"] or "연도 미상"][0] += hit
        by_year[p["year"] or "연도 미상"][1] += 1
    pct = lambda a: {k: {"hit": v[0], "n": v[1], "pct": round(v[0] / v[1] * 100, 1)} for k, v in sorted(a.items())}
    return res, pct(by_cat), pct(by_year)


def main():
    ck = Checker()
    insp, yearly, ytypes, phrases = load("inspections.csv"), load("yearly.csv"), load("yearly_types.csv"), load("phrases.csv")
    trend = yearly_trend(yearly)
    mix, used = type_mix(insp)
    th = themes(insp)
    old = Checker(ROOT / "analysis" / "rules_v3.1.json")
    cov, cov_cat, cov_year = coverage(phrases, ck, old)
    hits = sum(r["hit"] for r in cov)
    misses = [r for r in cov if not r["hit"]]
    new_only = [r for r in cov if r["set"] == "new"]

    food25 = {r["type"]: int(r["violations"]) for r in ytypes if r["domain"] == "식품" and r["period"] == "2025"}
    food26 = {r["type"]: int(r["violations"]) for r in ytypes if r["domain"] == "식품" and r["period"] == "2026.1-8"}
    t25, t26 = sum(food25.values()), 8792  # 2026 전체 건수(유형 3개만 공개)

    summary = {
        "trend": trend,
        "food_types": {"2025": {k: {"n": v, "pct": round(v / t25 * 100, 1)} for k, v in food25.items()},
                       "2026.1-8": {k: {"n": v, "pct": round(v / t26 * 100, 1)} for k, v in food26.items()}},
        "type_mix": mix, "type_mix_used": used,
        "inspections": th,
        "coverage": {"hit": hits, "n": len(cov), "pct": round(hits / len(cov) * 100, 1),
                     "by_category": cov_cat, "by_year": cov_year,
                     "new_phrases": {"hit": sum(r["hit"] for r in new_only), "hit_before": sum(r["hit_before"] for r in new_only),
                                     "n": len(new_only)},
                     "misses": [{k: r[k] for k in ("text", "product_type", "category", "year", "set")} for r in misses]},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 식약처 온라인 부당광고 단속 분석 결과", "",
         f"점검 발표 {len(insp)}건 · 연도별 집계 {len(yearly)}행 · 실제 적발 문구 {len(cov)}개", "",
         "## 연도별 적발 (진행 중인 해는 12개월 환산 추정)", ""]
    for dom, rows in trend.items():
        L.append(f"- {dom}: " + " → ".join(
            f"{r['year']} {r['violations']:,}" + (f"(환산 {r['annualized']:,})" if r["partial"] else "") for r in rows))
    L += ["", "## 점검 발표 기준 유형 구성비(%)", ""]
    for m in mix:
        L.append(f"- {m['group']} {m['year']} (n={m['total']}): " + ", ".join(f"{k} {v}" for k, v in
                                                                           sorted(m["share"].items(), key=lambda x: -x[1])))
    L += ["", f"## 지금 규칙이 실제 적발 문구를 잡는 비율: {hits}/{len(cov)} ({summary['coverage']['pct']}%)", ""]
    for k, v in cov_cat.items():
        L.append(f"- {k}: {v['hit']}/{v['n']} ({v['pct']}%)")
    L += ["", "### 못 잡은 문구", ""] + [f"- [{r['set']}] {r['text']} ({r['product_type']}, {r['category']})" for r in misses]
    # 대시보드용 문구별 결과
    with open(OUT / "phrase_coverage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "text", "product_type", "category", "year", "set", "hit_before", "hit_now", "grade", "rule"])
        for i, r in enumerate(cov, 1):
            w.writerow([f"P{i:03d}", r["text"], r["product_type"], r["category"], r["year"], r["set"],
                        int(r["hit_before"]), int(r["hit"]), r["grade"], r["rule"]])
    L.insert(L.index("### 못 잡은 문구"), f"이번에 새로 모은 문구 {len(new_only)}개: 분석 전 규칙(v3.1) {summary['coverage']['new_phrases']['hit_before']}개 → 지금(v3.2) {summary['coverage']['new_phrases']['hit']}개\n")
    (OUT / "report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
