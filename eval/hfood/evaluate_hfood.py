"""건강기능식품 원료 대조 평가: 실제 신고된 제품(식품안전나라 C003, 2020년 이후 3,000개 표본)으로 잰다.

제품마다 '원재료 목록'(실제 신고 문구)과 '제품이 인정받은 기능성'이 있다.
 A. 원료 인식: 원재료 목록에서 기능성 원료를 하나라도 찾는 비율
 B. 잘못 잡지 않기: 원재료 목록 + 그 제품의 인정 기능성 문구 → '인정받지 않은 기능성'(꼭 고치기)이 나오면 오탐
 C. 놓치지 않기: 원재료 목록 + 그 제품과 기능이 겹치지 않는 다른 제품의 기능성 문구 → '꼭 고치기'가 나오면 적발
사용: python eval/hfood/evaluate_hfood.py
"""
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from precheck.engine import Checker  # noqa: E402
from precheck.hfood import find_funcs, find_ingredients  # noqa: E402

ck = Checker()
kb = ck.hfood
rows = json.loads((ROOT / "data/hfood/raw/C003_sample.json").read_text(encoding="utf-8"))
parents = {f["id"]: [p for p in f["parent"].split(",") if p] for f in kb["funcs"]}


def claims(s):
    out = []
    for p in re.split(r"[\r\n]+|[①②③④⑤⑥⑦⑧⑨]|\(\d+\)|\s\d\)\s", s or ""):
        p = re.sub(r"\(국문\)|\(영문\).*|\(기타.*?\)|\(생리활성.*?\)", "", p).strip(" .,-/")
        if len(p) >= 6 and re.search("도움|필요", p):
            out.append(p)
    return out


def tags(text):
    t = set()
    for f in find_funcs(text, kb):
        t.add(f["id"])
        t.update(parents[f["id"]])
    return t


prods = []
for r in rows:
    cs = claims(r["PRIMARY_FNCLTY"])
    raw = (r["RAWMTRL_NM"] or "").strip()
    if cs and raw:
        prods.append({"name": r["PRDLST_NM"], "raw": raw, "claims": cs, "tags": set().union(*(tags(c) for c in cs))})
rnd = random.Random(1)
recog = b_fp = b_n = c_hit = c_n = c_any = b_any = 0
fp_ex, miss_ex, unk, by_form = [], [], Counter(), {}
pool = [c for p in prods for c in p["claims"]]
for p in prods:
    ings = find_ingredients(p["raw"], kb)
    if not ings:
        for w in re.split(r"[,()]", p["raw"])[:1]:
            unk[w.strip()[:20]] += 1
        continue
    recog += 1
    for c in p["claims"][:3]:
        b_n += 1
        fs = ck.check(p["raw"] + ". " + c, "hfood")
        bad = [f for f in fs if f.rule_id == "H4"]
        b_any += any(f.rule_id in ("H3", "H4", "H5") for f in fs)
        if bad:
            b_fp += 1
            if len(fp_ex) < 25:
                fp_ex.append((p["name"], p["raw"][:60], c, bad[0].phrase))
    for _ in range(50):
        c = rnd.choice(pool)
        ct = tags(c)
        if ct and not (ct & p["tags"]):
            break
    else:
        continue
    c_n += 1
    form = "도움" if "도움" in c else "필요"
    fs = ck.check(p["raw"] + ". " + c, "hfood")
    by_form.setdefault(form, Counter())["n"] += 1
    by_form[form]["red"] += any(f.rule_id == "H4" for f in fs)
    by_form[form]["any"] += any(f.rule_id in ("H3", "H4", "H5") for f in fs)
    by_form[form]["passed_other_ing"] += any(f.rule_id == "H1" for f in fs) and not any(f.rule_id in ("H3", "H4", "H5") for f in fs)
    c_any += any(f.rule_id in ("H3", "H4", "H5") for f in fs)
    if any(f.rule_id == "H4" for f in fs):
        c_hit += 1
    elif len(miss_ex) < 25:
        miss_ex.append((p["name"], p["raw"][:60], c, [(f.rule_id, f.phrase) for f in fs if f.rule_id.startswith("H")]))

n = len(prods)
res = {"products": n, "recognized": recog, "recog_rate": recog / n, "b_n": b_n, "b_fp": b_fp, "b_fp_rate": b_fp / max(b_n, 1),
       "b_any_rate": b_any / max(b_n, 1),
       "c_n": c_n, "c_hit": c_hit, "c_recall": c_hit / max(c_n, 1), "c_any_rate": c_any / max(c_n, 1),
       "c_by_form": {k: dict(v) for k, v in by_form.items()}}
(ROOT / "eval/hfood/results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=1))
if "-v" in sys.argv:
    print("\n잘못 잡은 예:"); [print(" ", x) for x in fp_ex]
    print("\n놓친 예:"); [print(" ", x) for x in miss_ex]
    print("\n원료를 못 찾은 제품의 첫 원재료:", unk.most_common(30))
