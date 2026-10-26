"""이미지 상세페이지 실험 채점: 그냥 AI(이미지) vs 규칙(옮겨 적은 글) vs 규칙+기준표 AI."""
import json, re
from pathlib import Path
H = Path(__file__).parent
truth = json.loads((H / "truth.json").read_text())
cats = json.loads((H.parent.parent / "rules" / "rules.json").read_text())["categories"]
BLUE = {"CP", "CB", "CX", "HF", "FP"}
norm = lambda s: re.sub(r"[\s·,—\-.]", "", s)

def block_of(page, phrase):
    p = norm(phrase)
    for i, b in enumerate(truth[page]["blocks"]):
        if p and (p in norm(b["text"]) or norm(b["text"]) in p):
            return i
    return None

def load(kind):
    out = []  # (page, block, level)  level: strong(위반) / soft(자료필요·확인)
    if kind == "A":
        for pg, ph, v in json.loads((H / "runs/plainA.json").read_text()):
            out.append((pg, block_of(pg, ph), "strong" if v == "위반" else "soft"))
    else:
        for pg, items in json.loads((H / "runs/rules.json").read_text()).items():
            for f in items:
                out.append((pg, block_of(pg, f["phrase"]), "soft" if f["grade"] == "blue" else "strong"))
        if kind == "C":
            for pg, ph, cat in json.loads((H / "runs/criteriaAI.json").read_text()):
                if cat in cats:
                    out.append((pg, block_of(pg, ph), "soft" if cat in BLUE else "strong"))
    return out

res = {}
for kind, name in [("A", "그냥 AI (이미지 통째로)"), ("B", "규칙만 (옮겨 적은 글)"), ("C", "규칙 + 기준표 AI")]:
    hits = load(kind)
    unmatched = sum(1 for h in hits if h[1] is None)
    s = {"viol": [0, 0], "cond": [0, 0], "fp_strong": [0, 0], "fp_soft": [0, 0], "missed": [], "extra": []}
    for pg, t in truth.items():
        for i, b in enumerate(t["blocks"]):
            lv = {h[2] for h in hits if h[0] == pg and h[1] == i}
            if b["label"] == "violation":
                s["viol"][1] += 1; s["viol"][0] += bool(lv)
                if not lv: s["missed"].append(b["text"])
            elif b["label"] == "conditional":
                s["cond"][1] += 1; s["cond"][0] += bool(lv)
                if not lv: s["missed"].append(b["text"] + " (자료 필요)")
            else:
                s["fp_strong"][1] += 1; s["fp_soft"][1] += 1
                if "strong" in lv: s["fp_strong"][0] += 1; s["extra"].append(b["text"] + " (위반)")
                elif "soft" in lv: s["fp_soft"][0] += 1; s["extra"].append(b["text"] + " (확인 요청)")
    s["unmatched"] = unmatched
    res[name] = s
(H / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
for n, s in res.items():
    print(n, "| 위반", s["viol"], "| 자료필요", s["cond"], "| 평범 문구 위반 판정", s["fp_strong"], "| 평범 문구 확인 요청", s["fp_soft"], "| 매칭 안 됨", s["unmatched"])
    print("   놓침:", s["missed"]); print("   괜히 잡음:", s["extra"])
