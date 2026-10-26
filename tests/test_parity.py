"""Python 엔진이 웹 검사기(JS)와 똑같은 결과를 내는지 확인. node 필요."""
import csv, json, shutil, subprocess, sys
from pathlib import Path
try:
    import pytest
except ImportError:  # pytest 없이도 python tests/test_parity.py 로 실행 가능
    pytest = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck import Checker

SAMPLES = [
    ("cos", "피부 재생 크림! 염증을 잡아주고 여드름 완화에 탁월. 진피층까지 흡수돼 주름 개선. 부작용 없는 피부과 추천 1위 제품, 7일 만에 변화. 노폐물 제거, 붓기 완화."),
    ("fcos", "주름 개선 기능성 화장품. 미백에 도움. 임상 완료, 파라벤 프리, 비건 인증."),
    ("food", "면역력 강화에 좋은 영양제 같은 차. 혈당 조절, 피로 회복, 변비 해결. 체험기 다수, 한방 특수제법."),
    ("hfood", "면역력 증진, 혈당 조절, 피로 회복에 도움을 줄 수 있음. 약 대신 드세요. 후기 폭발."),
]
if (ROOT / "data" / "eval_set.csv").exists():
    with open(ROOT / "data" / "eval_set.csv", encoding="utf-8") as f:
        SAMPLES += [(r["product_type"], r["text"]) for r in csv.DictReader(f)]


def _check(ptype, text):
    js = json.loads(subprocess.run(["node", str(ROOT / "tools" / "js_check.js"), ptype],
                                   input=text, capture_output=True, text=True, check=True).stdout)
    py = [{"start": f.start, "end": f.end, "grade": f.grade} for f in Checker().check(text, ptype)]
    assert py == js


if pytest:
    @pytest.mark.skipif(not shutil.which("node"), reason="node 없음")
    @pytest.mark.parametrize("ptype,text", SAMPLES)
    def test_same_as_web(ptype, text):
        _check(ptype, text)

if __name__ == "__main__":
    fails = 0
    for p, t in SAMPLES:
        try:
            _check(p, t)
        except AssertionError:
            fails += 1
            print("다름:", p, t[:40])
    print(f"{len(SAMPLES) - fails}/{len(SAMPLES)} 웹 버전과 같음")
    sys.exit(1 if fails else 0)
