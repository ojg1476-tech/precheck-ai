"""어려운 버전의 가상 상세페이지 (무료 OCR 실험용).

같은 문장(정답표 그대로)을 실제 상세페이지처럼 어렵게 그린다:
세로 1만 px 이상, 사진 같은 배경 위 글씨, 얇은 글꼴·외곽선·그림자, 기울인 글씨, 작은 연회색 글씨.
출력: eval/page_test/pages/hard_*.html (+ shoot_pages.js로 png), truth_hard.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval" / "page_test"
truth = json.loads((OUT / "truth.json").read_text(encoding="utf-8"))
THEME = {"p1_cream": ("#e8f1f4", "#1d4f63"), "p2_tea": ("#fbf1e1", "#7a3e0b"), "p3_omega": ("#e9f0fb", "#173f7a")}

CSS = """*{box-sizing:border-box}body{margin:0;width:860px;font-family:'Noto Sans CJK KR',sans-serif;background:%(bg)s;color:#222}
.sec{padding:70px 48px;text-align:center;position:relative}
.photo{height:1100px;background:
  radial-gradient(circle at 30%% 40%%,#ffffff88 0 8%%,transparent 30%%),
  repeating-linear-gradient(115deg,%(fg)s33 0 14px,%(fg)s11 14px 31px),
  linear-gradient(160deg,%(fg)s,%(bg)s)}
.s0{font-size:52px;font-weight:100;letter-spacing:.06em;color:%(fg)s}
.s1{font-size:40px;font-weight:900;color:#fff;-webkit-text-stroke:2px %(fg)s;text-shadow:4px 4px 0 %(fg)s88;
    background:repeating-radial-gradient(circle at 20%% 30%%,%(fg)s 0 6px,%(fg)scc 6px 13px)}
.s2{font-size:30px;font-weight:300;color:%(fg)sbb;background:linear-gradient(90deg,#fff,%(bg)s 50%%,#fff)}
.s3{font-size:34px;font-weight:700;color:#fff;transform:rotate(-4deg);background:%(fg)s;margin:40px 60px;border-radius:30px}
.s4{font-size:26px;font-weight:500;color:#fff;text-shadow:0 0 8px #000;
    background:repeating-conic-gradient(from 20deg,%(fg)s 0 10deg,#c9a26b 10deg 22deg,%(bg)s 22deg 31deg)}
.s5{font-size:15px;color:#aaa;background:#fafafa;text-align:left}
.s6{font-size:36px;font-weight:800;color:%(fg)s;background:linear-gradient(transparent 60%%,#ffe36e 60%%);display:inline-block}
.s7{font-family:'Noto Serif CJK KR','Noto Sans CJK KR',serif;font-size:30px;font-style:italic;color:#555;letter-spacing:.12em}"""

out = {}
for pid, t in truth.items():
    bg, fg = THEME[pid]
    parts = []
    for i, b in enumerate(t["blocks"]):
        style = f"s{i % 8}"
        inner = f'<span class="{style}">{b["text"]}</span>' if style == "s6" else b["text"]
        cls = "" if style == "s6" else style
        parts.append(f'<div class="sec {cls}">{inner}</div>')
        if i % 2 == 1:
            parts.append('<div class="photo"></div>')
    html = f"<!doctype html><meta charset=utf-8><style>{CSS % {'bg': bg, 'fg': fg}}</style>" + "".join(parts)
    (OUT / "pages" / f"hard_{pid}.html").write_text(html, encoding="utf-8")
    out[f"hard_{pid}"] = t
(OUT / "truth_hard.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", list(out))
