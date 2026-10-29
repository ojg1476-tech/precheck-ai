/* 처분을 돈으로: 1차 위반 행정처분 기간 × 하루 매출.
   기간은 rules.json의 penalties 문구(시행규칙 별표7 기준)와 같은 값이다. 바꾸면 penalties 문구도 같이 확인할 것. */
(function (root) {
  "use strict";
  // [최소 일수, 최대 일수, 범위] — 범위: product = 그 제품 광고 정지, store = 판매업 전체 영업정지
  const STOP = {
    cA: [90, 90, "product", "해당 제품 광고업무정지 3개월"],
    cB: [60, 60, "product", "해당 제품 광고업무정지 2개월"],
    cAB: [60, 90, "product", "해당 제품 광고업무정지 2~3개월"],
    f1: [60, 60, "store", "영업정지 2개월"],
    f2: [15, 15, "store", "영업정지 15일"],
    f3: [15, 15, "store", "영업정지 15일"],
    f5: [7, 7, "store", "영업정지 7일"],
    f6: [7, 15, "store", "영업정지 7~15일(2026.11.27부터)"],
  };
  // 기간이 정해져 있지 않거나 1차가 시정명령인 것: 돈으로 바꾸지 않는다
  const NO_DAYS = ["cP", "cX", "f34", "f4", "fP"];

  function stopFor(key, type) {
    const s = STOP[key];
    if (!s) return null;
    if (key === "f2" && type === "hfood") return [30, 30, "store", "영업정지 1개월"];   // 건강기능식품은 1개월
    return s;
  }

  /* findings(빨강·주황만) 중 가장 긴 처분 하나. 처분은 더해지지 않고 가장 무거운 것 기준으로 본다. */
  function worstStop(findings, type) {
    let best = null;
    for (const f of findings) {
      if (f.grade === "blue") continue;
      const s = stopFor(f.penaltyKey, type);
      if (s && (!best || s[1] > best[1])) best = s;
    }
    return best && { min: best[0], max: best[1], scope: best[2], label: best[3] };
  }

  function won(n) {
    if (n >= 1e8) return (Math.round(n / 1e7) / 10).toLocaleString("ko-KR") + "억 원";
    if (n >= 1e4) return Math.round(n / 1e4).toLocaleString("ko-KR") + "만 원";
    return Math.round(n).toLocaleString("ko-KR") + "원";
  }

  function lossText(stop, daily) {
    if (!stop || !daily) return "";
    return stop.min === stop.max ? won(stop.min * daily) : `${won(stop.min * daily)}~${won(stop.max * daily)}`;
  }

  const api = { STOP, NO_DAYS, stopFor, worstStop, lossText, won };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MoonguLoss = api;
})(typeof window !== "undefined" ? window : globalThis);
