"""뜻 비교(문장 임베딩) 실험 — 묶음 하나씩 빼고 재기 (leave-one-batch-out).

- 지식: 빼 둔 묶음을 제외한 모든 실제 적발 문구
- 판정: 새 문장과 가장 가까운 적발 문구의 유사도가 기준값 이상이면 '의심'
- 기준값: 빼 둔 묶음은 보지 않고, 평범한 문장(허용 문장 + 리뷰 표본)에서 오탐률이 목표 이하가 되도록 정함
- 규칙(v4)과 합치면(둘 중 하나라도 걸리면) 얼마나 오르는지도 잰다

GitHub Actions에서 실행(.github/workflows/embed.yml). 결과는 주석(annotation)과 eval/experiments/embed_result.md로 남긴다.
"""
import csv, os, re, sys, random, json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from precheck import Checker  # noqa: E402

MODEL = os.environ.get("EMBED_MODEL", "intfloat/multilingual-e5-small")
REVIEWS = os.environ.get("REVIEWS", "")


def log(m):
    print(m)
    if os.environ.get("GITHUB_ACTIONS"):
        print("::notice::" + m.replace("\n", " | ")[:1000])


def load():
    V, A = [], []
    def add(path, batch_of):
        for r in csv.DictReader(open(path, encoding="utf-8")):
            b = batch_of(r)
            (V if r["label"] == "violation" else A if r["label"] == "allowed" else []).append((b, r["product_type"], r["text"]))
    add(ROOT / "data/eval_set.csv", lambda r: "개발용")
    for f in ["test2", "test3", "test4", "test6", "test7"]:
        add(ROOT / f"data/{f}.csv", lambda r, f=f: f)
    add(ROOT / "data/test5_batches.csv", lambda r: "test5")
    seen = {re.sub(r"\W", "", t) for _, _, t in V}
    for r in csv.DictReader(open(ROOT / "data/enforcement/phrases.csv", encoding="utf-8")):
        if re.sub(r"\W", "", r["text"]) not in seen:
            V.append(("적발문구", r["product_type"], r["text"]))
    return V, A


def reviews(n=3000, seed=0):
    if not REVIEWS or not Path(REVIEWS).exists():
        return []
    COS = re.compile(r"크림|로션|토너|세럼|에센스|앰플|선크림|샴푸|화장품|스킨|클렌징|마스크팩")
    FOOD = re.compile(r"맛있|먹|마셔|마시|차가|젤리|간식|과자|음료|영양제|즙|분말|스틱")
    out = []
    for line in open(REVIEWS, encoding="utf-8"):
        s = line.rstrip("\n").split("\t", 1)[-1]
        t = "cos" if COS.search(s) else "food" if FOOD.search(s) else None
        if t: out.append(("리뷰", t, s))
    random.Random(seed).shuffle(out)
    return out[:n]


def main():
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MODEL)
    pre = "query: " if "e5" in MODEL else ""
    enc = lambda xs: m.encode([pre + x for x in xs], normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    V, A = load()
    R = reviews()
    ck = Checker()
    rule = lambda t, x: any(f.grade in ("red", "amber") for f in ck.check(x, t))
    EV, EA, ER = enc([x for _, _, x in V]), enc([x for _, _, x in A]), enc([x for _, _, x in R]) if R else np.zeros((0, 1))
    batches = ["test3", "test4", "test5", "test6", "test7"]
    lines = [f"모델: {MODEL} · 적발 문구 {len(V)}개 · 허용 {len(A)}개 · 리뷰 {len(R)}개", "",
             "| 빼 둔 묶음 | 문구 | 규칙 v4 | 뜻 비교만 | 규칙+뜻 비교 | 기준값 | 평범한 문장 오탐(규칙+뜻) |", "| --- | --- | --- | --- | --- | --- | --- |"]
    tot = [0, 0, 0, 0]
    for target in ["fpr1", "fpr05"]:
        cap = 0.01 if target == "fpr1" else 0.005
        lines.append(f"| **오탐 목표 {cap * 100:.1f}%** | | | | | | |")
        for hb in batches:
            ti = [i for i, v in enumerate(V) if v[0] == hb]
            ki = [i for i, v in enumerate(V) if v[0] != hb]
            if not ti: continue
            KB = EV[ki]
            # 평범한 문장(허용 + 리뷰)에서 기준값 정하기 — 빼 둔 묶음은 보지 않음
            neg = np.vstack([EA, ER]) if len(R) else EA
            neg_s = (neg @ KB.T).max(1)
            neg_rule = [rule(t, x) for _, t, x in A + R]
            th = None
            for c in np.arange(0.80, 0.999, 0.002):
                fp = np.mean([(s >= c) or r for s, r in zip(neg_s, neg_rule)])
                if fp <= cap: th = float(c); break
            th = th or 0.999
            fp = float(np.mean([(s >= th) or r for s, r in zip(neg_s, neg_rule)]))
            s = (EV[ti] @ KB.T).max(1)
            r_hit = [rule(V[i][1], V[i][2]) for i in ti]
            e_hit = [bool(x >= th) for x in s]
            both = [a or b for a, b in zip(r_hit, e_hit)]
            n = len(ti)
            lines.append(f"| {hb} | {n} | {sum(r_hit) / n * 100:.1f}% | {sum(e_hit) / n * 100:.1f}% | **{sum(both) / n * 100:.1f}%** | {th:.3f} | {fp * 100:.2f}% |")
            if target == "fpr1":
                tot[0] += n; tot[1] += sum(r_hit); tot[2] += sum(e_hit); tot[3] += sum(both)
    lines.insert(4, "")
    lines.append("")
    lines.append(f"합계(오탐 목표 1%): 규칙 {tot[1] / tot[0] * 100:.1f}% → 뜻 비교 {tot[2] / tot[0] * 100:.1f}% → 규칙+뜻 비교 {tot[3] / tot[0] * 100:.1f}% (문구 {tot[0]}개)")
    out = ROOT / f"eval/experiments/embed_result_{MODEL.split('/')[-1]}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for l in lines: log(l)


if __name__ == "__main__":
    main()
