/* 일괄 점검 결과 → 엑셀 리포트 (precheck/report.py 와 같은 4개 시트). */
(function (root) {
  "use strict";
  const M = root.Moongu || (typeof require !== "undefined" ? require("./engine.js") : null);
  const X = root.MiniXLSX || (typeof require !== "undefined" ? require("./xlsx.js") : null);
  const TYPE_NAME = { cos: "일반 화장품", fcos: "기능성 화장품", food: "일반 식품", hfood: "건강기능식품", "": "-" };
  const NOTICE = "이 리포트는 공개된 법령·식약처 기준·실제 단속 사례에 비춰 문제가 될 수 있는 표현을 알려 주는 점검 자료예요. "
    + "법적으로 위반인지 확정하는 판단은 아니며, 최종 확인은 관계 기관이나 전문가에게 받으세요.";
  const STYLES = {
    head: { bold: true, color: "FFFFFF", fill: "0F5B48" }, title: { bold: true, size: 15, wrap: false },
    muted: { color: "5F6B67", wrap: false }, bold: { bold: true, wrap: false }, cell: {},
    "높음": { fill: "FCE8EA", bold: true, color: "B4232F" }, "중간": { fill: "FBF1DF", bold: true, color: "8A5A00" },
    "확인": { fill: "E6EEF8", bold: true, color: "2D64B0" }, "양호": { fill: "E4F2E9", bold: true, color: "2F855A" },
    "오류": { fill: "EEF1EF", bold: true, color: "5F6B67" },
    red: { fill: "FCE8EA", bold: true, color: "B4232F" }, amber: { fill: "FBF1DF", bold: true, color: "8A5A00" }, blue: { fill: "E6EEF8", bold: true, color: "2D64B0" },
  };
  const ORDER = { red: 0, amber: 1, blue: 2 };

  function table(header, rows) { return [header.map(h => ({ v: h, s: "head" })), ...rows.map(r => r.map(v => (v && typeof v === "object") ? v : { v, s: "cell" }))]; }

  function buildReport(results, checker, today = new Date().toISOString().slice(0, 10)) {
    const ov = M.overview(results, checker);
    const sum = [[{ v: "상세페이지 광고 일괄 점검 리포트", s: "title" }], [{ v: `점검일 ${today} · 기준 버전 ${checker.version} · 규칙 ${checker.rules.length}개`, s: "muted" }], []];
    sum.push([{ v: "점검한 상품", s: "bold" }, ov.total]);
    for (const [k, v] of Object.entries(ov.tiers)) sum.push([{ v: "위험도 " + k, s: k }, v]);
    sum.push([], [{ v: "여러 상품에서 반복된 문제", s: "bold" }]);
    for (const [name, n] of ov.common) sum.push([name, `${n}개 상품`]);
    if (!ov.common.length) sum.push(["-"]);
    sum.push([], [{ v: "위험도 뜻", s: "bold" }]);
    for (const t of ["높음: 꼭 고쳐야 할 표현이 하나 이상 있어요.", "중간: 문제가 될 수 있어 확인이 필요한 표현이 있어요.",
      "확인: 쓸 수는 있지만 증명 자료나 인정 여부를 확인해야 하는 표현만 있어요.", "양호: 기본 검사에서 걸린 표현이 없어요.",
      "같은 위험도 안에서는 형사처벌이 무거운 상품이 먼저 와요."]) sum.push([t]);
    sum.push([], [NOTICE]);
    const noticeRow = sum.length;

    const rank = results.map((p, i) => {
      const c = p.counts;
      return [i + 1, p.name, TYPE_NAME[p.productType] ?? p.productType, { v: p.tier, s: p.tier }, M.penaltyText(p.maxPenalty),
        c.red, c.amber, c.blue, p.score, p.error || ""];
    });
    const detail = [];
    for (const p of results) {
      for (const f of p.findings.slice().sort((a, b) => ORDER[a.grade] - ORDER[b.grade] || a.start - b.start)) {
        detail.push([p.name, { v: f.gradeName, s: f.grade }, f.phrase, f.label, f.why, f.alt, f.checks.map(c => "□ " + c).join("\n"), f.penalty, f.law, f.source]);
      }
    }
    const basis = [
      "화장품: 화장품법 제13조·제14조·제37조, 시행규칙 별표5(표시·광고 준수사항)·별표7(행정처분 기준), 대한화장품협회 「화장품 광고자문 기준 및 해설서」(2025)",
      "식품: 식품 등의 표시·광고에 관한 법률 제8조·제26조·제27조, 시행령 별표1(부당한 표시·광고의 내용), 시행규칙 별표7(행정처분 기준)",
      "형사처벌은 법에 정해진 최대치예요. 실제 처벌은 사안마다 달라요.",
      "행정처분 기간은 처음 위반했을 때 기준이고, 1년 안에 반복하면 늘어나요. 식품은 판매업 기준이에요.",
      "‘꼭 고치기’는 기준에 금지로 적힌 표현, ‘확인 필요’는 맥락에 따라 위반이 될 수 있는 표현, ‘자료 챙기기’는 증명 자료가 있어야 쓰는 표현이에요.",
      NOTICE,
    ];
    return X.writeWorkbook([
      { name: "요약", rows: sum, widths: [48, 14, 10, 10], merges: [`A${noticeRow}:D${noticeRow}`], heights: { [noticeRow]: 48 } },
      { name: "위험 순위", rows: table(["순위", "상품명", "제품 종류", "위험도", "가장 무거운 형사처벌(최대)", "꼭 고치기", "확인 필요", "자료 챙기기", "점수", "메모"], rank),
        widths: [6, 26, 14, 9, 30, 9, 9, 10, 7, 28], freeze: 1 },
      { name: "상세", rows: table(["상품명", "등급", "찾은 표현", "쉬운 이름", "왜 문제인가", "대신 이렇게", "쓰기 전에 확인할 것", "이대로 두면", "관련 기준", "출처"], detail),
        widths: [20, 10, 18, 20, 36, 26, 44, 44, 30, 28], freeze: 1 },
      { name: "기준 안내", rows: [[{ v: "이 점검의 기준과 출처", s: "title" }], [], ...basis.map(t => [t])], widths: [110],
        heights: Object.fromEntries(basis.map((_, i) => [i + 3, 36])) },
    ], STYLES);
  }

  const api = { buildReport, TYPE_NAME };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MoonguReport = api;
})(typeof window !== "undefined" ? window : globalThis);
