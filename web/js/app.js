/* 문구레이더 화면 동작. 모든 검사는 이 브라우저 안에서만 돌고, 파일은 어디에도 보내지 않는다. */
(function () {
  "use strict";
  const M = window.Moongu, R = window.MoonguReport, L = window.MoonguLoss, SE = window.MoonguSeason;
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const TIER = {
    "높음": ["var(--red)", "꼭 고칠 표현이 있어요"], "중간": ["var(--amber)", "확인이 필요해요"],
    "확인": ["var(--blue)", "증명 자료를 챙기세요"], "양호": ["var(--ok)", "걸린 표현이 없어요"], "오류": ["var(--gray)", "읽지 못했어요"],
  };
  const GRADE = { red: ["var(--red)", "var(--red-50)"], amber: ["var(--amber)", "var(--amber-50)"], blue: ["var(--blue)", "var(--blue-50)"], ai: ["var(--violet)", "var(--violet-50)"] };
  const ORDER = { red: 0, amber: 1, blue: 2 };
  const TYPES = [["cos", "일반 화장품"], ["fcos", "기능성 화장품"], ["food", "일반 식품"], ["hfood", "건강기능식품"]];
  const state = { ck: null, results: null, source: "", ocr: null, pick: 0, imgFiles: [], season: [], news: null, enforced: null };

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
      out += esc(text.slice(pos, f.start)) + `<mark class="g-${f.grade} ${cls}" data-i="${f._i ?? i}" style="--c:${c};--b:${b}">${esc(text.slice(f.start, f.end))}</mark>`;
      pos = f.end;
    });
    return out + esc(text.slice(pos));
  }

  /* 이대로 두면 얼마 손해: 1차 위반 처분 기간 × 하루 매출 */
  const daily = {};   // key → 하루 매출 (store = 가게 전체, p:<상품> = 그 상품)
  try { const v = +localStorage.getItem("moongu-daily-store"); if (v > 0) daily.store = v; } catch (e) { /* 저장소 없음 */ }
  function lossHTML(stop, key) {
    if (!stop) return "";
    const v = daily[key] || 0, store = stop.scope === "store";
    return `<div class="loss" data-key="${esc(key)}" data-min="${stop.min}" data-max="${stop.max}">
      <div class="lh"><b>이대로 두면 얼마 손해?</b><span>${esc(stop.label)} · 1차 위반 기준</span></div>
      <label class="li"><span>${store ? "가게 하루 매출" : "이 상품 하루 매출"}</span>
        <input inputmode="numeric" autocomplete="off" placeholder="예: 300,000" value="${v ? v.toLocaleString("ko-KR") : ""}"><span>원</span></label>
      <div class="lv">${lossLine(stop, v)}</div>
      <p class="ln">${store ? "식품은 상품 하나만 걸려도 가게 전체 영업이 멈춰요." : "화장품은 걸린 제품의 광고(판매 페이지)가 멈춰요."} 게시물 접속 차단과 형사처벌은 이와 별도예요.</p>
    </div>`;
  }
  function lossLine(stop, v) {
    return v ? `최대 <b>${L.lossText(stop, v)}</b>어치 매출이 멈출 수 있어요` : `하루 매출을 넣으면 금액으로 계산해 드려요`;
  }
  function onLossInput(e) {
    const box = e.target.closest(".loss"); if (!box || e.target.tagName !== "INPUT") return;
    const digits = e.target.value.replace(/[^0-9]/g, "").slice(0, 12), v = +digits || 0;
    e.target.value = v ? v.toLocaleString("ko-KR") : "";
    const key = box.dataset.key; daily[key] = v;
    if (key === "store") { try { localStorage.setItem("moongu-daily-store", String(v)); } catch (err) { /* 무시 */ } }
    const stop = { min: +box.dataset.min, max: +box.dataset.max };
    document.querySelectorAll(`.loss[data-key="${CSS.escape(key)}"]`).forEach(b => {
      if (b !== box) { const i = b.querySelector("input"); if (i) i.value = e.target.value; }
      b.querySelector(".lv").innerHTML = lossLine({ min: +b.dataset.min, max: +b.dataset.max }, v);
    });
    if (box.querySelector(".lv")) box.querySelector(".lv").innerHTML = lossLine(stop, v);
    if (v) countOnce("loss-calc");
  }

  /* 같은 규칙에 걸린 표현은 카드 하나로 */
  function cards(fs, type = "") {
    const groups = new Map();
    fs.map((f, i) => ({ f, i })).sort((a, b) => ORDER[a.f.grade] - ORDER[b.f.grade] || a.f.start - b.f.start)
      .forEach(x => { const k = x.f.ruleId + x.f.grade + (/^H/.test(x.f.ruleId) ? x.f.why : ""); if (!groups.has(k)) groups.set(k, []); groups.get(k).push(x); });
    return [...groups.values()].map(g => {
      const f = g[0].f, [c, b] = GRADE[f.grade];
      const seen = new Set(), chips = g.filter(x => !seen.has(x.f.phrase) && seen.add(x.f.phrase))
        .map(x => `<button type="button" data-i="${x.i}" title="문구에서 위치 보기">${esc(x.f.phrase)}</button>`).join("");
      const ex = realExamples(f, type);
      const real = ex.length ? `<div class="real-ex"><b>같은 유형으로 실제 적발된 문구</b>${ex.map(p =>
        `<a href="${esc(p.src)}" target="_blank" rel="noopener" title="${esc(p.site)}${p.year ? " · " + p.year + "년" : ""}">‘${esc(p.t)}’</a>`).join("")}</div>` : "";
      const checks = f.checks.length ? `<div class="checks"><b>쓰기 전에 확인할 것</b>${f.checks.map(t =>
        `<label><input type="checkbox"><span>${esc(t)}</span></label>`).join("")}</div>` : "";
      return `<article class="fcard" style="--c:${c};--b:${b}">
        <div class="hd"><span class="grade">${esc(f.gradeName)}</span><span class="lb">${esc(f.label)}</span></div>
        ${f.easy && f.easy !== f.label ? `<p class="easy">${esc(f.easy)}</p>` : ""}
        <div class="phs">${chips}</div>
        <p class="why">${esc(f.why)}</p>
        <div class="two">${f.penalty ? `<div class="risk"><b>이대로 두면</b>${esc(f.penalty)}</div>` : ""}<div class="alt"><b>대신 이렇게</b>${esc(f.alt)}</div></div>
        ${real}
        ${checks}
        <details><summary>근거 보기</summary><p>정확한 용어: ${esc(f.term)}<br>관련 기준: ${esc(f.law)}<br>출처: ${esc(f.source)}</p></details>
      </article>`;
    }).join("");
  }

  /* 건강기능식품: 원고에서 찾은 원료와 대조 안내 */
  function ingLine(text, type, ctx = {}) {
    if (type !== "hfood" || !text.trim() || !state.ck.hfood) return "";
    state.ck.check(text, type, ctx);
    const ings = state.ck.lastIngredients || [], prod = state.ck.lastProduct;
    if (prod) return `<div class="ing"><b>신고 제품 대조</b><span>찾은 제품 <em>${esc(prod.name)}</em> 품목제조신고번호 ${esc(prod.no)}${prod.count > 1 ? ` (같은 이름 제품 ${prod.count}개)` : ""} — 이 제품이 식약처에 신고한 기능성과 원고의 효능 표현을 하나씩 맞춰 봤어요.</span>
      <div class="ing-ok"><b>이 제품이 쓸 수 있는 기능성 문구</b>${prod.claims.map(c => `<span>${esc(c)}</span>`).join("")}</div>
      <small>식품안전나라 건강기능식품 품목제조 신고사항 기준. 다른 제품이면 오른쪽 위 칸에 정확한 제품명이나 신고번호를 넣어 주세요.</small></div>`;
    if (!ings.length) return `<div class="ing"><b>원료 대조</b><span>원고에서 기능성 원료 이름을 찾지 못했어요. ‘홍삼’, ‘루테인’, ‘Lactobacillus gasseri BNR17’처럼 원료명을 넣으면 식약처가 그 원료에 인정한 기능성과 맞는지 대조해 드려요.</span></div>`;
    const names = [...new Set(ings.map(g => g.name))];
    return `<div class="ing"><b>원료 대조</b><span>찾은 원료 <em>${names.map(esc).join("</em><em>")}</em> — 식약처가 이 원료에 인정한 기능성과 원고의 효능 표현을 하나씩 맞춰 봤어요. <small>식품안전나라 원료 인정 자료 ${state.ck.hfood.items.length.toLocaleString("ko-KR")}종 기준</small></span></div>`;
  }

  /* ── 익명 사용 집계 (GoatCounter: 방문·버튼 횟수만, 문구·파일 내용은 보내지 않음) ── */
  function count(path, event = true) {
    const send = () => { try { window.goatcounter.count({ path, title: path, event }); } catch (e) { /* 집계 실패는 무시 */ } };
    if (window.goatcounter && window.goatcounter.count) send(); else window.addEventListener("load", send, { once: true });
  }
  const once = new Set();
  function countOnce(path) { if (!once.has(path)) { once.add(path); count(path); } }

  /* 결과 아래: 도움 여부 + 준비 중 기능(수요 확인용) */
  function pulse() {
    document.querySelectorAll(".pulse").forEach(el => {
      const w = el.dataset.where;
      el.innerHTML = `<div class="pulse-in glass">
        <div class="fb"><b>점검 결과가 도움이 됐나요?</b>
          <span class="fb-btns"><button type="button" data-fb="up">👍 도움됐어요</button><button type="button" data-fb="down">👎 아쉬워요</button></span></div>
        <div class="door"><div><span class="soon">준비 중</span><b>매주 자동 점검</b>
          <p>스마트스토어·쿠팡 상품을 한 번 연결해 두면, 새로 올린 상품과 바뀐 식약처 기준을 매주 자동으로 점검해 알려드려요.</p></div>
          <button type="button" class="btn ghost" data-door>나오면 쓰고 싶어요</button></div></div>`;
      el.addEventListener("click", e => {
        const fb = e.target.closest("[data-fb]"), door = e.target.closest("[data-door]");
        if (fb) {
          countOnce(`fb-${fb.dataset.fb}-${w}`);
          fb.closest(".fb").innerHTML = `<b>${fb.dataset.fb === "up" ? "알려 주셔서 고마워요!" : "알려 주셔서 고마워요. 더 다듬을게요."}</b>`;
        } else if (door) {
          countOnce(`door-auto-${w}`);
          door.outerHTML = `<span class="door-ok">고마워요! 원하는 분이 많으면 먼저 만들게요.</span>`;
        }
      });
    });
  }

  /* ── 라우팅 ─────────────────────────── */
  function route() {
    const h = location.hash.replace(/^#\/?/, "");
    const r = h.startsWith("text") ? "text" : h.startsWith("about") ? "about" : h.startsWith("season") ? "season" : "batch";
    document.querySelectorAll(".nav a").forEach(a => { if (a.dataset.route !== r) a.removeAttribute("aria-current"); else a.setAttribute("aria-current", "page"); });
    let v = r;
    if (r === "batch") v = state.results ? "batch-result" : state.imgFiles.length ? "batch-images" : "batch-start";
    document.querySelectorAll(".view").forEach(s => (s.hidden = s.dataset.view !== v));
    if (route.last !== r) { route.last = r; count(r === "batch" ? "/" : "/" + r, false); }
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
    try { run(await readTable(table), table.name); count("check-file"); }
    catch (e) { showError("파일을 읽지 못했어요. " + e.message); }
  }

  /* 예시 상품 (examples/examples.json, 가상의 상품들) */
  let exP = null;
  const examples = () => (exP = exP || fetch("examples.json").then(r => r.json()).then(d => d.items).catch(e => { exP = null; throw e; }));
  const shuffle = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

  /* 신고 제품 표(약 0.8MB)는 건강기능식품을 검사할 때만 받는다 */
  let productsP = null;
  function ensureProducts() {
    if (!state.ck.hfood || state.ck.products) return Promise.resolve();
    if (!productsP) productsP = fetch("hfood_products.json").then(r => r.json()).then(d => state.ck.setProducts(d)).catch(() => { productsP = null; });
    return productsP;
  }
  const hasHfood = items => items.some(it => { try { return M.normalizeType(it.type) === "hfood"; } catch (e) { return false; } });

  function run(items, source, ocr = null) {
    if (hasHfood(items) && !state.ck.products && state.ck.hfood) { ensureProducts().then(() => run(items, source, ocr)); return; }
    state.results = M.checkProducts(items, state.ck); state.ai = null;
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
    count("check-image");
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
        <div class="card urgent"><h3>먼저 고칠 상품<small>형사처벌이 무거운 순서</small></h3>${urgentHTML}</div>${sumLoss(res)}</div>
      <div><div class="card"><h3>여러 상품에서 반복된 문제<small>꼭 고치기·확인 필요 기준</small></h3><div class="bars">${bars}</div></div>${sumSeason(res)}</div></div>`;

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
    renderAIBatchBox();

    // 읽어 낸 글
    if (state.ocr) $("#tp-ocr").innerHTML = `<p class="sub" style="margin:0 0 12px">이미지에서 읽어 낸 글이에요. 잘못 읽은 곳이 있으면 글을 고쳐 ‘문구 하나 검사’에 넣어 보세요.</p>` +
      Object.entries(state.ocr).map(([n, t]) => `<div class="copybox"><div class="cap"><span>${esc(n)}</span></div><div class="copytext open">${esc(t) || "(읽은 글 없음)"}</div></div>`).join("");
  }

  /* 요약: 식품은 가게 전체 영업정지라 가장 긴 처분 하나만, 화장품은 상품별 광고 정지 개수 */
  function sumLoss(res) {
    let food = null, foodN = 0, cosN = 0;
    for (const r of res) {
      const s = L.worstStop(r.findings, r.productType); if (!s) continue;
      if (s.scope === "store") { foodN++; if (!food || s.max > food.max) food = s; } else cosN++;
    }
    if (!food && !cosN) return "";
    const cos = cosN ? `<p class="ln">화장품 ${cosN}개는 걸린 제품마다 광고업무정지 2~3개월이 따로 걸려요. 상품별 금액은 ‘상품별 자세히’에서 계산해 보세요.</p>` : "";
    if (!food) return `<div class="card loss-card"><h3>이대로 두면 얼마 손해?</h3>${cos}</div>`;
    return `<div class="card loss-card"><h3>이대로 두면 얼마 손해?<small>식품 ${foodN}개 중 가장 무거운 처분 기준</small></h3>${lossHTML(food, "store")}${cos}</div>`;
  }

  /* 요약: 맡긴 상품에 필요한 소식 (다가오는 단속 시즌 + 해당 최신 소식) */
  function sumSeason(res) {
    if (!state.season.length && !state.news) return "";
    const P = window.MoonguRelevance.personalize(res, { season: state.season, news: state.news });
    const nm = ps => ps.slice(0, 3).map(p => esc(p.name)).join(", ") + (ps.length > 3 ? ` 외 ${ps.length - 3}개` : "");
    const rows = [
      ...P.season.map(({ e, products }) => `<li><span class="sw">${SE.soon(e)}</span><span><b>${esc(e.theme)}</b> <span class="dm d-${e.domain}">${SE.DOMAIN_NAME[e.domain]}</span>
        <span class="mt">과거 이맘때 단속 · ${esc(e.tip)}</span><span class="pn">해당 상품: ${nm(products)}</span></span></li>`),
      ...P.news.map(({ item: n, level, products }) => `<li><span class="sw ${n.kind === "제도" ? "po" : "en"}">${n.kind === "제도" ? "기준 변경" : "최신 단속"}</span><span>
        <a href="${esc(n.url)}" target="_blank" rel="noopener"><b>${esc(n.title)}</b></a>
        <span class="mt">${esc(n.date.replace(/-/g, "."))}${products[0] && products[0].hit ? ` · 겹친 표현 ‘${esc(products[0].hit)}’` : ""}</span>
        <span class="pn">${level === "분야" ? `같은 분야 상품 전체 (${products.length}개)` : "해당 상품: " + nm(products)}</span></span></li>`),
    ].slice(0, 6).join("");
    return `<div class="card sea-card"><h3>내 상품에 필요한 소식<small>올린 상품의 분야·표현과 겹치는 것만</small></h3>
      ${rows ? `<ul>${rows}</ul>` : `<p class="empty-s">지금은 올린 상품에 해당하는 단속 시즌이나 소식이 없어요.</p>`}
      <p class="ln">엑셀 리포트의 ‘맞춤 소식’ 시트에 전부 정리돼요.</p>
      <a class="more" href="#/season">단속 달력과 전체 소식 보기 →</a></div>`;
  }

  function renderDetail() {
    const r = state.results[state.pick];
    document.querySelectorAll("#plist button").forEach(b => b.setAttribute("aria-selected", String(+b.dataset.pick === state.pick)));
    const aiH = (state.ai && state.ai.get(state.pick)) || [];
    if (!r || (!r.findings.length && !aiH.length)) { $("#pdetail").innerHTML = ""; return; }
    const c = r.counts;
    $("#pdetail").innerHTML = `<div class="ph-head"><h3>${esc(r.name)}</h3>${tierTag(r.tier)}<span class="mt">${esc(R.TYPE_NAME[r.productType])} · 꼭 고치기 ${c.red}, 확인 필요 ${c.amber}, 자료 챙기기 ${c.blue}</span></div>
      ${r.maxPenalty ? `<p class="ph-pen">이대로 두면 최대 <b>${M.penaltyText(r.maxPenalty)}</b></p>` : ""}
      ${(() => { const s = L.worstStop(r.findings, r.productType); return s ? lossHTML(s, s.scope === "store" ? "store" : "p:" + r.name) : ""; })()}
      <div class="copybox"><div class="cap"><span>상세 문구</span><button type="button" id="copy-more">전체 보기</button></div>
        <div class="copytext" id="copytext">${marked(r.text, withAI(r.findings, (state.ai && state.ai.get(state.pick)) || []))}</div></div>
      ${ingLine(r.text, r.productType, { name: r.name })}${cards(r.findings, r.productType)}${aiCard((state.ai && state.ai.get(state.pick)) || [])}`;
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
    const blob = R.buildReport(state.results, state.ck, undefined, { season: state.season, news: state.news, enforced: state.enforced,
      ai: state.ai ? [...state.ai.entries()].flatMap(([i, hs]) => hs.map(h => ({ name: state.results[i].name, ...h }))) : null });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = `moonguradar_report_${new Date().toLocaleDateString("sv-SE")}.xlsx`;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    toast("엑셀 리포트를 받았어요");
    count("report-download");
  }

  /* ── 문구 하나 검사 ──────────────────── */
  let txtType = "cos", lastFs = [];
  function checkText() {
    const ed = $("#ed"), text = ed.value;
    const ctx = txtType === "hfood" ? { name: $("#ed-prod-in").value.trim() } : {};
    if (txtType === "hfood" && !state.ck.products && state.ck.hfood) ensureProducts().then(() => { if (state.ck.products) checkText(); });
    lastFs = text.trim() ? state.ck.check(text, txtType, ctx) : [];
    if (text.trim()) countOnce("check-text");
    const aiHits = aiText.text === text && txtType !== "hfood" ? aiText.hits : [];
    $("#ed-hl").innerHTML = marked(text, withAI(lastFs, aiHits)) + "\n";
    $("#ed-count").textContent = `${text.length.toLocaleString("ko-KR")}자`;
    const c = M.summarize(lastFs);
    $("#ed-sum").innerHTML = [["red", "꼭 고치기"], ["amber", "확인 필요"], ["blue", "자료 챙기기"]].map(([g, n]) =>
      `<div class="${c[g] ? "" : "zero"}"><div class="k"><span class="sq" style="--c:${GRADE[g][0]}"></span>${n}</div><div class="v">${c[g]}</div></div>`).join("");
    const st = text.trim() ? L.worstStop(lastFs, txtType) : null;
    $("#ed-loss").innerHTML = st ? lossHTML(st, st.scope === "store" ? "store" : "p:text") : "";
    $("#ed-cards").innerHTML = !text.trim()
      ? `<div class="hint"><b>문구를 붙여 넣어 주세요</b>상세페이지 글을 왼쪽에 넣으면 고칠 곳에 물결 밑줄을 긋고, 이유와 대신 쓸 말을 여기에 보여드려요. 처음이라면 위의 ‘예시 넣기’를 눌러 보세요. 누를 때마다 다른 예시가 나와요.</div>`
      : ingLine(text, txtType, ctx) + (lastFs.length ? cards(lastFs, txtType) : `<div class="hint"><b>걸린 표현이 없어요</b>기본 검사를 통과했어요. 중요한 광고는 협회 심의도 받아 보세요.</div>`) + aiCard(aiHits);
    renderAIBox("#ed-ai", text.trim() ? (aiText.text === text ? aiText : null) : null, "text");
    syncScroll();
    if (text.trim() && window.MoonguAI && MoonguAI.isReady() && aiText.text !== text) {
      clearTimeout(checkText.t); checkText.t = setTimeout(() => runAIText(), 700);
    }
  }
  function syncScroll() { const ed = $("#ed"); $("#ed-hl").parentElement.scrollTop = ed.scrollTop; }

  /* ── AI로 한 번 더 확인 (뜻 비교) ─────────── */
  let aiText = { text: null, hits: [] }, aiBusy = false;
  function withAI(fs, hits) {   // 규칙 결과와 AI 구절을 위치 순서로 합쳐 밑줄 긋기용으로
    return fs.map((f, i) => ({ ...f, _i: i })).concat(hits.map((h, k) => ({ grade: "ai", start: h.start, end: h.end, _i: "a" + k })))
      .sort((a, b) => a.start - b.start);
  }
  function aiCard(hits) {
    if (!hits.length) return "";
    const [c, b] = GRADE.ai;
    return `<article class="fcard ai-card" style="--c:${c};--b:${b}">
      <div class="hd"><span class="grade">AI 확인 필요</span><span class="lb">실제 적발 문구와 뜻이 비슷한 표현</span></div>
      <ul class="ai-list">${hits.map(h => `<li><b>‘${esc(h.text)}’</b><span>비슷한 실제 적발 문구: ‘${esc(h.near.t)}’</span></li>`).join("")}</ul>
      <p class="why">규칙에는 걸리지 않았지만, 실제로 적발된 문구와 뜻이 가까워요. 효능을 말하는 표현인지 직접 확인해 보세요.</p>
    </article>`;
  }
  function renderAIBox(sel, done, where) {
    const el = $(sel); if (!el) return;
    if (aiBusy) return;
    if (where === "text" && txtType === "hfood") {
      el.innerHTML = `<div class="ai-box"><span>건강기능식품은 식약처가 인정한 기능 문구를 쓸 수 있어서 AI 확인은 하지 않아요. 대신 원고 속 원료가 그 기능성을 인정받았는지 아래 ‘원료 대조’로 확인해요.</span></div>`;
      return;
    }
    if (done) {
      el.innerHTML = `<div class="ai-box done"><span class="ai-dot"></span><span>AI 확인 완료 · ${done.hits.length ? `뜻이 비슷한 표현 <b>${done.hits.length}곳</b>` : "더 찾은 표현이 없어요"}</span></div>`;
      return;
    }
    const ready = window.MoonguAI && MoonguAI.isReady();
    el.innerHTML = `<div class="ai-box"><div><b>AI로 한 번 더 확인</b><span>규칙에 없는 표현도 실제 적발 문구와 뜻을 비교해 찾아요.${ready ? "" : " 처음 한 번 AI 모델(약 110MB)을 받아요."} 문구는 이 브라우저 밖으로 나가지 않아요.</span></div>
      <button type="button" class="btn ghost ai-go" data-where="${where}">AI 확인</button></div>`;
  }
  async function aiLoad(el) {
    await MoonguAI.load((p, total) => { el.innerHTML = aiProgress(`AI 모델 받는 중 · ${Math.round(p * 100)}% (${Math.round(total / 1048576)}MB, 처음 한 번만)`, p); });
  }
  function aiProgress(msg, p) {
    return `<div class="ai-box busy"><div><b>${esc(msg)}</b><span class="prog"><i style="width:${(p * 100).toFixed(0)}%"></i></span></div></div>`;
  }
  async function runAIText() {
    const ed = $("#ed"), text = ed.value, el = $("#ed-ai");
    if (!text.trim() || aiBusy || txtType === "hfood") return;
    aiBusy = true;
    try {
      if (!MoonguAI.isReady()) { await aiLoad(el); countOnce("ai-load"); }
      el.innerHTML = aiProgress("AI가 문장을 살펴보는 중", 0);
      const hits = await MoonguAI.check(text, lastFs.map(f => [f.start, f.end]), (i, n) => { el.innerHTML = aiProgress(`AI가 문장을 살펴보는 중 · ${i}/${n}`, i / n); });
      if (ed.value === text) aiText = { text, hits };
      countOnce("ai-check-text");
    } catch (e) {
      el.innerHTML = `<div class="ai-box"><span>AI를 준비하지 못했어요. ${esc(e.message)}</span></div>`; aiBusy = false; return;
    }
    aiBusy = false;
    checkText();
  }
  async function runAIBatch() {
    const el = $("#res-ai"), res = state.results;
    if (aiBusy || !res) return;
    aiBusy = true;
    try {
      if (!MoonguAI.isReady()) { await aiLoad(el); countOnce("ai-load"); }
      // 건강기능식품은 인정받은 기능 문구를 쓸 수 있어 AI 확인에서 뺀다 (AI는 '기능을 말하는 표현'을 찾도록 배웠다)
      const todo = res.map((r, i) => [r, i]).filter(([r]) => r.text && !r.error && r.productType !== "hfood");
      state.ai = new Map();
      for (let k = 0; k < todo.length; k++) {
        const [r, i] = todo[k];
        el.innerHTML = aiProgress(`AI가 상품을 살펴보는 중 · ${k + 1}/${todo.length} ${r.name}`, k / todo.length);
        state.ai.set(i, await MoonguAI.check(r.text, r.findings.map(f => [f.start, f.end])));
      }
      countOnce("ai-check-batch");
    } catch (e) {
      el.innerHTML = `<div class="ai-box"><span>AI를 준비하지 못했어요. ${esc(e.message)}</span></div>`; aiBusy = false; return;
    }
    aiBusy = false;
    renderAIBatchBox(); renderDetail();
  }
  function renderAIBatchBox() {
    const el = $("#res-ai"); if (!el || aiBusy) return;
    if (state.ai) {
      const n = [...state.ai.values()].reduce((s, h) => s + h.length, 0), p = [...state.ai.values()].filter(h => h.length).length;
      el.innerHTML = `<div class="ai-box done"><span class="ai-dot"></span><span>AI 확인 완료 · ${n ? `상품 ${p}개에서 뜻이 비슷한 표현 <b>${n}곳</b>을 더 찾았어요. ‘상품별 자세히’와 엑셀 리포트에 함께 담겨요.` : "규칙 밖에서 더 찾은 표현이 없어요."}</span></div>`;
    } else renderAIBox("#res-ai", null, "batch");
  }

  /* ── 실제 적발 ───────────────────────── */
  // 같은 규칙에 걸리는 실제 적발 문구 (같은 분야 먼저, 최대 3개)
  function realExamples(f, type) {
    const E = state.enforced; if (!E || !E.byRule[f.ruleId]) return [];
    const cos = type === "cos" || type === "fcos";
    return E.byRule[f.ruleId].map(i => E.phrases[i]).filter(p => p.t !== f.phrase)
      .sort((a, b) => ((b.type === "cos" || b.type === "fcos") === cos) - ((a.type === "cos" || a.type === "fcos") === cos) || (b.year || 0) - (a.year || 0))
      .slice(0, 3);
  }
  function renderReal() {
    const E = state.enforced; if (!E) { document.querySelector(".real").hidden = true; return; }
    const food = E.yearly.filter(y => y.domain === "food"), max = Math.max(...food.map(y => y.n));
    const full = food.filter(y => y.months === 12), last = full[full.length - 1], prev = full[full.length - 2];
    const perDay = Math.round(last.n / 365), grow = Math.round((last.n / prev.n - 1) * 100);
    $("#real-main").innerHTML = `<div class="rm-top"><div><b class="big">${last.n.toLocaleString("ko-KR")}<small>건</small></b>
        <span class="lb">${last.year}년 식품 온라인 부당광고 적발</span></div>
        <div class="pills"><span>하루 평균 <b>${perDay}건</b></span><span>${prev.year}년보다 <b>${grow}%</b> 늘었어요</span></div></div>
      <div class="bars-y" role="img" aria-label="식품 온라인 부당광고 적발 건수: ${food.map(y => `${y.year}년${y.months < 12 ? `(1~${y.months}월)` : ""} ${y.n}건`).join(", ")}">
        ${food.map(y => `<div class="by${y === last ? " hi" : ""}${y.months < 12 ? " part" : ""}" tabindex="0">
          <span class="tip">${y.year}년${y.months < 12 ? ` 1~${y.months}월` : ""} · ${y.n.toLocaleString("ko-KR")}건</span>
          <span class="ba"><i style="height:${(y.n / max * 100).toFixed(1)}%"></i>${y === last || y.months < 12 ? `<span class="v" style="bottom:calc(${(y.n / max * 100).toFixed(1)}% + 5px)">${y.n.toLocaleString("ko-KR")}</span>` : ""}</span><span class="yl">${String(y.year).slice(2)}년${y.months < 12 ? `<br><em>1~${y.months}월</em>` : ""}</span></div>`).join("")}
      </div>`;
    const cosAll = E.types.find(t => t.domain === "cos" && t.type === "전체"), cosDrug = E.types.find(t => t.domain === "cos" && t.type === "의약품오인");
    const f25 = E.types.filter(t => t.domain === "food" && t.period === "2025"), hf = f25.find(t => t.type === "건기식오인"), dz = f25.find(t => t.type === "질병예방치료");
    const f25all = full[full.length - 1].n;
    $("#real-side").innerHTML = [
      cosAll && `<div class="rs glass"><b>${cosAll.n.toLocaleString("ko-KR")}<small>건</small></b><span>화장품 부당광고 적발 (2021년~2025년 9월)</span>
        <em>그중 <b>${Math.round(cosDrug.n / cosAll.n * 100)}%</b>가 ‘약처럼 보이는 표현’</em></div>`,
      hf && `<div class="rs glass"><b>${hf.n.toLocaleString("ko-KR")}<small>건</small></b><span>2025년 식품 적발 중 ‘건강기능식품처럼 보이는 표현’</span>
        <em>식품 적발의 <b>${Math.round(hf.n / f25all * 100)}%</b> · 질병 예방·치료 표현도 ${dz.n.toLocaleString("ko-KR")}건</em></div>`,
    ].filter(Boolean).join("");
    // 문구 벽: 분야별로 섞어서 최근 것 위주로
    // 화장품·식품을 번갈아 (최근 것 먼저)
    const seen = new Set(), grp = { c: [], f: [] };
    for (const p of E.phrases.slice().sort((a, b) => (b.year || 0) - (a.year || 0)))
      if (!seen.has(p.t) && p.t.length <= 18) { seen.add(p.t); grp[p.type === "cos" || p.type === "fcos" ? "c" : "f"].push(p); }
    const pick = [];
    for (let i = 0; pick.length < 28 && (i < grp.c.length || i < grp.f.length); i++) { if (grp.c[i]) pick.push(grp.c[i]); if (grp.f[i]) pick.push(grp.f[i]); }
    $("#real-wall").innerHTML = pick.map(p => `<a href="${esc(p.src)}" target="_blank" rel="noopener" class="rw d-${p.type === "fcos" ? "cos" : p.type}"
      title="${esc(p.cat)} · ${esc(p.site)}${p.year ? " · " + p.year + "년" : ""}">${esc(p.t)}<i>${SE.DOMAIN_NAME[p.type === "fcos" ? "cos" : p.type]}</i></a>`).join("");
    $("#real-src").textContent = `출처: 연도별·유형별 건수는 국정감사 자료를 인용한 보도(푸드투데이, 메디포뉴스), 문구는 식약처 발표를 인용한 보도 ${E.phrases.length}개에서 모았어요. 2026년은 1~8월 건수예요.`;
    $("#real-wall").addEventListener("click", e => { if (e.target.closest("a")) countOnce("real-phrase-click"); });
  }

  /* ── 단속 소식 ───────────────────────── */
  let newsCat = "all";
  function renderSeason() {
    const up = SE.upcoming(state.season), today = new Date();
    const end = new Date(today.getTime() + 61 * 864e5);
    $("#sea-range").textContent = `${today.getMonth() + 1}월 ${today.getDate()}일 ~ ${end.getMonth() + 1}월 ${end.getDate()}일`;
    $("#sea-up").innerHTML = up.length ? up.map(e => `<article class="sea-ev">
        <div class="top"><span class="sw">${SE.soon(e)}</span><span class="dm d-${e.domain}">${SE.DOMAIN_NAME[e.domain]}</span></div>
        <h4>${esc(e.theme)}</h4>
        <p class="mt">${esc(SE.when(e))}${e.total ? ` · <b>${e.total.toLocaleString("ko-KR")}건</b> 적발` : ""}</p>
        <p class="tip">${esc(e.tip)}</p>
        <a href="${esc(e.source)}" target="_blank" rel="noopener">출처</a></article>`).join("")
      : `<p class="empty-s">앞으로 두 달 동안 과거에 단속 발표가 있었던 시기가 없어요.</p>`;
    const months = Array.from({ length: 12 }, () => []);
    for (const e of state.season) months[+e.date.slice(5, 7) - 1].push(e);
    const now = today.getMonth();
    $("#sea-cal").innerHTML = months.map((evs, i) => `<div class="mo${i === now ? " now" : ""}"><div class="mh">${i + 1}월${i === now ? "<em>지금</em>" : ""}</div>
      ${evs.length ? evs.map(e => `<span class="ch d-${e.domain}" title="${esc(SE.when(e))} · ${esc(e.tip)}">${esc(e.theme)}<i>${e.date.slice(2, 4)}년</i></span>`).join("") : `<span class="none">발표 없음</span>`}</div>`).join("");
    renderNews();
  }
  function renderNews() {
    const N = state.news; if (!N) return;
    $("#news-upd").textContent = `${N.updated} 업데이트`;
    const items = N.items.filter(n => newsCat === "all" || n.cats.includes(newsCat)).sort((a, b) => b.date.localeCompare(a.date));
    $("#news-list").innerHTML = items.map(n => `<li><a href="${esc(n.url)}" target="_blank" rel="noopener">
      <div class="nh"><span class="nd">${esc(n.date.replace(/-/g, "."))}</span><span class="nk k-${n.kind === "단속" ? "en" : "po"}">${esc(n.kind)}</span>
        ${n.cats.map(c => `<span class="dm d-${c}">${SE.DOMAIN_NAME[c]}</span>`).join("")}</div>
      <b>${esc(n.title)}</b>${n.summary ? `<p>${esc(n.summary)}</p>` : ""}<span class="src">${esc(n.source)} ↗</span></a></li>`).join("")
      || `<li class="empty-s">이 분야의 소식이 아직 없어요.</li>`;
  }

  /* ── 시작 ───────────────────────────── */
  async function init() {
    const data = await (await fetch("rules.json")).json();
    state.ck = new M.Checker(data);
    $("#foot-v").textContent = `기준 ${state.ck.version} · 규칙 ${state.ck.rules.length}개 · 검사와 이미지 읽기는 모두 이 브라우저 안에서만 이뤄지고, 올린 파일은 어디에도 보내지 않아요.`;
    proof();
    pulse();
    try {
      const [sea, news, enf] = await Promise.all(["season.json", "news.json", "enforced.json"].map(f => fetch(f).then(r => r.json())));
      state.season = sea.events; state.news = news; state.enforced = enf;
    } catch (e) { /* 시즌·소식이 없어도 검사는 된다 */ }
    renderSeason();
    renderReal();
    const nf = $("#news-filter");
    nf.insertAdjacentHTML("beforeend", [["all", "전체"], ["cos", "화장품"], ["food", "식품"], ["hfood", "건강기능식품"]].map(([v, t]) =>
      `<label><input type="radio" name="news-cat" value="${v}"${v === "all" ? " checked" : ""}><span>${t}</span></label>`).join(""));
    nf.addEventListener("change", e => { newsCat = e.target.value; renderNews(); });
    $("#news-list").addEventListener("click", e => { if (e.target.closest("a")) countOnce("news-click"); });

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
      try {
        const ex = await examples();
        // 누를 때마다 다른 조합: 화장품 3 · 기능성 화장품 1 · 식품 3 · 건강기능식품 3
        const pick = [["cos", 3], ["fcos", 1], ["food", 3], ["hfood", 3]].flatMap(([t, n]) => shuffle(ex.filter(x => x.type === t)).slice(0, n));
        run(shuffle(pick).map((x, i) => ({ row: i + 1, name: x.name, type: x.type, text: x.text })), "예시 목록");
      } catch (e) {
        const t = await (await fetch("sample_products.csv")).text();
        run(M.readRows(M.parseCSV(t.replace(/^﻿/, ""))), "예시 목록");
      }
      count("check-sample");
    });
    $("#ed-example").addEventListener("click", async () => {
      const ex = (await examples()).filter(x => x.type === txtType && x.text !== $("#ed").value);
      if (!ex.length) return;
      const x = ex[Math.floor(Math.random() * ex.length)];
      $("#ed").value = x.text;
      if (txtType === "hfood") $("#ed-prod-in").value = "";
      checkText(); count("text-example");
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

    document.addEventListener("input", onLossInput);
    document.addEventListener("click", e => {
      const b = e.target.closest(".ai-go"); if (!b) return;
      b.dataset.where === "batch" ? runAIBatch() : runAIText();
    });
    seg($("#txt-type"), "txt-type", txtType, v => { txtType = v; $("#ed-prod").hidden = v !== "hfood"; checkText(); });
    $("#ed-prod-in").addEventListener("input", () => { clearTimeout(checkText.p); checkText.p = setTimeout(checkText, 200); });
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
