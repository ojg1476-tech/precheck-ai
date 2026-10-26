/* 문구레이더 화면 동작. 모든 검사는 이 브라우저 안에서만 돌고, 파일은 어디에도 보내지 않는다. */
(function () {
  "use strict";
  const M = window.Moongu, R = window.MoonguReport;
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const TIER = {
    "높음": ["var(--red)", "꼭 고칠 표현이 있어요"], "중간": ["var(--amber)", "확인이 필요해요"],
    "확인": ["var(--blue)", "증명 자료를 챙기세요"], "양호": ["var(--ok)", "걸린 표현이 없어요"], "오류": ["var(--gray)", "읽지 못했어요"],
  };
  const GRADE = { red: ["var(--red)", "var(--red-50)"], amber: ["var(--amber)", "var(--amber-50)"], blue: ["var(--blue)", "var(--blue-50)"] };
  const ORDER = { red: 0, amber: 1, blue: 2 };
  const TYPES = [["cos", "일반 화장품"], ["fcos", "기능성 화장품"], ["food", "일반 식품"], ["hfood", "건강기능식품"]];
  const state = { ck: null, results: null, source: "", ocr: null, pick: 0, imgFiles: [] };

  /* ── 공통 ───────────────────────────── */
  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast.t); toast.t = setTimeout(() => (t.hidden = true), 2600);
  }
  function tierTag(t) { return `<span class="tier" style="--c:${TIER[t][0]}"><span class="sq"></span>${t}</span>`; }
  function shortPen(p) { if (!p) return "-"; return `징역 ${p[0]}년 / 벌금 ${p[1] >= 1e8 ? p[1] / 1e8 + "억" : (p[1] / 1e4).toLocaleString("ko-KR") + "만"}`; }
  function seg(el, name, value, onChange) {
    el.insertAdjacentHTML("beforeend", TYPES.map(([v, t]) =>
      `<label><input type="radio" name="${name}" value="${v}"${v === value ? " checked" : ""}><span>${t}</span></label>`).join(""));
    el.addEventListener("change", e => onChange(e.target.value));
  }
  function marked(text, fs, cls = "") {
    let out = "", pos = 0;
    fs.forEach((f, i) => {
      const [c, b] = GRADE[f.grade];
      out += esc(text.slice(pos, f.start)) + `<mark class="g-${f.grade} ${cls}" data-i="${i}" style="--c:${c};--b:${b}">${esc(text.slice(f.start, f.end))}</mark>`;
      pos = f.end;
    });
    return out + esc(text.slice(pos));
  }

  /* 같은 규칙에 걸린 표현은 카드 하나로 */
  function cards(fs) {
    const groups = new Map();
    fs.map((f, i) => ({ f, i })).sort((a, b) => ORDER[a.f.grade] - ORDER[b.f.grade] || a.f.start - b.f.start)
      .forEach(x => { const k = x.f.ruleId + x.f.grade; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(x); });
    return [...groups.values()].map(g => {
      const f = g[0].f, [c, b] = GRADE[f.grade];
      const seen = new Set(), chips = g.filter(x => !seen.has(x.f.phrase) && seen.add(x.f.phrase))
        .map(x => `<button type="button" data-i="${x.i}" title="문구에서 위치 보기">${esc(x.f.phrase)}</button>`).join("");
      const checks = f.checks.length ? `<div class="checks"><b>쓰기 전에 확인할 것</b>${f.checks.map(t =>
        `<label><input type="checkbox"><span>${esc(t)}</span></label>`).join("")}</div>` : "";
      return `<article class="fcard" style="--c:${c};--b:${b}">
        <div class="hd"><span class="grade">${esc(f.gradeName)}</span><span class="lb">${esc(f.label)}</span></div>
        <div class="phs">${chips}</div>
        <p class="why">${esc(f.why)}</p>
        <div class="two">${f.penalty ? `<div class="risk"><b>이대로 두면</b>${esc(f.penalty)}</div>` : ""}<div class="alt"><b>대신 이렇게</b>${esc(f.alt)}</div></div>
        ${checks}
        <details><summary>근거 보기</summary><p>정확한 용어: ${esc(f.term)}<br>관련 기준: ${esc(f.law)}<br>출처: ${esc(f.source)}</p></details>
      </article>`;
    }).join("");
  }

  /* ── 라우팅 ─────────────────────────── */
  function route() {
    const h = location.hash.replace(/^#\/?/, "");
    const r = h.startsWith("text") ? "text" : h.startsWith("about") ? "about" : "batch";
    document.querySelectorAll(".nav a").forEach(a => { if (a.dataset.route !== r) a.removeAttribute("aria-current"); else a.setAttribute("aria-current", "page"); });
    let v = r;
    if (r === "batch") v = state.results ? "batch-result" : state.imgFiles.length ? "batch-images" : "batch-start";
    document.querySelectorAll(".view").forEach(s => (s.hidden = s.dataset.view !== v));
    if (r === "text") setTimeout(() => $("#ed").focus(), 0);
    window.scrollTo(0, 0);
  }

  /* ── 시작 화면 ───────────────────────── */
  function proof() {
    const text = "피부 재생 크림, 7일 만에 주름 개선", fs = state.ck.check(text, "cos");
    let out = "", pos = 0;
    for (const f of fs) {
      out += esc(text.slice(pos, f.start)) + `<span class="wv g-${f.grade}">${esc(text.slice(f.start, f.end))}</span>`;
      pos = f.end;
    }
    $("#proof-copy").innerHTML = out + esc(text.slice(pos));
    const sorted = fs.slice().sort((a, b) => ORDER[a.grade] - ORDER[b.grade] || a.start - b.start);
    $("#proof-notes").innerHTML = sorted.map(f => {
      const alt = f.alt.startsWith("(") ? esc(f.alt.replace(/[()]/g, "")) : `대신 <em>${esc(f.alt.split(" / ")[0])}</em>`;
      return `<li style="--c:${GRADE[f.grade][0]}"><span class="ph">${esc(f.phrase)}</span>${esc(f.label)}<br>${alt}</li>`;
    }).join("");
    const tier = fs.some(f => f.grade === "red") ? "높음" : fs.some(f => f.grade === "amber") ? "중간" : "확인";
    $("#proof-tier").textContent = "위험도 " + tier;

    // 레이더: 바늘이 지나갈 때 실제 검사 결과가 하나씩 잡힌다 (6초에 한 바퀴, 시계 방향)
    const more = state.ck.check(text + ", 피부과 추천", "cos");
    const spots = [[78, 43], [116, 47], [244, 47], [282, 43]];      // [각도(위=0, 시계 방향), 반지름 %]
    $("#blips").innerHTML = more.slice(0, 4).map((f, i) => {
      const [deg, r] = spots[i], rad = deg * Math.PI / 180;
      const x = 50 + r * Math.sin(rad), y = 50 - r * Math.cos(rad);
      return `<span class="blip" style="left:${x}%;top:${y}%;--c:${GRADE[f.grade][0]};--d:${(deg / 360 * 6 - 6).toFixed(2)}s"><i></i>${esc(f.phrase)}<small>${esc(f.label)}</small></span>`;
    }).join("");
  }

  function showError(msg) { const e = $("#start-err"); e.textContent = msg; e.hidden = !msg; }

  async function decodeCSV(buf) {
    try { return new TextDecoder("utf-8", { fatal: true }).decode(buf).replace(/^﻿/, ""); }
    catch (e) { return new TextDecoder("euc-kr").decode(buf); }
  }

  async function readTable(file) {
    const buf = await file.arrayBuffer(), name = file.name.toLowerCase();
    let rows;
    if (/\.(xlsx|xlsm)$/.test(name)) rows = await MiniXLSX.readFirstSheet(buf, s => new DOMParser().parseFromString(s, "application/xml"));
    else if (/\.(csv|txt)$/.test(name)) rows = M.parseCSV(await decodeCSV(buf));
    else throw new Error("CSV 또는 엑셀(.xlsx) 파일만 올릴 수 있어요.");
    return M.readRows(rows);
  }

  async function onFiles(list) {
    showError("");
    const files = [...list];
    if (!files.length) return;
    const imgs = files.filter(f => /^image\//.test(f.type) || /\.(png|jpe?g|webp)$/i.test(f.name));
    if (imgs.length === files.length) { state.imgFiles = imgs; renderImages(); location.hash = "#/"; route(); return; }
    const table = files.find(f => /\.(csv|txt|xlsx|xlsm)$/i.test(f.name));
    if (!table) { showError("CSV, 엑셀, 또는 상세페이지 이미지(PNG, JPG) 파일을 올려 주세요."); return; }
    try { run(await readTable(table), table.name); }
    catch (e) { showError("파일을 읽지 못했어요. " + e.message); }
  }

  function run(items, source, ocr = null) {
    state.results = M.checkProducts(items, state.ck);
    state.source = source; state.ocr = ocr; state.imgFiles = [];
    state.pick = Math.max(0, state.results.findIndex(r => r.findings.length));
    renderResult(); location.hash = "#/"; route();
  }

  /* ── 이미지 ─────────────────────────── */
  let imgType = "cos";
  function renderImages() {
    $("#img-count").textContent = `${state.imgFiles.length}장`;
    $("#img-list").innerHTML = state.imgFiles.map((f, i) =>
      `<li><span>${esc(f.name.replace(/\.[^.]+$/, ""))}</span><span class="prog"><i id="ib-${i}"></i></span><span class="st" id="is-${i}">대기</span></li>`).join("");
    $("#img-go").disabled = false;
  }
  async function readImages() {
    const go = $("#img-go"); go.disabled = true; go.textContent = "읽는 중…";
    const items = [], texts = {};
    for (let i = 0; i < state.imgFiles.length; i++) {
      const f = state.imgFiles[i], name = f.name.replace(/\.[^.]+$/, "");
      $(`#is-${i}`).textContent = i === 0 ? "엔진 준비 중" : "읽는 중";
      try {
        const text = await MoonguOCR.readImages([f], p => { $(`#ib-${i}`).style.width = (p * 100).toFixed(0) + "%"; $(`#is-${i}`).textContent = "읽는 중"; });
        texts[name] = text; items.push({ row: i + 1, name, type: imgType, text });
        $(`#is-${i}`).textContent = "완료";
      } catch (e) {
        items.push({ row: i + 1, name, type: imgType, text: "", _err: e.message }); $(`#is-${i}`).textContent = "실패";
      }
    }
    go.textContent = "글자 읽고 검사하기";
    run(items, `이미지 ${items.length}장, 이 브라우저에서 읽음`, texts);
  }

  /* ── 결과 ───────────────────────────── */
  function renderResult() {
    const res = state.results, ov = M.overview(res, state.ck);
    $("#res-source").textContent = `${state.source} · 상품 ${ov.total}개`;
    const flagged = res.filter(r => r.findings.length).length;
    $('[data-tab="detail"]').innerHTML = `상품별 자세히<span class="cnt">${flagged}</span>`;
    $('[data-tab="ocr"]').hidden = !state.ocr;
    selectTab("sum");

    // 요약
    const cells = [`<div class="c"><div class="k">점검한 상품</div><div class="v">${ov.total}<small>개</small></div><div class="d">위험한 순서로 정렬했어요</div></div>`]
      .concat(["높음", "중간", "확인", "양호"].map(t => `<div class="c${ov.tiers[t] ? "" : " zero"}"><div class="k"><span class="sq" style="--c:${TIER[t][0]}"></span>${t}</div>
        <div class="v">${ov.tiers[t]}</div><div class="d">${TIER[t][1]}</div></div>`));
    const dist = Object.keys(TIER).filter(t => ov.tiers[t]).map(t => `<span style="--c:${TIER[t][0]};flex:${ov.tiers[t]}" title="${t} ${ov.tiers[t]}개"></span>`).join("");
    const urgent = res.filter(r => r.tier === "높음" || r.tier === "중간").slice(0, 3);
    const urgentHTML = urgent.length ? `<ol>${urgent.map(r => {
      const c = r.counts, i = res.indexOf(r);
      return `<li><button type="button" data-go="${i}"><span class="rk">${i + 1}</span><span><span class="nm">${esc(r.name)}</span>
        <span class="mt">꼭 고치기 ${c.red}, 확인 필요 ${c.amber}</span></span><span class="pen">${shortPen(r.maxPenalty)}</span></button></li>`;
    }).join("")}</ol>` : `<p class="empty-s">급하게 고칠 상품이 없어요.</p>`;
    const top = ov.total || 1;
    const bars = ov.common.length ? ov.common.map(([n, k]) => `<div class="bar"><span class="t">${esc(n)}</span><span class="tr"><i style="width:${(k / top * 100).toFixed(1)}%"></i></span>
      <span class="n">상품 ${k}개</span></div>`).join("") : `<p class="empty-s">여러 상품에 같은 유형의 표현이 걸리지 않았어요.</p>`;
    $("#tp-sum").innerHTML = `<div class="sum-grid">
      <div><div class="card"><div class="board">${cells.join("")}</div><div class="dist">${dist}</div></div>
        <div class="card urgent"><h3>먼저 고칠 상품<small>형사처벌이 무거운 순서</small></h3>${urgentHTML}</div></div>
      <div class="card"><h3>여러 상품에서 반복된 문제<small>꼭 고치기·확인 필요 기준</small></h3><div class="bars">${bars}</div></div></div>`;

    // 위험 순서
    $("#tp-rank").innerHTML = `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>순위</th><th>상품명</th><th>제품 종류</th><th>위험도</th>
      <th class="num">꼭 고치기</th><th class="num">확인 필요</th><th class="num">자료 챙기기</th><th>최대 처벌</th><th>메모</th></tr></thead><tbody>${res.map((r, i) => {
      const c = r.counts, n = v => `<td class="num${v ? "" : " z"}">${v}</td>`;
      return `<tr class="${r.findings.length ? "go" : ""}" data-go="${r.findings.length ? i : ""}"><td class="num">${i + 1}</td><td class="nm">${esc(r.name)}</td>
        <td>${esc(R.TYPE_NAME[r.productType] ?? r.productType)}</td><td>${tierTag(r.tier)}</td>${n(c.red)}${n(c.amber)}${n(c.blue)}
        <td style="white-space:nowrap">${shortPen(r.maxPenalty)}</td><td class="memo">${esc(r.error)}</td></tr>`;
    }).join("")}</tbody></table></div>`;

    // 상품 목록
    $("#plist").innerHTML = res.map((r, i) => !r.findings.length ? "" :
      `<li><button type="button" role="option" data-pick="${i}"><span class="sq" style="--c:${TIER[r.tier][0]}"></span><span>
        <span class="nm">${esc(r.name)}</span><span class="mt">꼭 고치기 ${r.counts.red} · 확인 ${r.counts.amber} · 자료 ${r.counts.blue}</span></span></button></li>`).join("")
      || `<li class="empty-s" style="padding:16px">걸린 표현이 있는 상품이 없어요.</li>`;
    renderDetail();

    // 읽어 낸 글
    if (state.ocr) $("#tp-ocr").innerHTML = `<p class="sub" style="margin:0 0 12px">이미지에서 읽어 낸 글이에요. 잘못 읽은 곳이 있으면 글을 고쳐 ‘문구 하나 검사’에 넣어 보세요.</p>` +
      Object.entries(state.ocr).map(([n, t]) => `<div class="copybox"><div class="cap"><span>${esc(n)}</span></div><div class="copytext open">${esc(t) || "(읽은 글 없음)"}</div></div>`).join("");
  }

  function renderDetail() {
    const r = state.results[state.pick];
    document.querySelectorAll("#plist button").forEach(b => b.setAttribute("aria-selected", String(+b.dataset.pick === state.pick)));
    if (!r || !r.findings.length) { $("#pdetail").innerHTML = ""; return; }
    const c = r.counts;
    $("#pdetail").innerHTML = `<div class="ph-head"><h3>${esc(r.name)}</h3>${tierTag(r.tier)}<span class="mt">${esc(R.TYPE_NAME[r.productType])} · 꼭 고치기 ${c.red}, 확인 필요 ${c.amber}, 자료 챙기기 ${c.blue}</span></div>
      ${r.maxPenalty ? `<p class="ph-pen">이대로 두면 최대 <b>${M.penaltyText(r.maxPenalty)}</b></p>` : ""}
      <div class="copybox"><div class="cap"><span>상세 문구</span><button type="button" id="copy-more">전체 보기</button></div>
        <div class="copytext" id="copytext">${marked(r.text, r.findings)}</div></div>
      ${cards(r.findings)}`;
    const ct = $("#copytext");
    if (ct.scrollHeight <= 140) { ct.classList.add("open"); $("#copy-more").hidden = true; }
    $("#pdetail").scrollTop = 0;
  }

  function selectTab(t) {
    document.querySelectorAll("#res-tabs button").forEach(b => b.setAttribute("aria-selected", String(b.dataset.tab === t)));
    document.querySelectorAll(".tp").forEach(p => (p.hidden = p.dataset.panel !== t));
  }

  function goProduct(i) { state.pick = i; renderDetail(); selectTab("detail"); }

  async function downloadReport() {
    const blob = R.buildReport(state.results, state.ck);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `moonguradar_report_${new Date().toLocaleDateString("sv-SE")}.xlsx`;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    toast("엑셀 리포트를 받았어요");
  }

  /* ── 문구 하나 검사 ──────────────────── */
  let txtType = "cos", lastFs = [];
  function checkText() {
    const ed = $("#ed"), text = ed.value;
    lastFs = text.trim() ? state.ck.check(text, txtType) : [];
    $("#ed-hl").innerHTML = marked(text, lastFs) + "\n";
    $("#ed-count").textContent = `${text.length.toLocaleString("ko-KR")}자`;
    const c = M.summarize(lastFs);
    $("#ed-sum").innerHTML = [["red", "꼭 고치기"], ["amber", "확인 필요"], ["blue", "자료 챙기기"]].map(([g, n]) =>
      `<div class="${c[g] ? "" : "zero"}"><div class="k"><span class="sq" style="--c:${GRADE[g][0]}"></span>${n}</div><div class="v">${c[g]}</div></div>`).join("");
    $("#ed-cards").innerHTML = !text.trim()
      ? `<div class="hint"><b>문구를 붙여 넣어 주세요</b>상세페이지 글을 왼쪽에 넣으면 고칠 곳에 물결 밑줄을 긋고, 이유와 대신 쓸 말을 여기에 보여드려요.</div>`
      : lastFs.length ? cards(lastFs)
        : `<div class="hint"><b>걸린 표현이 없어요</b>기본 검사를 통과했어요. 중요한 광고는 협회 심의도 받아 보세요.</div>`;
    syncScroll();
  }
  function syncScroll() { const ed = $("#ed"); $("#ed-hl").parentElement.scrollTop = ed.scrollTop; }

  /* ── 시작 ───────────────────────────── */
  async function init() {
    const data = await (await fetch("rules.json")).json();
    state.ck = new M.Checker(data);
    $("#fact-rules").textContent = state.ck.rules.length;
    $("#foot-v").textContent = `기준 ${state.ck.version} · 규칙 ${state.ck.rules.length}개 · 검사와 이미지 읽기는 모두 이 브라우저 안에서만 이뤄지고, 올린 파일은 어디에도 보내지 않아요.`;
    proof();

    const file = $("#file"), ask = $("#ask"), start = $("#view-start");
    file.addEventListener("change", () => { onFiles(file.files); file.value = ""; });
    $("#attach").addEventListener("click", () => file.click());
    ask.addEventListener("submit", e => {
      e.preventDefault();
      const t = $("#ask-text").value.trim();
      if (!t) { file.click(); return; }
      $("#ed").value = t; $("#ask-text").value = ""; location.hash = "#/text"; checkText();
    });
    let depth = 0;
    start.addEventListener("dragenter", e => { e.preventDefault(); depth++; ask.classList.add("over"); });
    start.addEventListener("dragover", e => e.preventDefault());
    start.addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; ask.classList.remove("over"); } });
    start.addEventListener("drop", e => { e.preventDefault(); depth = 0; ask.classList.remove("over"); onFiles(e.dataTransfer.files); });
    $("#try-sample").addEventListener("click", async () => {
      const t = await (await fetch("sample_products.csv")).text();
      run(M.readRows(M.parseCSV(t.replace(/^﻿/, ""))), "예시 목록");
    });

    seg($("#img-type"), "img-type", imgType, v => (imgType = v));
    $("#img-cancel").addEventListener("click", () => { state.imgFiles = []; route(); });
    $("#img-go").addEventListener("click", readImages);

    $("#res-tabs").addEventListener("click", e => { const b = e.target.closest("button[data-tab]"); if (b) selectTab(b.dataset.tab); });
    $("#res-new").addEventListener("click", () => { state.results = null; route(); setTimeout(() => $("#ask-text").focus(), 0); });
    $("#res-xlsx").addEventListener("click", downloadReport);
    $("#tp-sum").addEventListener("click", e => { const b = e.target.closest("[data-go]"); if (b) goProduct(+b.dataset.go); });
    $("#tp-rank").addEventListener("click", e => { const r = e.target.closest("tr[data-go]"); if (r && r.dataset.go !== "") goProduct(+r.dataset.go); });
    $("#plist").addEventListener("click", e => { const b = e.target.closest("[data-pick]"); if (b) { state.pick = +b.dataset.pick; renderDetail(); } });
    $("#pdetail").addEventListener("click", e => {
      if (e.target.id === "copy-more") { const ct = $("#copytext"); const o = ct.classList.toggle("open"); e.target.textContent = o ? "접기" : "전체 보기"; return; }
      const chip = e.target.closest(".phs button"); if (!chip) return;
      const ct = $("#copytext"); ct.classList.add("open"); $("#copy-more").textContent = "접기";
      const m = ct.querySelector(`mark[data-i="${chip.dataset.i}"]`);
      if (m) { m.scrollIntoView({ block: "center", behavior: "smooth" }); m.classList.add("flash"); setTimeout(() => m.classList.remove("flash"), 1400); }
    });

    seg($("#txt-type"), "txt-type", txtType, v => { txtType = v; checkText(); });
    const ed = $("#ed"); let t;
    ed.addEventListener("input", () => { clearTimeout(t); t = setTimeout(checkText, 120); $("#ed-hl").innerHTML = esc(ed.value) + "\n"; });
    ed.addEventListener("scroll", syncScroll);
    $("#ed-cards").addEventListener("click", e => {
      const chip = e.target.closest(".phs button"); if (!chip) return;
      const f = lastFs[+chip.dataset.i]; ed.focus(); ed.setSelectionRange(f.start, f.end);
    });
    checkText();

    window.addEventListener("hashchange", route);
    route();
  }
  init().catch(e => { document.body.insertAdjacentHTML("afterbegin", `<p class="err" style="margin:16px">화면을 준비하지 못했어요. ${esc(e.message)}</p>`); });
})();
