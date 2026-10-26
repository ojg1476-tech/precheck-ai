"""단속 데이터 분석과 v3.2 규칙 확인. python tests/test_enforcement.py 로도 실행."""
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck import Checker  # noqa: E402

TYPES = ["질병예방치료", "의약품오인", "건기식오인", "거짓과장", "체험기기만", "심의위반", "기능성오인", "소비자오인", "기타"]


def test_inspection_totals():
    # 유형이 공개된 발표는 유형 합 = 적발 합, 모든 행에 출처가 있다
    for r in csv.DictReader(open(ROOT / "data/enforcement/inspections.csv", encoding="utf-8")):
        s = sum(int(r[t] or 0) for t in TYPES)
        assert r["source_url"].startswith("https://"), r["id"]
        assert s == 0 or s == int(r["total"]) or "미기재" in r["note"], r["id"]


def test_v32_new_phrases():
    ck = Checker()
    for text, t in [("집중력 강화", "food"), ("두뇌 건강", "food"), ("키 성장", "food"), ("전 피로에 더 좋았어요", "food"),
                    ("지방세포 증식", "cos"), ("모발성장촉진", "cos"), ("11살은 어려집니다", "cos")]:
        assert ck.check(text, t), text
    for text, t in [("포장이 좋았어요", "food"), ("두뇌 회전이 빠른 퍼즐 상자", "cos"), ("아이 키에 맞춘 컵 크기", "food")]:
        assert not ck.check(text, t), text


def test_analysis_runs():
    out = subprocess.run([sys.executable, str(ROOT / "analysis/enforcement.py")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "분석 전 규칙(v3.1) 16개 → 지금(v3.2) 23개" in out.stdout


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f()
        print("통과:", f.__name__)
    print(f"{len(fns)}/{len(fns)} 통과")
