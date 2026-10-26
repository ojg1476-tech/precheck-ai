"""무료 OCR(Tesseract) 실험: 쉬운 페이지 3장 + 어려운 페이지 3장.

1) 글자 정확도: 정답 문장마다 OCR 결과에서 가장 비슷한 줄을 찾아 글자 일치율(1 - 편집거리/길이)을 잰다.
2) 검사 결과: 정답 문장과 짝지은 OCR 줄을 규칙으로 검사해, 원문으로 검사했을 때와 같은 결과가 나오는지 본다.
실행: python eval/page_test/score_free.py [--tessdata 폴더]
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

H = Path(__file__).parent
ROOT = H.parent.parent
sys.path.insert(0, str(ROOT))
from precheck import Checker, ocr  # noqa: E402

norm = lambda s: re.sub(r"[\s·,—\-.ㆍ]", "", s)


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def best_line(text, lines):
    """정답 문장과 가장 비슷한 OCR 구간(연속 1~2줄)."""
    cands = lines + [a + b for a, b in zip(lines, lines[1:])]
    if not cands:
        return "", 0.0
    t = norm(text)
    best = max(cands, key=lambda c: difflib.SequenceMatcher(None, t, norm(c)).ratio())
    acc = max(0.0, 1 - lev(t, norm(best)) / max(1, len(t)))
    return best, acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tessdata")
    ap.add_argument("--set", default="dev", choices=["dev", "test"],
                    help="dev = 쉬운·어려운 페이지 6장(개선 작업용), test = 고정해 둔 시험 페이지 3장")
    args = ap.parse_args()
    ck = Checker()
    files = ["truth.json", "truth_hard.json"] if args.set == "dev" else ["truth_test.json"]
    truth = {}
    for f in files:
        truth.update(json.loads((H / f).read_text(encoding="utf-8")))
    runs, rows = {}, []
    for pid, t in truth.items():
        text = ocr.read_text_free([(H / "pages" / f"{pid}.png").read_bytes()], tessdata=args.tessdata)
        runs[pid] = text
        lines = [l for l in text.splitlines() if l.strip()]
        for b in t["blocks"]:
            got, acc = best_line(b["text"], lines)
            want = bool(ck.check(b["text"], t["type"]))      # 원문 그대로 검사했을 때
            have = bool(ck.check(got, t["type"])) if acc >= 0.5 else False
            rows.append({"page": pid, "group": "시험 페이지" if pid.startswith("test_") else
                         "어려운 페이지" if pid.startswith("hard_") else "쉬운 페이지", "text": b["text"], "label": b["label"],
                         "ocr": got, "acc": round(acc, 3), "flag_truth": want, "flag_ocr": have})
    (H / "runs" / f"tesseract_{args.set}.json").write_text(json.dumps(runs, ensure_ascii=False, indent=1), encoding="utf-8")

    res = {}
    for group in dict.fromkeys(r["group"] for r in rows):
        rs = [r for r in rows if r["group"] == group]
        flagged = [r for r in rs if r["flag_truth"]]
        res[group] = {
            "문장": len(rs),
            "평균 글자 정확도": round(sum(r["acc"] for r in rs) / len(rs), 3),
            "거의 그대로 읽은 문장(95% 이상)": sum(r["acc"] >= 0.95 for r in rs),
            "원문이면 규칙이 잡는 문장": len(flagged),
            "OCR 글로도 잡은 문장": sum(r["flag_ocr"] for r in flagged),
            "OCR 때문에 놓친 문장": [f"{r['text']} → {r['ocr']}" for r in flagged if not r["flag_ocr"]],
            "OCR 때문에 새로 걸린 평범한 문장": [r["text"] for r in rs if r["flag_ocr"] and not r["flag_truth"]],
        }
    (H / f"results_free_{args.set}.json").write_text(json.dumps({"summary": res, "rows": rows}, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
