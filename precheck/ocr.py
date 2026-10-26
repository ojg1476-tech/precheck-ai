"""상세페이지 이미지 → 글자 (Claude API). API 키가 있을 때만 쓴다.

- 세로로 긴 이미지는 글자가 작아지지 않도록 조각으로 잘라 보낸다 (조각마다 겹치는 부분을 둬 줄이 잘리지 않게).
- SDK 없이 표준 라이브러리(urllib)로 Messages API를 부른다.
- 비용: 이미지 토큰 = ⌈가로/28⌉ × ⌈세로/28⌉ (Claude 문서 기준), 가격은 아래 PRICE (2026-10 확인).
"""
from __future__ import annotations

import base64
import io
import json
import math
import urllib.request
from dataclasses import dataclass

from PIL import Image

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-haiku-5-5"
# 백만 토큰당 달러 (입력, 출력) — https://platform.claude.com/docs/en/about-claude/pricing
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}
MAX_WIDTH = 1000      # 가로가 이보다 넓으면 줄인다
CHUNK_HEIGHT = 1800   # 조각 높이 (긴 변 2,576px 한도 안)
OVERLAP = 80          # 조각끼리 겹치는 높이

PROMPT = ("첨부한 이미지들은 한 상품 상세페이지를 위에서 아래로 자른 조각이에요(조각끼리 조금 겹쳐요). "
          "이미지에 적힌 글자를 위에서 아래 순서대로 빠짐없이 그대로 옮겨 적어 주세요. 해석·요약·판단은 하지 말고, "
          "겹치는 부분에서 같은 줄이 반복되면 한 번만 적고, 글 덩어리마다 줄을 바꿔 주세요. 옮겨 적은 글만 답하세요.")


def visual_tokens(width: int, height: int) -> int:
    return math.ceil(width / 28) * math.ceil(height / 28)


def slice_image(data: bytes) -> list[bytes]:
    """긴 상세페이지 이미지를 PNG 조각들로 나눈다."""
    im = Image.open(io.BytesIO(data)).convert("RGB")
    if im.width > MAX_WIDTH:
        im = im.resize((MAX_WIDTH, round(im.height * MAX_WIDTH / im.width)))
    out, top = [], 0
    while top < im.height:
        bottom = min(top + CHUNK_HEIGHT, im.height)
        buf = io.BytesIO()
        im.crop((0, top, im.width, bottom)).save(buf, format="PNG")
        out.append(buf.getvalue())
        if bottom == im.height:
            break
        top = bottom - OVERLAP
    return out


def estimate(images: list[bytes], model: str = DEFAULT_MODEL, out_tokens: int = 1500) -> dict:
    """조각 기준 예상 토큰과 비용(달러)."""
    tok = 0
    for d in images:
        for c in slice_image(d):
            w, h = Image.open(io.BytesIO(c)).size
            tok += visual_tokens(w, h)
    tok += 300  # 지시문
    pin, pout = PRICE[model]
    return {"input_tokens": tok, "usd": round(tok / 1e6 * pin + out_tokens / 1e6 * pout, 5)}


@dataclass
class OcrResult:
    text: str
    input_tokens: int
    output_tokens: int
    model: str

    @property
    def usd(self) -> float:
        pin, pout = PRICE.get(self.model, (0, 0))
        return self.input_tokens / 1e6 * pin + self.output_tokens / 1e6 * pout


def read_text(images: list[bytes], api_key: str, model: str = DEFAULT_MODEL, timeout: int = 120) -> OcrResult:
    """한 상품의 이미지(여러 장 가능)를 순서대로 읽어 글자로 돌려준다."""
    if not api_key:
        raise ValueError("API 키가 없어서 이미지 글자를 읽을 수 없어요.")
    content = []
    for d in images:
        for c in slice_image(d):
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                        "data": base64.b64encode(c).decode()}})
    if len(content) > 20:
        raise ValueError("이미지가 너무 길어요. 한 상품당 조각 20개(세로 약 3만 px)까지만 읽을 수 있어요.")
    content.append({"type": "text", "text": PROMPT})
    body = json.dumps({"model": model, "max_tokens": 4000,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    usage = data.get("usage", {})
    return OcrResult(text=text, input_tokens=usage.get("input_tokens", 0),
                     output_tokens=usage.get("output_tokens", 0), model=model)
