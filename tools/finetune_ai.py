"""AI 문장 모델 자체를 다시 학습(미세조정)하고, 지금 방식과 공정하게 비교한다. GitHub Actions(.github/workflows/finetune_ai.yml)에서 실행.

지금 방식: 문장 모델(ko-sroberta-multitask)은 그대로 두고, 그 위의 판별기(로지스틱 회귀)만 학습
새 방식: 문장 모델까지 '적발 문구 대 평범한 문장'으로 미세조정한 뒤, 같은 판별기·기준값 방식을 얹음

--mode ab    : 시험 세트 9·10·11·12를 두 방식 모두 학습에서 빼고, 같은 조건으로 학습 → 그 세트와 리뷰로 비교
               결과: eval/report/ai_finetune_ab.json
--mode final : 세트 11·12(최종 시험)만 빼고 미세조정 → --save 폴더에 모델 저장 (ONNX 변환은 워크플로에서)

연습 문장(data/aug/*.csv, 합성)은 학습에만 쓴다. 시험·기준값·오탐 측정에는 진짜 문구·리뷰만 쓴다.
"""
import argparse, csv, json, random, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_ai as B  # noqa: E402

AB_EVAL = ["test9", "test10", "test11", "test12"]
DOM = {"cos": "cos", "fcos": "cos", "food": "food", "hfood": "food"}
NO_AI = {"hfood", "fcos"}


