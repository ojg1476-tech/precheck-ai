"""AI 판별기 다시 학습하기 (모델은 저장소의 8비트 모델 그대로) — 화장품·식품 기준값을 따로 정한다.

바꾼 점 (2026-10-30)
- 음성(평범한 문장)에 화장품 리뷰를 더 넣는다: 예전에는 리뷰 표본 대부분이 식품이라 화장품 리뷰를 많이 잘못 표시했다.
- 기준값을 화장품용·식품용으로 따로 정한다: 각 분야의 평범한 리뷰(학습에 안 쓴 것) 중 AI가 새로 표시하는 비율이 1%가 되게.
- 오탐 비율은 기준값을 정하는 데 쓰지 않은 리뷰로 따로 잰다.

1) 시험 묶음(3~8)을 하나씩 빼고 학습·측정 → eval/report/ai_lobo.json (예전 방식 'old'와 새 방식 'new' 둘 다)
2) 모든 적발 문구로 다시 학습 → web/ai/kb.json 의 lr (w, b, threshold_cos, threshold_food)
GitHub Actions(.github/workflows/train_ai.yml)에서 실행.
"""
import argparse, base64, json, random, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_ai as B  # noqa: E402

HELD = ["test3", "test4", "test5", "test6", "test7", "test8"]
FINAL = ["test9"]   # 학습·기준값에 전혀 안 쓰는 최종 시험 세트 (build_ai.load 에 넣지 않는다)
DOM = {"cos": "cos", "fcos": "cos", "food": "food", "hfood": "food"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", required=True); ap.add_argument("--tokenizer", required=True); ap.add_argument("--reviews", required=True)
    a = ap.parse_args()
    emb = B.Embedder(a.onnx, a.tokenizer)
    ck = B.Checker()
    rule = lambda t, x: any(f.grade in ("red", "amber") for f in ck.check(x, t))
    V, A = B.load()
    R = B.reviews(a.reviews)                      # 예전 방식과 같은 2,000개 표본
    RA, RB = R[: len(R) // 2], R[len(R) // 2:]
    seen = {x for _, x in R}
    allr = B.reviews(a.reviews, n=10 ** 9)
    cos = [x for t, x in allr if t == "cos" and x not in seen]
    food = [x for t, x in allr if t == "food" and x not in seen]
    random.Random(5).shuffle(cos); random.Random(6).shuffle(food)
    k = len(cos) // 3
    cosTr, cosCal, cosEv = cos[:k], cos[k:2 * k], cos[2 * k:]
    foodCal, foodEv = food[:3000], food[3000:6000]
    EV = emb([x for _, _, x in V])
    cache = {}
    def wemb(texts):
        need = sorted({w for t in texts for w in B.windows(t)} - cache.keys())
        for w, e in zip(need, emb(need) if need else []): cache[w] = e
    wemb([x for _, _, x in V] + [x for _, _, x in A] + [s for _, s in R] + cos + foodCal + foodEv)
    B.log(f"적발 {len(V)} · 허용 {len(A)} · 화장품 리뷰 학습/기준/측정 {len(cosTr)}/{len(cosCal)}/{len(cosEv)} · 식품 리뷰 기준/측정 {len(foodCal)}/{len(foodEv)} · 구절 {len(cache)}")
    from sklearn.linear_model import LogisticRegression
    def text_max(text, f):
        ws = B.windows(text)
        return max(f(np.vstack([cache[w] for w in ws]))) if ws else -9
    def q(f, xs, typ):
        free = [text_max(x, f) for x in xs if not rule(typ, x)]
        return float(np.quantile(free, 1 - B.TARGET_FP)) + 1e-6
    def rate(f, xs, typ, th):
        return sum((not rule(typ, x)) and text_max(x, f) > th for x in xs), len(xs)
    def fit(tr, negA, extra):
        negW = sorted({w for _, s_ in RA for w in B.windows(s_)} | {w for x in negA for w in B.windows(x)} | {w for x in extra for w in B.windows(x)})
        EN = np.vstack([cache[w] for w in negW])
        X = np.vstack([EV[tr], EN]); y = np.r_[np.ones(len(tr)), np.zeros(len(EN))]
        lr = LogisticRegression(C=2.0, class_weight="balanced", max_iter=2000).fit(X, y)
        return lr, (lambda M: lr.decision_function(M))
    out = {"phrases": [], "allowed": [], "reviews": {}}
    for hb in HELD:
        ti = [i for i, v in enumerate(V) if v[0] == hb]
        tr = [i for i, v in enumerate(V) if v[0] != hb]
        negA = [x for b, _, x in A if b != hb]
        _, f_old = fit(tr, negA, [])
        th_old = float(np.quantile([text_max(x, f_old) for t, x in RB if not rule(t, x)], 1 - B.TARGET_FP)) + 1e-6
        _, f_new = fit(tr, negA, cosTr)
        th_new = {"cos": q(f_new, cosCal, "cos"), "food": q(f_new, foodCal, "food")}
        for i in ti:
            _, t, x = V[i]
            out["phrases"].append({"batch": hb, "type": t, "text": x, "rule": bool(rule(t, x)),
                                   "ai_old": bool(text_max(x, f_old) > th_old), "ai_new": bool(text_max(x, f_new) > th_new[DOM[t]])})
        for b, t, x in A:
            if b == hb:
                out["allowed"].append({"batch": hb, "type": t, "text": x, "rule": bool(rule(t, x)),
                                       "ai_old": bool(text_max(x, f_old) > th_old), "ai_new": bool(text_max(x, f_new) > th_new[DOM[t]])})
        if hb == "test3":
            for typ, xs in (("cos", cosEv), ("food", foodEv)):
                o, n = rate(f_old, xs, typ, th_old); nn, _ = rate(f_new, xs, typ, th_new[typ])
                out["reviews"][typ] = {"n": n, "rule": int(sum(bool(rule(typ, x)) for x in xs)), "ai_new_old": int(o), "ai_new_new": int(nn)}
        B.log(f"{hb}: 처음 보는 위반 {len(ti)}개 (기준값 예전 {th_old:.3f} / 화장품 {th_new['cos']:.3f} · 식품 {th_new['food']:.3f})")
    p = ROOT / "eval/report/ai_lobo.json"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    for key in ("ai_old", "ai_new"):
        for dom in ("cos", "food"):
            ph = [x for x in out["phrases"] if DOM[x["type"]] == dom]
            B.log(f"{key} {dom}: 규칙 {sum(x['rule'] for x in ph)} → 규칙+AI {sum(x['rule'] or x[key] for x in ph)} / {len(ph)}")
    B.log(f"리뷰 오탐(측정용): {out['reviews']}")

    # 최종 모델: 모든 적발 문구로 학습, 기준값은 분야별
    lr, f = fit(list(range(len(V))), [x for _, _, x in A], cosTr)
    th_cos, th_food = q(f, cosCal, "cos"), q(f, foodCal, "food")
    oc, nc = rate(f, cosEv, "cos", th_cos); of, nf = rate(f, foodEv, "food", th_food)
    kbp = ROOT / "web/ai/kb.json"; kb = json.loads(kbp.read_text(encoding="utf-8"))
    kb["lr"] = {"w": base64.b64encode(lr.coef_[0].astype(np.float32).tobytes()).decode(), "b": float(lr.intercept_[0]),
                "threshold": round(th_food, 5), "threshold_cos": round(th_cos, 5), "threshold_food": round(th_food, 5),
                "measured_fp_cos": round(oc / nc, 4), "measured_fp_food": round(of / nf, 4),
                "note": "적발 문구(+) 대 평범한 리뷰(화장품 리뷰 포함)·허용 문장 구절(−) 로지스틱 회귀. 기준값은 화장품·식품 따로 (tools/train_ai.py)"}
    kbp.write_text(json.dumps(kb, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    probe = ["피부 재생 크림", "탈모에 좋은 차", "촉촉한 보습 로션", "아이 키 크는 젤리"]
    wemb(probe)
    (ROOT / "web/ai/probe.json").write_text(json.dumps({x: {"lr": round(float(text_max(x, f)), 4)} for x in probe}, ensure_ascii=False) + "\n", encoding="utf-8")
    B.log(f"최종: 기준값 화장품 {th_cos:.4f} · 식품 {th_food:.4f} · 측정용 리뷰 새 표시 화장품 {oc}/{nc} · 식품 {of}/{nf}")

    # 최종 시험(학습에 안 쓴 세트): 위 최종 모델로 채점만 한다 → eval/report/ai_final.json
    import csv
    fin = {}
    for name in FINAL:
        rows = [r for r in csv.DictReader(open(ROOT / f"data/{name}.csv", encoding="utf-8")) if r["label"] in ("violation", "allowed")]
        wemb([r["text"] for r in rows])
        th = {"cos": th_cos, "food": th_food}
        fin[name] = [{"type": r["product_type"], "label": r["label"], "text": r["text"], "rule": bool(rule(r["product_type"], r["text"])),
                      "ai": bool(r["product_type"] != "hfood" and text_max(r["text"], f) > th[DOM[r["product_type"]]])} for r in rows]
        v = [x for x in fin[name] if x["label"] == "violation"]; al = [x for x in fin[name] if x["label"] == "allowed"]
        B.log(f"최종 시험 {name}: 규칙 {sum(x['rule'] for x in v)} → 규칙+AI {sum(x['rule'] or x['ai'] for x in v)} / {len(v)} · 허용 오탐 규칙+AI {sum(x['rule'] or x['ai'] for x in al)}/{len(al)}")
    (ROOT / "eval/report/ai_final.json").write_text(json.dumps(fin, ensure_ascii=False, indent=0), encoding="utf-8")


if __name__ == "__main__":
    main()
