"""브라우저용 '뜻 비교' AI 만들기 (GitHub Actions: .github/workflows/build_ai.yml 에서 실행).

1. jhgan/ko-sroberta-multitask 를 ONNX로 바꾸고 8비트로 줄인다 (optimum-cli 결과를 입력으로 받음)
2. 줄인 모델이 원래 모델과 같은 판단을 하는지, 묶음 하나씩 빼고 재기로 다시 확인한다
3. 상세페이지 문장을 구절로 나눠 비교하는 방식(브라우저와 똑같은 나누기)으로 기준값을 정한다
   - 평범한 문장(쇼핑 리뷰 표본)에서 AI가 '새로' 표시하는 문장이 목표 비율 이하가 되도록
4. 기준 문구(실제 적발 문구) 임베딩과 기준값을 web/ai/kb.json 으로 저장한다

    python tools/build_ai.py --onnx /tmp/onnx/model_quantized.onnx --tokenizer /tmp/onnx --reviews <리뷰 파일>
"""
import argparse, base64, csv, json, os, random, re, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from precheck import Checker  # noqa: E402

TARGET_FP = 0.01        # 평범한 문장 중 AI가 새로 표시해도 되는 비율
MAX_SENT_WORDS = 8      # 이보다 짧은 문장은 통째로도 비교


def log(m):
    print(m)
    if os.environ.get("GITHUB_ACTIONS"):
        print("::notice::" + m.replace("\n", " ## ")[:4000])


def windows(text):
    """브라우저(web/js/ai.js)와 똑같이 나눈다: 문장 → 어절 2·3개 묶음, 4글자 이상 어절, 짧은 문장 통째"""
    out = []
    for s in re.split(r"[.!?\n,·…~]+|\s{2,}", text):
        w = s.split()
        if not w: continue
        if len(w) <= MAX_SENT_WORDS: out.append(" ".join(w))
        for n in (2, 3):
            for i in range(0, max(0, len(w) - n + 1)):
                out.append(" ".join(w[i:i + n]))
        out += [x for x in w if len(x) >= 4]
    seen, res = set(), []
    for x in out:
        if x not in seen: seen.add(x); res.append(x)
    return res


class Embedder:
    def __init__(self, onnx_path, tok_dir):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.s = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self.t = Tokenizer.from_file(str(Path(tok_dir) / "tokenizer.json"))
        self.t.enable_truncation(128)
        self.t.no_padding()   # tokenizer.json에 패딩 설정이 들어 있으면 패딩 토큰까지 평균에 섞인다 (원인이었음)
        self.inputs = {i.name for i in self.s.get_inputs()}

    def __call__(self, texts, bs=64):
        outs = []
        for i in range(0, len(texts), bs):
            enc = self.t.encode_batch(texts[i:i + bs])
            L = max(len(e.ids) for e in enc)
            ids = np.array([e.ids + [1] * (L - len(e.ids)) for e in enc], dtype=np.int64)
            att = np.array([list(e.attention_mask) + [0] * (L - len(e.ids)) for e in enc], dtype=np.int64)
            feed = {"input_ids": ids, "attention_mask": att}
            if "token_type_ids" in self.inputs: feed["token_type_ids"] = np.zeros_like(ids)
            h = self.s.run(None, feed)[0]
            m = att[..., None].astype(np.float32)
            v = (h * m).sum(1) / np.clip(m.sum(1), 1e-9, None)          # 평균 풀링 (sentence-transformers 설정과 같음)
            outs.append(v / np.linalg.norm(v, axis=1, keepdims=True))
        return np.vstack(outs).astype(np.float32)


def load():
    V, A = [], []
    def add(path, b):
        for r in csv.DictReader(open(path, encoding="utf-8")):
            (V if r["label"] == "violation" else A if r["label"] == "allowed" else []).append((b, r["product_type"], r["text"]))
    add(ROOT / "data/eval_set.csv", "개발용")
    for f in ["test2", "test3", "test4", "test6", "test7"]:
        add(ROOT / f"data/{f}.csv", f)
    add(ROOT / "data/test5_batches.csv", "test5")
    seen = {re.sub(r"\W", "", t) for _, _, t in V}
    for r in csv.DictReader(open(ROOT / "data/enforcement/phrases.csv", encoding="utf-8")):
        if re.sub(r"\W", "", r["text"]) not in seen:
            seen.add(re.sub(r"\W", "", r["text"])); V.append(("적발문구", r["product_type"], r["text"]))
    return V, A


