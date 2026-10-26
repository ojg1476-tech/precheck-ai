/* 상세페이지 이미지 → 글자. precheck/ocr.py 의 무료 방식과 같은 방법:
 * 폭 1400px로 맞춘 흑백 이미지를 가로줄 밝기 변화로 글 덩어리로 나누고, 어두운 덩어리는 뒤집어 하나씩 읽는다. */
(function (root) {
  "use strict";
  const WIDTH = 1400, BUSY_STD = 6, GAP = 10, STRIP = 2000;
  let worker = null, seq = 0;
  const pending = new Map();

  function call(msg, transfer) {
    return new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      worker.postMessage({ id, ...msg }, transfer || []);
    });
  }

  const BASE = () => new URL("vendor/tesseract/", document.baseURI).href;
  async function start() {
    const base = BASE();
    if (!worker) {
      worker = new Worker(new URL("js/ocr-worker.js", document.baseURI).href);
      worker.onmessage = e => {
        const p = pending.get(e.data.id); if (!p) return;
        pending.delete(e.data.id);
        e.data.ok ? p.resolve(e.data) : p.reject(new Error(e.data.error));
      };
    }
    return call({ kind: "init", base });
  }

  async function toGray(file) {
    const bmp = await createImageBitmap(file);
    const h = Math.max(1, Math.round(bmp.height * WIDTH / bmp.width));
    const gray = new Uint8Array(WIDTH * h);
    const cv = document.createElement("canvas"); cv.width = WIDTH;
    const ctx = cv.getContext("2d", { willReadFrequently: true });
    for (let y0 = 0; y0 < h; y0 += STRIP) {           // 사파리 캔버스 크기 제한 때문에 띠로 나눠 그린다
      const sh = Math.min(STRIP, h - y0); cv.height = sh;
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, WIDTH, sh);
      ctx.drawImage(bmp, 0, y0 * bmp.height / h, bmp.width, sh * bmp.height / h, 0, 0, WIDTH, sh);
      const d = ctx.getImageData(0, 0, WIDTH, sh).data;
      for (let i = 0, j = y0 * WIDTH; i < d.length; i += 4, j++) gray[j] = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
    }
    bmp.close && bmp.close();
    return { gray, width: WIDTH, height: h };
  }

  function blocks({ gray, width, height }) {
    const busy = new Uint8Array(height);
    for (let y = 0; y < height; y++) {
      let s = 0, s2 = 0; const o = y * width;
      for (let x = 0; x < width; x++) { const v = gray[o + x]; s += v; s2 += v * v; }
      const m = s / width; busy[y] = Math.sqrt(Math.max(0, s2 / width - m * m)) > BUSY_STD ? 1 : 0;
    }
    const spans = []; let start = -1, quiet = 0;
    for (let y = 0; y < height; y++) {
      if (busy[y]) { if (start < 0) start = y; quiet = 0; }
      else if (start >= 0) { quiet++; if (quiet >= GAP) { spans.push([start, y - quiet + 1]); start = -1; quiet = 0; } }
    }
    if (start >= 0) spans.push([start, height]);
    const out = [];
    for (const [s, e] of spans) {
      if (e - s < 8) continue;
      const y0 = Math.max(0, s - 8), y1 = Math.min(height, e + 8), bh = y1 - y0;
      let b = gray.slice(y0 * width, y1 * width);
      const border = [];
      for (let x = 0; x < width; x++) border.push(b[x], b[(bh - 1) * width + x]);
      for (let y = 0; y < bh; y++) border.push(b[y * width], b[y * width + width - 1]);
      border.sort((p, q) => p - q);
      if (border[border.length >> 1] < 128) for (let i = 0; i < b.length; i++) b[i] = 255 - b[i];
      const sorted = Float64Array.from(b).sort(), bg = sorted[sorted.length >> 1] > 127 ? 255 : 0;
      const P = 20, W = width + 2 * P, H = bh + 2 * P, padded = new Uint8Array(W * H).fill(bg);
      for (let y = 0; y < bh; y++) padded.set(b.subarray(y * width, (y + 1) * width), (y + P) * W + P);
      out.push({ gray: padded, width: W, height: H });
    }
    return out;
  }

  function clean(text) {
    return text.split("\n").map(l => l.trim()).filter(l => (l.match(/[가-힣]/g) || []).length >= 2 || (l.match(/[가-힣A-Za-z0-9]/g) || []).length >= 4);
  }

  /* 한 상품의 이미지(여러 장 가능)를 읽는다. onProgress(0~1) */
  async function readImages(files, onProgress) {
    await start();
    const lines = [];
    const all = [];
    for (const f of files) all.push(...blocks(await toGray(f)));
    for (let i = 0; i < all.length; i++) {
      const b = all[i];
      const r = await call({ kind: "read", gray: b.gray, width: b.width, height: b.height }, [b.gray.buffer]);
      for (const l of clean(r.text)) if (lines[lines.length - 1] !== l) lines.push(l);
      onProgress && onProgress((i + 1) / all.length);
    }
    return lines.join("\n");
  }

  root.MoonguOCR = { readImages, blocks, clean, start };
})(window);
