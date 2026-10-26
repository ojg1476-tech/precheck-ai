"""일괄 점검·리포트·이미지 읽기 모듈 테스트 (실제 API 호출 없음). python tests/test_batch.py 로도 실행."""
import io
import json
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image  # noqa: E402

from precheck import check_products, read_table  # noqa: E402
from precheck import ocr  # noqa: E402
from precheck.batch import normalize_type, penalty_text  # noqa: E402
from precheck.report import build_report  # noqa: E402

SAMPLE = ROOT / "examples" / "sample_products.csv"


def test_read_and_rank():
    res = check_products(read_table(SAMPLE.read_bytes(), "s.csv"))
    tiers = [r.tier for r in res]
    assert tiers[0] == "높음" and tiers[-1] == "오류"          # 위험한 상품이 먼저, 빈 문구는 맨 끝
    assert tiers.index("양호") > tiers.index("확인")
    top = res[0]
    assert top.max_penalty == (10, 100_000_000)               # 식품 질병·의약품·건기식 오인 → 10년/1억
    names = {r.name: r.tier for r in res}
    assert names["현미 누룽지"] == "양호" and names["클렌징 폼"] == "양호"


def test_type_aliases():
    assert normalize_type("건강기능식품") == "hfood" and normalize_type(" 일반 화장품 ") == "cos"
    try:
        normalize_type("의약품")
        assert False
    except ValueError:
        pass


def test_xlsx_input_and_report():
    from openpyxl import Workbook, load_workbook
    wb = Workbook()
    wb.active.append(["제품명", "종류", "내용"])
    wb.active.append(["차", "식품", "감기 예방 차"])
    buf = io.BytesIO()
    wb.save(buf)
    res = check_products(read_table(buf.getvalue(), "a.xlsx"))
    assert res[0].tier == "높음"
    out = load_workbook(io.BytesIO(build_report(res)))
    assert out.sheetnames == ["요약", "위험 순위", "상세", "기준 안내"]
    assert out["위험 순위"].cell(row=2, column=2).value == "차"


def test_penalty_text():
    assert penalty_text((10, 100_000_000)) == "징역 10년 이하 또는 벌금 1억 원 이하"
    assert penalty_text((1, 10_000_000)) == "징역 1년 이하 또는 벌금 1,000만 원 이하"


def _png(w, h):
    b = io.BytesIO()
    Image.new("RGB", (w, h), "white").save(b, format="PNG")
    return b.getvalue()


def test_slice_long_image():
    chunks = ocr.slice_image(_png(860, 10000))
    sizes = [Image.open(io.BytesIO(c)).size for c in chunks]
    assert all(w == 860 and h <= ocr.CHUNK_HEIGHT for w, h in sizes)
    assert sum(h for _, h in sizes) >= 10000                   # 겹침 때문에 원본보다 같거나 길다
    assert Image.open(io.BytesIO(ocr.slice_image(_png(2000, 500))[0])).size[0] == ocr.MAX_WIDTH


def test_read_text_mocked():
    fake = {"content": [{"type": "text", "text": "감기 예방 차"}], "usage": {"input_tokens": 12000, "output_tokens": 300}}

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps(fake).encode()

    with mock.patch("urllib.request.urlopen", return_value=R()) as m:
        r = ocr.read_text([_png(860, 4000)], api_key="test")
    sent = json.loads(m.call_args[0][0].data)
    assert sent["model"] == ocr.DEFAULT_MODEL and sum(c["type"] == "image" for c in sent["messages"][0]["content"]) == 3
    assert r.text == "감기 예방 차" and round(r.usd, 5) == round(12000 / 1e6 * 0.10 + 300 / 1e6 * 0.50, 5)


def test_free_ocr_dark_block_inverted():
    im = Image.new("L", (1400, 300), 255)
    im.paste(20, (0, 100, 1400, 200))          # 어두운 배경 띠
    for x in range(100, 1300, 30):
        im.paste(240, (x, 130, x + 12, 170))   # 그 위 흰 글씨
    blk = ocr.text_blocks(im)
    import numpy as np
    assert len(blk) == 1 and np.median(np.asarray(blk[0])) > 127   # 뒤집혀 밝은 바탕


def test_free_ocr_cleanup_and_dedupe():
    raw = "피부과 전문의가 직접 개발\n은\n=\nJ\nofo\n끈적임 없이 산뜻하게"
    assert ocr._clean(raw) == "피부과 전문의가 직접 개발\n끈적임 없이 산뜻하게"

    class P:  # 글 덩어리 두 개를 차례로 읽은 상황 (같은 줄이 이어지면 하나만 남긴다)
        def __init__(self, out): self.returncode, self.stdout, self.stderr = 0, out, ""
    outs = iter([P("첫 줄 문장입니다\n겹치는 줄입니다"), P("겹치는 줄입니다\n마지막 줄입니다")])
    im = Image.new("L", (1400, 600), 255)
    for y0 in (100, 400):                      # 무늬 있는 띠 두 개 = 글 덩어리 두 개
        for x in range(0, 1400, 20):
            im.paste(0, (x, y0, x + 10, y0 + 60))
    b = io.BytesIO(); im.save(b, format="PNG")
    assert len(ocr.text_blocks(im)) == 2
    with mock.patch("shutil.which", return_value="/usr/bin/tesseract"), \
         mock.patch("subprocess.run", side_effect=lambda *a, **k: next(outs)):
        text = ocr.read_text_free([b.getvalue()])
    assert text.splitlines() == ["첫 줄 문장입니다", "겹치는 줄입니다", "마지막 줄입니다"]


if __name__ == "__main__":
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    for f in fns:
        f()
        print("통과:", f.__name__)
    print(f"{len(fns)}/{len(fns)} 통과")