def reviews(path, n=2000):
    COS = re.compile(r"크림|로션|토너|세럼|에센스|앰플|선크림|샴푸|화장품|스킨|클렌징|마스크팩")
    FOOD = re.compile(r"맛있|먹|마셔|마시|차가|젤리|간식|과자|음료|영양제|즙|분말|스틱")
    out = []
    for line in open(path, encoding="utf-8"):
        s = line.rstrip("\n").split("\t", 1)[-1]
        t = "cos" if COS.search(s) else "food" if FOOD.search(s) else None
        if t: out.append((t, s))
    random.Random(0).shuffle(out)
    return out[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", required=True); ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--reviews", required=True); ap.add_argument("--fp32", help="비교용 원래 모델(sentence-transformers 이름)")
    ap.add_argument("--compare", help="진단용 ONNX 파일들(쉼표)"); ap.add_argument("--diag-only", action="store_true")
    a = ap.parse_args()
    emb = Embedder(a.onnx, a.tokenizer)
    ck = Checker()
    rule = lambda t, x: any(f.grade in ("red", "amber") for f in ck.check(x, t))
    V, A = load()
    R = reviews(a.reviews)
    EV = emb([x for _, _, x in V])

    # 0) 진단: 여러 변환본이 원래 모델과 얼마나 같은지
    if a.compare:
        from sentence_transformers import SentenceTransformer
        texts = [x for _, _, x in V][:200]
        ref = SentenceTransformer(a.fp32).encode(texts, normalize_embeddings=True)
        for pth in a.compare.split(","):
            e = Embedder(pth, a.tokenizer)(texts)
            log(f"진단 {Path(pth).name}: 원래 모델과 코사인 평균 {(ref * e).sum(1).mean():.4f}, 최소 {(ref * e).sum(1).min():.4f}")
    # 1) 원래 모델과 비교
    if a.fp32:
        from sentence_transformers import SentenceTransformer
        ref = SentenceTransformer(a.fp32).encode([x for _, _, x in V], normalize_embeddings=True)
        log(f"8비트 모델과 원래 모델의 임베딩 코사인: 평균 {(ref * EV).sum(1).mean():.4f}, 최소 {(ref * EV).sum(1).min():.4f}")

    if a.diag_only:
        return
    # 문장별 구절 임베딩 캐시
    cache = {}
    def wemb(texts):
        need = sorted({w for t in texts for w in windows(t)} - cache.keys())
        for w, e in zip(need, emb(need) if need else []): cache[w] = e
    def score(text, KB):
        ws = windows(text)
        if not ws: return 0.0, "", ""
        M = np.vstack([cache[w] for w in ws]) @ KB.T
        i, j = np.unravel_index(M.argmax(), M.shape)
        return float(M[i, j]), ws[i], j
    wemb([x for _, _, x in V] + [x for _, _, x in A] + [s for _, s in R])
    log(f"기준 문구 {len(V)}개, 허용 {len(A)}개, 리뷰 {len(R)}개, 비교한 구절 {len(cache)}개")

    def calibrate(KB):
        neg = [(t, x) for _, t, x in A] + R
        free = [score(x, KB)[0] for t, x in neg if not rule(t, x)]
        for c in np.arange(0.60, 0.999, 0.002):
            if np.mean([s >= c for s in free]) <= TARGET_FP: return float(c), float(np.mean([s >= c for s in free]))
        return 0.999, 0.0

    # 2) 묶음 하나씩 빼고 재기 (브라우저와 같은 구절 나누기)
    rows, tot = [], [0, 0, 0]
    for hb in ["test3", "test4", "test5", "test6", "test7"]:
        ti = [i for i, v in enumerate(V) if v[0] == hb]
        KB = EV[[i for i, v in enumerate(V) if v[0] != hb]]
        th, fp = calibrate(KB)
        r = [rule(V[i][1], V[i][2]) for i in ti]
        e = [score(V[i][2], KB)[0] >= th for i in ti]
        b = [x or y for x, y in zip(r, e)]
        rows.append(f"{hb}: 규칙 {sum(r)}/{len(ti)} → 규칙+AI {sum(b)}/{len(ti)} (기준값 {th:.3f}, 평범한 문장 새 표시 {fp * 100:.2f}%)")
        tot[0] += len(ti); tot[1] += sum(r); tot[2] += sum(b)
    log("묶음 하나씩 빼고 재기 (8비트 모델, 구절 나누기): " + " / ".join(rows))
    log(f"합계: 규칙 {tot[1] / tot[0] * 100:.1f}% → 규칙+AI {tot[2] / tot[0] * 100:.1f}% (처음 보는 문구 {tot[0]}개)")

    # 3) 최종: 모든 적발 문구를 기준으로 기준값을 다시 정하고 저장
    th, fp = calibrate(EV)
    q = np.clip(np.round(EV * 127), -127, 127).astype(np.int8)        # 8비트로 저장 (복원: /127)
    out = {
        "model": "ko-sroberta-multitask (jhgan) · ONNX 8비트", "dim": int(EV.shape[1]), "threshold": round(th, 4),
        "target_fp": TARGET_FP, "measured_fp": round(fp, 4), "max_sent_words": MAX_SENT_WORDS,
        "note": "실제 적발 문구와 뜻이 가까운 구절을 '확인 필요'로 알려 주는 용도. 기존 규칙 판정과는 따로 보여 준다.",
        "phrases": [{"t": x, "type": t} for _, t, x in V],
        "emb": base64.b64encode(q.tobytes()).decode(),
    }
    p = ROOT / "web/ai/kb.json"; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    # 브라우저 결과와 맞춰 보기 위한 확인용 값
    probe = ["피부 재생 크림", "탈모에 좋은 차", "촉촉한 보습 로션", "아이 키 크는 젤리"]
    log("최종 기준값 %.3f (평범한 문장 새 표시 %.2f%%) · 확인용 점수 %s" % (th, fp * 100, {x: round(score(x, EV)[0], 4) for x in (wemb(probe) or probe)}))
    (ROOT / "web/ai/probe.json").write_text(json.dumps({x: round(score(x, EV)[0], 4) for x in probe}, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
