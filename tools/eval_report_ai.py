"""정확도 보고서용: 학습형 AI(규칙 + AI)를 '묶음 하나씩 빼고' 다시 학습해, 처음 보는 문구 하나하나의 판정을 저장한다.

tools/build_ai.py 의 학습 방식과 같다(구절 나누기·로지스틱 회귀·평범한 리뷰 1% 기준값). 모델은 저장소의 8비트 모델을 쓴다.
GitHub Actions(.github/workflows/eval_report.yml)에서 실행 → eval/report/ai_lobo.json
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_ai as B  # noqa: E402

HELD = ["test3", "test4", "test5", "test6", "test7"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", required=True); ap.add_argument("--tokenizer", required=True); ap.add_argument("--reviews", required=True)
    a = ap.parse_args()
    emb = B.Embedder(a.onnx, a.tokenizer)
    ck = B.Checker()
    rule = lambda t, x: any(f.grade in ("red", "amber") for f in ck.check(x, t))
    V, A = B.load()
    R = B.reviews(a.reviews)
    EV = emb([x for _, _, x in V])
    cache = {}
    def wemb(texts):
        need = sorted({w for t in texts for w in B.windows(t)} - cache.keys())
        for w, e in zip(need, emb(need) if need else []): cache[w] = e
    wemb([x for _, _, x in V] + [x for _, _, x in A] + [s for _, s in R])
    from sklearn.linear_model import LogisticRegression
    RA, RB = R[: len(R) // 2], R[len(R) // 2:]
    def text_max(text, f):
        ws = B.windows(text)
        return max(f(np.vstack([cache[w] for w in ws]))) if ws else -9
    out = {"phrases": [], "allowed": [], "reviews": {}}
    for hb in HELD:
        ti = [i for i, v in enumerate(V) if v[0] == hb]
        tr = [i for i, v in enumerate(V) if v[0] != hb]
        # 음성: 리뷰 앞쪽 절반 + 빼 둔 묶음이 아닌 허용 문장의 구절
        negA = [x for b, _, x in A if b != hb]
        negW = sorted({w for _, s_ in RA for w in B.windows(s_)} | {w for x in negA for w in B.windows(x)})
        EN = np.vstack([cache[w] for w in negW])
        X = np.vstack([EV[tr], EN]); y = np.r_[np.ones(len(tr)), np.zeros(len(EN))]
        lr = LogisticRegression(C=2.0, class_weight="balanced", max_iter=2000).fit(X, y)
        f = lambda M: lr.decision_function(M)
        free = [text_max(x, f) for t, x in RB if not rule(t, x)]
        th = float(np.quantile(free, 1 - B.TARGET_FP)) + 1e-6
        for i in ti:
            _, t, x = V[i]
            out["phrases"].append({"batch": hb, "type": t, "text": x, "rule": bool(rule(t, x)), "ai": bool(text_max(x, f) > th)})
        for b, t, x in A:
            if b == hb:   # 빼 둔 묶음의 허용 문장 (학습에 안 씀)
                out["allowed"].append({"batch": hb, "type": t, "text": x, "rule": bool(rule(t, x)), "ai": bool(text_max(x, f) > th)})
        if hb == "test3":   # 평범한 리뷰(학습에 안 쓴 뒤쪽 절반) — 종류별로 규칙·AI가 새로 표시한 비율
            for typ in ("cos", "food"):
                rs = [x for t, x in RB if t == typ]
                out["reviews"][typ] = {"n": len(rs), "rule": int(sum(bool(rule(typ, x)) for x in rs)),
                                       "ai_new": int(sum(bool((not rule(typ, x)) and text_max(x, f) > th) for x in rs))}
        B.log(f"{hb}: 처음 보는 위반 {len(ti)}개 처리")
    p = ROOT / "eval/report/ai_lobo.json"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    n = len(out["phrases"]); r = sum(x["rule"] for x in out["phrases"]); b = sum(x["rule"] or x["ai"] for x in out["phrases"])
    B.log(f"합계 {n}개: 규칙 {r} → 규칙+AI {b} · 리뷰 {out['reviews']}")


if __name__ == "__main__":
    main()