def splits(path):
    """train_ai.py 와 같은 리뷰 나누기 (같은 seed)"""
    R = B.reviews(path)
    RA, RB = R[: len(R) // 2], R[len(R) // 2:]
    seen = {x for _, x in R}
    allr = B.reviews(path, n=10 ** 9)
    cos = [x for t, x in allr if t == "cos" and x not in seen]
    food = [x for t, x in allr if t == "food" and x not in seen]
    random.Random(5).shuffle(cos); random.Random(6).shuffle(food)
    k = len(cos) // 3
    return dict(RA=RA, RB=RB, cosTr=cos[:k], cosCal=cos[k:2 * k], cosEv=cos[2 * k:], foodCal=food[:3000], foodEv=food[3000:6000])


def load_aug():
    V, A = [], []
    for f in sorted((ROOT / "data/aug").glob("*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            (V if r["label"] == "violation" else A).append(("합성", r["product_type"], r["text"]))
    return V, A


def load_sets(names):
    out = []
    for n in names:
        for r in csv.DictReader(open(ROOT / f"data/{n}.csv", encoding="utf-8")):
            if r["label"] in ("violation", "allowed"):
                out.append((n, r["product_type"], r["label"], r["text"]))
    return out


def finetune(Vtr, Atr, sp, out_dir, epochs=2, seed=0):
    """문장 모델 + 선형 판별기를 같이 학습. 양성: 적발 문구(통째), 음성: 리뷰·허용 문장의 구절(브라우저와 같은 나누기)"""
    import torch
    from sentence_transformers import SentenceTransformer
    torch.manual_seed(seed); random.seed(seed)
    torch.set_num_threads(max(1, torch.get_num_threads()))
    st = SentenceTransformer("jhgan/ko-sroberta-multitask", device="cpu")
    st.max_seq_length = 64
    pos = sorted({x for _, _, x in Vtr})
    neg = sorted({w for _, s in sp["RA"] for w in B.windows(s)} | {w for s in sp["cosTr"] for w in B.windows(s)}
                 | {w for _, _, x in Atr for w in B.windows(x)})
    random.Random(seed).shuffle(neg)
    neg = neg[:30000]
    data = [(x, 1.0) for x in pos] + [(x, 0.0) for x in neg]
    B.log(f"미세조정: 적발 문구 {len(pos)} · 평범한 구절 {len(neg)} · {epochs}번 반복")
    head = torch.nn.Linear(st.get_sentence_embedding_dimension(), 1)
    params = list(st.parameters()) + list(head.parameters())
    opt = torch.optim.AdamW([{"params": list(st.parameters()), "lr": 2e-5}, {"params": list(head.parameters()), "lr": 1e-3}], weight_decay=0.01)
    pw = torch.tensor(len(neg) / max(1, len(pos)))
    lossf = torch.nn.BCEWithLogitsLoss(pos_weight=pw)
    bs, t0 = 32, time.time()
    st.train()
    for ep in range(epochs):
        random.Random(seed + ep).shuffle(data)
        tot = 0.0
        for i in range(0, len(data), bs):
            batch = data[i:i + bs]
            feats = st.tokenize([x for x, _ in batch])
            out = st(feats)["sentence_embedding"]
            emb = torch.nn.functional.normalize(out, dim=1)   # 브라우저와 같이 정규화한 임베딩 위에서 판별
            logit = head(emb).squeeze(1)
            loss = lossf(logit, torch.tensor([y for _, y in batch]))
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(params, 1.0); opt.step()
            tot += float(loss) * len(batch)
            if (i // bs) % 200 == 0:
                print(f"  {ep + 1}번째 {i}/{len(data)} 손실 {float(loss):.4f} ({time.time() - t0:.0f}초)", flush=True)
        B.log(f"미세조정 {ep + 1}/{epochs} 평균 손실 {tot / len(data):.4f} ({time.time() - t0:.0f}초)")
    st.eval()
    st.save(str(out_dir))
    return out_dir


def evaluate(name, onnx, tok, Vtr, Atr, evalrows, sp, prefix, fps=(B.TARGET_FP,)):
    """판별기(로지스틱 회귀)+화장품·식품 기준값을 train_ai.py 와 같은 방식으로 학습하고, 시험 세트·리뷰로 잰다"""
    from sklearn.linear_model import LogisticRegression
    emb = B.Embedder(onnx, tok)
    ck = B.Checker()
    rule = lambda t, x: any(f.grade in ("red", "amber") for f in ck.check(x, t))
    cache = {}
    def wemb(texts):
        need = sorted({w for t in texts for w in B.windows(t)} - cache.keys())
        for w, e in zip(need, emb(need) if need else []): cache[w] = e
    allx = [x for _, _, x in Vtr] + [x for _, _, x in Atr] + [s for _, s in sp["RA"]] + sp["cosTr"] + sp["cosCal"] + sp["cosEv"] + sp["foodCal"] + sp["foodEv"] + [r[3] for r in evalrows]
    wemb(allx)
    EV = emb([x for _, _, x in Vtr])
    negW = sorted({w for _, s in sp["RA"] for w in B.windows(s)} | {w for x in sp["cosTr"] for w in B.windows(x)} | {w for _, _, x in Atr for w in B.windows(x)})
    EN = np.vstack([cache[w] for w in negW])
    X = np.vstack([EV, EN]); y = np.r_[np.ones(len(EV)), np.zeros(len(EN))]
    lr = LogisticRegression(C=2.0, class_weight="balanced", max_iter=3000).fit(X, y)
    f = lambda M: lr.decision_function(M)
    def tmax(t):
        ws = B.windows(t)
        return max(f(np.vstack([cache[w] for w in ws]))) if ws else -9
    def q(xs, typ, fp):
        free = [tmax(x) for x in xs if not rule(typ, x)]
        return float(np.quantile(free, 1 - fp)) + 1e-6
    allres = {}
    for fp in fps:
        th = {"cos": q(sp["cosCal"], "cos", fp), "food": q(sp["foodCal"], "food", fp)}
        allres[fp] = score(name + (f" · 기준 {fp:.0%}" if len(fps) > 1 else ""), th, evalrows, prefix, tmax, rule, sp)
    return allres if len(fps) > 1 else allres[fps[0]]


def score(name, th, evalrows, prefix, tmax, rule, sp):
    res = {"name": name, "threshold": th, "sets": {}, "reviews": {}}
    for n in AB_EVAL:
        rs = [r for r in evalrows if r[0] == n]
        v = [r for r in rs if r[2] == "violation"]; al = [r for r in rs if r[2] == "allowed"]
        ai = lambda r: r[1] not in NO_AI and tmax(r[3]) > th[DOM[r[1]]]
        pre = prefix.get(n, {})
        res["sets"][n] = {"n": len(v), "ai_only": int(sum(ai(r) for r in v)),
                          "rule_prefix_plus_ai": int(sum(pre.get(r[3], False) or ai(r) for r in v)),
                          "rule_prefix": int(sum(pre.get(r[3], False) for r in v)),
                          "missed_by_rule_caught_by_ai": int(sum((not pre.get(r[3], False)) and ai(r) for r in v)),
                          "missed_by_rule": int(sum(not pre.get(r[3], False) for r in v)),
                          "n_allowed": len(al), "allowed_ai_fp": int(sum(ai(r) for r in al))}
    for typ, xs in (("cos", sp["cosEv"]), ("food", sp["foodEv"])):
        newf = sum((not rule(typ, x)) and tmax(x) > th[typ] for x in xs)
        res["reviews"][typ] = {"n": len(xs), "ai_new": int(newf)}
    tot = {k: sum(s[k] for s in res["sets"].values()) for k in ("n", "rule_prefix", "rule_prefix_plus_ai", "missed_by_rule", "missed_by_rule_caught_by_ai", "n_allowed", "allowed_ai_fp")}
    res["total"] = tot
    B.log(f"[{name}] 세트9~12 위반 {tot['n']}개: 규칙(고정 시점) {tot['rule_prefix']} → 규칙+AI {tot['rule_prefix_plus_ai']} "
          f"(규칙이 놓친 {tot['missed_by_rule']}개 중 AI가 {tot['missed_by_rule_caught_by_ai']}개) · 허용 오탐 {tot['allowed_ai_fp']}/{tot['n_allowed']} · "
          f"리뷰 새 표시 화장품 {res['reviews']['cos']['ai_new']}/{res['reviews']['cos']['n']} 식품 {res['reviews']['food']['ai_new']}/{res['reviews']['food']['n']}")
    for n, s in res["sets"].items():
        B.log(f"[{name}] {n}: 규칙 {s['rule_prefix']} → 규칙+AI {s['rule_prefix_plus_ai']} / {s['n']} · AI 단독 {s['ai_only']} · 허용 오탐 {s['allowed_ai_fp']}/{s['n_allowed']}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["ab", "final"], required=True)
    ap.add_argument("--reviews", required=True)
    ap.add_argument("--old-onnx"); ap.add_argument("--old-tok")
    ap.add_argument("--save", default="/tmp/ft_model")
    ap.add_argument("--new-onnx"); ap.add_argument("--new-tok")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--stage", choices=["train", "eval", "tradeoff"], default="train")
    a = ap.parse_args()
    sp = splits(a.reviews)
    V, A = B.load()
    aV, aA = load_aug()
    hold = set(AB_EVAL) if a.mode == "ab" else {"test11", "test12"}
    Vtr = [v for v in V if v[0] not in hold]; Atr = [x for x in A if x[0] not in hold]
    if a.stage == "train":
        finetune(Vtr + aV, Atr + aA, sp, Path(a.save), epochs=a.epochs)
        return
    if a.stage == "tradeoff":   # 지금 모델로 기준값(리뷰 오탐 목표)을 바꿔 가며 잡는 양·오탐 비교
        evalrows = load_sets(AB_EVAL)
        prefix = json.loads((ROOT / "eval/report/final_rule_prefix.json").read_text(encoding="utf-8"))
        r = evaluate("지금 방식", a.old_onnx, a.old_tok, Vtr, Atr, evalrows, sp, prefix, fps=(0.01, 0.02, 0.03, 0.05))
        (ROOT / "eval/report/ai_threshold_tradeoff.json").write_text(json.dumps({str(k): v for k, v in r.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
        return
    # eval (ab): 두 방식을 같은 학습 데이터(진짜 문구만)로 판별기 학습 → 비교
    evalrows = load_sets(AB_EVAL)
    prefix = json.loads((ROOT / "eval/report/final_rule_prefix.json").read_text(encoding="utf-8"))
    old = evaluate("지금 방식", a.old_onnx, a.old_tok, Vtr, Atr, evalrows, sp, prefix)
    new = evaluate("미세조정", a.new_onnx, a.new_tok, Vtr, Atr, evalrows, sp, prefix)
    out = {"note": "세트 9~12를 두 방식 모두 학습에서 뺀 비교. 연습 문장(합성)은 미세조정에만 씀.", "old": old, "new": new}
    p = ROOT / "eval/report/ai_finetune_ab.json"; p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
