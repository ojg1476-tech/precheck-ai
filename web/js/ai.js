/* AI로 한 번 더 확인: 실제 적발 문구와 '뜻'이 가까운 구절을 찾는다.
   - 모델(ko-sroberta-multitask, 8비트)은 이 브라우저 안에서만 돈다. 문구는 어디에도 보내지 않는다.
   - 구절 나누기와 기준값은 tools/build_ai.py 와 같다 (그쪽에서 처음 보는 문구로 성능을 쟀다). */
(function (root) {
  "use strict";
  const BASE = "ai/", MODEL = "ko-sroberta-multitask", VENDOR = "vendor/transformers/";
  let ready = null, kb = null, extractor = null;
  const cache = new Map();   // 구절 → 임베딩

  /* 문장 → 어절 2·3개 묶음, 4글자 이상 어절, 짧은 문장 통째 (위치 포함) */
  function windows(text, maxWords = 8) {
    const out = [], seen = new Set();
    const sentRe = /[^.!?\n,·…~]+/g; let m;
    while ((m = sentRe.exec(text))) {
      const s = m[0], base = m.index;
      // 두 칸 이상 띄어쓰기도 문장 경계 (Python과 같게)
      const parts = []; const pr = /(?:\S+(?: \S+)*)/g; let q;
      while ((q = pr.exec(s))) parts.push([q[0], base + q.index]);
      for (const [seg, off] of parts) {
        const w = []; const wr = /\S+/g; let t;
        while ((t = wr.exec(seg))) w.push([t[0], off + t.index]);
        if (!w.length) continue;
        const add = (i, j) => {
          const str = w.slice(i, j).map(x => x[0]).join(" ");
          if (seen.has(str)) return; seen.add(str);
          out.push({ text: str, start: w[i][1], end: w[j - 1][1] + w[j - 1][0].length });
        };
        if (w.length <= maxWords) add(0, w.length);
        for (const n of [2, 3]) for (let i = 0; i + n <= w.length; i++) add(i, i + n);
        w.forEach((x, i) => { if (x[0].length >= 4) add(i, i + 1); });
      }
    }
    return out;
  }

  async function fetchParts(url, onProgress) {
    const n = +(await (await fetch(url.replace(/model_quantized\.onnx$/, "parts.txt"))).text()) || 1;
    const blobs = []; let got = 0;
    const sizes = await Promise.all(Array.from({ length: n }, (_, i) => fetch(`${url}.part${i}`, { method: "HEAD" })
      .then(r => +r.headers.get("content-length") || 0).catch(() => 0)));
    const total = sizes.reduce((a, b) => a + b, 0) || 1;
    for (let i = 0; i < n; i++) {
      const r = await fetch(`${url}.part${i}`);
      const rd = r.body.getReader(), chunks = [];
      for (;;) { const { done, value } = await rd.read(); if (done) break; chunks.push(value); got += value.length; onProgress && onProgress(got / total, total); }
      blobs.push(new Blob(chunks));
    }
    return new Blob(blobs);
  }

  function load(onProgress) {
    if (ready) return ready;
    ready = (async () => {
      const T = await import(new URL(VENDOR + "transformers.min.js", document.baseURI).href);
      T.env.allowRemoteModels = false; T.env.allowLocalModels = true;
      T.env.localModelPath = new URL(BASE + "model/", document.baseURI).href;
      T.env.useBrowserCache = false;
      T.env.backends.onnx.wasm.wasmPaths = new URL(VENDOR, document.baseURI).href;
      // 여러 스레드는 cross-origin isolation(web/vercel.json 헤더)일 때만 쓸 수 있다
      T.env.backends.onnx.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 2) : 1;
      // 모델 파일은 깃허브 크기 제한 때문에 나눠 두었다 → 이어 붙여서 넘긴다
      T.env.useCustomCache = true;
      T.env.customCache = {
        match: async req => {
          const url = String((req && (req.url || req.href)) || req);
          if (!/model_quantized\.onnx$/.test(url)) return undefined;
          const blob = await fetchParts(url, onProgress);
          return new Response(blob, { headers: { "content-length": String(blob.size) } });
        },
        put: async () => {},
      };
      const [k] = await Promise.all([fetch(BASE + "kb.json").then(r => r.json())]);
      const raw = Uint8Array.from(atob(k.emb), c => c.charCodeAt(0));
      const i8 = new Int8Array(raw.buffer), dim = k.dim, n = k.phrases.length;
      const M = new Float32Array(n * dim);
      for (let r = 0; r < n; r++) {
        let s = 0; for (let c = 0; c < dim; c++) { const v = i8[r * dim + c] / 127; M[r * dim + c] = v; s += v * v; }
        s = Math.sqrt(s) || 1; for (let c = 0; c < dim; c++) M[r * dim + c] /= s;
      }
      let W = null;
      if (k.lr) { const wb = Uint8Array.from(atob(k.lr.w), c => c.charCodeAt(0)); W = new Float32Array(wb.buffer); }
      kb = { ...k, M, n, dim, W };
      extractor = await T.pipeline("feature-extraction", MODEL, { dtype: "q8", device: "wasm" });
      return true;
    })();
    ready.catch(() => { ready = null; });
    return ready;
  }

  async function embed(texts, onStep) {
    const need = texts.filter(t => !cache.has(t));
    for (let i = 0; i < need.length; i += 16) {
      const part = need.slice(i, i + 16);
      const out = await extractor(part, { pooling: "mean", normalize: true });
      const d = out.dims[1], data = out.data;
      part.forEach((t, j) => cache.set(t, data.slice(j * d, (j + 1) * d)));
      onStep && onStep(Math.min(i + 16, need.length), need.length);
      await new Promise(r => setTimeout(r, 0));
    }
    return texts.map(t => cache.get(t));
  }

  function lrScore(v) { let s = kb.lr.b; for (let c = 0; c < kb.dim; c++) s += v[c] * kb.W[c]; return s; }
  function nearest(v) {
    const { M, n, dim } = kb; let best = -1, bi = 0;
    for (let r = 0; r < n; r++) { let s = 0; const o = r * dim; for (let c = 0; c < dim; c++) s += v[c] * M[o + c]; if (s > best) { best = s; bi = r; } }
    return [best, bi];
  }

  /* text에서 의심 구절 찾기. skip: 이미 규칙에 걸린 [start,end] 구간들 (겹치는 구절은 뺌) */
  async function check(text, skip = [], onStep) {
    await load();
    const ws = windows(text, kb.max_sent_words || 8);
    if (!ws.length) return [];
    const E = await embed(ws.map(w => w.text), onStep);
    const hits = [];
    ws.forEach((w, i) => {
      const flag = kb.W ? lrScore(E[i]) > kb.lr.threshold : nearest(E[i])[0] >= kb.threshold;
      if (!flag || skip.some(([a, b]) => w.start < b && a < w.end)) return;
      const [s, bi] = nearest(E[i]);
      hits.push({ ...w, score: kb.W ? lrScore(E[i]) : s, sim: s, near: kb.phrases[bi] });
    });
    // 겹치는 구절은 점수가 높은 것 하나만
    hits.sort((a, b) => b.score - a.score);
    const keep = [];
    for (const h of hits) if (!keep.some(k => h.start < k.end && k.start < h.end)) keep.push(h);
    return keep.sort((a, b) => a.start - b.start);
  }

  /* 확인용: 문구 전체에서 가장 높은 유사도 (tools/build_ai.py 의 score 와 같아야 함) */
  async function score(text) {
    await load();
    const ws = windows(text, kb.max_sent_words || 8); if (!ws.length) return 0;
    const E = await embed(ws.map(w => w.text));
    return { knn: Math.max(...E.map(v => nearest(v)[0])), lr: kb.W ? Math.max(...E.map(lrScore)) : null };
  }

  const api = { load, check, windows, score, isReady: () => !!extractor, info: () => kb && { threshold: kb.threshold, model: kb.model } };
  root.MoonguAI = api;
})(window);
