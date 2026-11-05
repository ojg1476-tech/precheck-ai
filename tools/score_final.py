"""배포된 AI(web/ai/kb.json)를 다시 학습하지 않고, 고정한 최종 시험 세트를 그대로 채점한다 (2026-11-05).
웹 검사기와 같게: 규칙에 안 걸린 문장만 AI가 보고, 건강기능식품·기능성 화장품은 AI를 쓰지 않는다.
GitHub Actions(.github/workflows/score_final.yml) → eval/report/ai_final.json 에 세트별로 더한다.

    python tools/score_final.py --onnx model.onnx --tokenizer DIR test15
"""
import argparse, base64, csv, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_ai as B  # noqa: E402

DOM = {"cos": "cos", "fcos": "cos", "food": "food", "hfood": "food"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", required=True); ap.add_argument("--tokenizer", required=True); ap.add_argument("sets", nargs="+")
    a = ap.parse_args()
    emb = B.Embedder(a.onnx, a.tokenizer); ck = B.Checker()
    lr = json.loads((ROOT / "web/ai/kb.json").read_text(encoding="utf-8"))["lr"]
    w = np.frombuffer(base64.b64decode(lr["w"]), dtype=np.float32); b = lr["b"]
    th = {"cos": lr.get("threshold_cos", lr["threshold"]), "food": lr.get("threshold_food", lr["threshold"])}
    fp = ROOT / "eval/report/ai_final.json"
    out = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
    for name in a.sets:
        rows = [r for r in csv.DictReader(open(ROOT / f"data/{name}.csv", encoding="utf-8")) if r["label"] in ("violation", "allowed")]
        res = []
        for r in rows:
            t, x = r["product_type"], r["text"]
            rule = any(f.grade in ("red", "amber") for f in ck.check(x, t))
            ai = False
            if t not in ("hfood", "fcos"):
                ws = B.windows(x)
                ai = bool(ws) and float(np.max(emb(ws) @ w + b)) > th[DOM[t]]
            res.append({"type": t, "label": r["label"], "text": x, "rule": rule, "ai": ai})
        v = [z for z in res if z["label"] == "violation"]; al = [z for z in res if z["label"] == "allowed"]
        B.log(f"최종 시험 {name}: 규칙 {sum(z['rule'] for z in v)} → 규칙+AI {sum(z['rule'] or z['ai'] for z in v)} / {len(v)} · "
              f"허용 오탐 규칙 {sum(z['rule'] for z in al)} · 규칙+AI {sum(z['rule'] or z['ai'] for z in al)} / {len(al)}")
        for z in res:
            B.log(f"  {z['label']} 규칙={'O' if z['rule'] else '-'} AI={'O' if z['ai'] else '-'} {z['text']}")
        out[name] = res
    fp.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")


if __name__ == "__main__":
    main()
