"""건강기능식품 원료 대조: 손으로 만든 문구 모두 맞히기 + 실제 신고 제품에서 잘못 잡는 비율 1% 미만 유지. python tests/test_hfood.py"""
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from precheck.engine import Checker  # noqa: E402


def test_hand_cases():
    ck = Checker()
    rows = list(csv.DictReader(open(ROOT / "data/hfood_test.csv", encoding="utf-8")))
    bad = []
    for r in rows:
        got = sorted({f.rule_id for f in ck.check(r["text"], "hfood", name=r.get("name", "")) if f.rule_id.startswith("H")}) or ["none"]
        ok = (r["expect"] in got) if r["expect"] != "none" else got == ["none"]
        if not ok:
            bad.append((r["id"], r["expect"], got))
    assert not bad, bad
    print(f"손으로 만든 문구 {len(rows)}/{len(rows)} 맞음")


def test_real_products():
    out = subprocess.run([sys.executable, str(ROOT / "eval/hfood/evaluate_hfood.py")], capture_output=True, text=True, check=True).stdout
    r = json.loads(out)
    assert r["recog_rate"] > 0.95 and r["b_fp_rate"] < 0.01, r
    print(f"실제 신고 제품 {r['products']}개: 원료 인식 {r['recog_rate']:.1%}, 인정 문구를 잘못 잡은 비율 {r['b_fp_rate']:.2%}")


def test_report_no_and_name():
    out = subprocess.run([sys.executable, str(ROOT / "eval/hfood/evaluate_products.py")], capture_output=True, text=True, check=True).stdout
    r = json.loads(out)
    assert r["own_fp_rate"] < 0.005 and r["other_any_rate"] > 0.95 and r["name_ok_rate"] > 0.9 and r["name_wrong_rate"] < 0.01, r
    print(f"신고번호 대조: 신고 문구 오탐 {r['own_fp_rate']:.2%}, 신고 안 한 기능 적발 {r['other_any_rate']:.1%} · 상품명으로 찾기 {r['name_ok_rate']:.1%} (다른 제품 {r['name_wrong_rate']:.2%})")


def test_examples_are_fictional():
    """예시 상품은 가상의 이름이라 실제 신고 제품과 이어지면 안 됨"""
    ck = Checker()
    items = json.loads((ROOT / "examples/examples.json").read_text(encoding="utf-8"))["items"]
    for it in items:
        assert it["type"] in ("cos", "fcos", "food", "hfood"), it
        ck.check(it["text"], it["type"], name=it["name"])
        assert ck.last_product is None, (it["name"], ck.last_product)
    print(f"예시 상품 {len(items)}개: 실제 제품과 이어지지 않음")


if __name__ == "__main__":
    test_examples_are_fictional()
    test_hand_cases()
    test_real_products()
    test_report_no_and_name()
