/* 이미지 글 덩어리 → 글자 (Tesseract WebAssembly, 브라우저 안에서만 실행). */
let api = null, ready = null, T = null;

function simdSupported() {
  try { // i32x4.splat 하나짜리 최소 모듈
    return WebAssembly.validate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123, 3, 2, 1, 0, 10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11]));
  } catch (e) { return false; }
}

async function init(base) {
  importScripts(base + (simdSupported() ? "tesseract-core-simd-lstm.wasm.js" : "tesseract-core-lstm.wasm.js"));
  T = await TesseractCore();
  for (const lang of ["kor", "eng"]) {
    const buf = await (await fetch(base + lang + ".traineddata")).arrayBuffer();
    T.FS.writeFile(lang + ".traineddata", new Uint8Array(buf));
  }
  api = new T.TessBaseAPI();
  if (api.Init(null, "kor+eng") !== 0) throw new Error("글자 읽기 엔진을 시작하지 못했어요.");
  api.SetVariable("tessedit_pageseg_mode", "6");
}

self.onmessage = async (e) => {
  const { id, kind } = e.data;
  try {
    if (kind === "init") { ready = ready || init(e.data.base); await ready; self.postMessage({ id, ok: true }); return; }
    await ready;
    const { gray, width, height } = e.data;
    // 흑백 PGM 파일로 넘긴다 (엔진이 /input 파일을 읽어 자체 메모리에 둔다)
    const head = new TextEncoder().encode(`P5\n${width} ${height}\n255\n`);
    const pgm = new Uint8Array(head.length + gray.length);
    pgm.set(head); pgm.set(gray, head.length);
    T.FS.writeFile("/input", pgm);
    api.SetImageFile();
    const text = api.GetUTF8Text();
    api.Clear();
    self.postMessage({ id, ok: true, text });
  } catch (err) {
    self.postMessage({ id, ok: false, error: String(err && err.message || err) });
  }
};
