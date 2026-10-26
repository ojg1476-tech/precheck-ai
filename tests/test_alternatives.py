"""'대신 이렇게' 문구가 같은 기준으로 다시 검사해도 걸리지 않는지 확인 (자료 챙기기 등급은 허용)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from precheck import Checker  # noqa: E402


def bad_alternatives():
    ck = Checker()
    alts = {(r["alt"], t) for r in ck.rules for t in r["applies_to"]}
    for code, c in ck.categories.items():
        for t in (("cos", "fcos") if code.startswith("C") else ("food", "hfood")):
            alts.add((c["alt"], t))
    out = []
    for alt, t in sorted(alts):
        hits = [f.phrase for f in ck.check(alt, t) if f.grade != "blue"]
        if hits:
            out.append((t, alt, hits))
    return out, len(alts)


def test_alternatives_pass():
    bad, _ = bad_alternatives()
    assert not bad, bad


if __name__ == "__main__":
    bad, n = bad_alternatives()
    for b in bad:
        print("걸림:", b)
    print(f"{n - len(bad)}/{n} 대안 문구 통과")
    sys.exit(1 if bad else 0)
