"""웹 검사기(precheck.html)의 규칙 부분을 tools/rules_web.js로 교체한다. 사용: python tools/splice_web.py <precheck.html>
규칙 블록 = 'const COS=' 부터 마지막 'function lawFor' 줄까지. 교체 후 중복 함수가 없는지 확인한다."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
page = Path(sys.argv[1])
h = page.read_text(encoding="utf-8")
rules = (ROOT / "tools" / "rules_web.js").read_text(encoding="utf-8").rstrip()
helpers = ('function catOf(f){return f.cat||(f.rule?(isCos()?f.rule.catC:f.rule.catF):"")||"";}\n'
           'function checksFor(f){const c=CAT[catOf(f)];return c?c.checks:[];}\n')
a = h.index("const COS=")
ends = [m.end() for m in re.finditer(r"function lawFor\(f\)\{[^\n]*\n", h)]
b = ends[-1]
for fn in ("function catOf(", "function checksFor("):  # 이전 교체 때 넣은 도우미 줄은 같이 바꾼다
    if h.startswith(fn, b):
        b = h.index("\n", b) + 1
h = h[:a] + rules + "\n" + helpers + h[b:]
for name in ("function riskFor(", "function lawFor(", "function catOf(", "function checksFor(", "const COS=", "const RULES="):
    n = h.count(name)
    assert n == 1, f"{name} {n}번"
page.write_text(h, encoding="utf-8")
print("교체 완료:", page)
