/* 의존성 없는 작은 엑셀(xlsx) 읽기·쓰기.
 * 쓰기: 압축 없는 zip(STORE) + 스타일(굵게·채우기 색·줄바꿈·열 너비·틀 고정).
 * 읽기: zip 목차 → DecompressionStream('deflate-raw')로 풀기 → 첫 시트를 2차원 배열로. */
(function (root) {
  "use strict";
  const enc = new TextEncoder();

  /* ── zip ───────────────────────────────── */
  const CRC = (() => {
    const t = new Uint32Array(256);
    for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; }
    return t;
  })();
  function crc32(buf) { let c = 0xffffffff; for (let i = 0; i < buf.length; i++) c = CRC[(c ^ buf[i]) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }

  function zipStore(files) { // files: [{name, data: Uint8Array}]
    const parts = [], central = []; let offset = 0;
    for (const f of files) {
      const name = enc.encode(f.name), crc = crc32(f.data), size = f.data.length;
      const h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint16(8, 0, true);
      h.setUint32(14, crc, true); h.setUint32(18, size, true); h.setUint32(22, size, true); h.setUint16(26, name.length, true);
      parts.push(new Uint8Array(h.buffer), name, f.data);
      const c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true);
      c.setUint32(16, crc, true); c.setUint32(20, size, true); c.setUint32(24, size, true); c.setUint16(28, name.length, true);
      c.setUint32(42, offset, true);
      central.push(new Uint8Array(c.buffer), name);
      offset += 30 + name.length + size;
    }
    const cdSize = central.reduce((s, p) => s + p.length, 0);
    const e = new DataView(new ArrayBuffer(22));
    e.setUint32(0, 0x06054b50, true); e.setUint16(8, files.length, true); e.setUint16(10, files.length, true);
    e.setUint32(12, cdSize, true); e.setUint32(16, offset, true);
    return new Blob([...parts, ...central, new Uint8Array(e.buffer)], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
  }

  async function unzip(buf) { // → Map(name → Uint8Array)
    const u8 = new Uint8Array(buf), dv = new DataView(buf);
    let eocd = -1;
    for (let i = u8.length - 22; i >= Math.max(0, u8.length - 65557); i--) if (dv.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
    if (eocd < 0) throw new Error("엑셀 파일을 열지 못했어요. 파일이 손상됐을 수 있어요.");
    const n = dv.getUint16(eocd + 10, true); let p = dv.getUint32(eocd + 16, true);
    const out = new Map(), dec = new TextDecoder();
    for (let k = 0; k < n; k++) {
      const method = dv.getUint16(p + 10, true), csize = dv.getUint32(p + 20, true);
      const nlen = dv.getUint16(p + 28, true), xlen = dv.getUint16(p + 30, true), clen = dv.getUint16(p + 32, true);
      const local = dv.getUint32(p + 42, true), name = dec.decode(u8.subarray(p + 46, p + 46 + nlen));
      p += 46 + nlen + xlen + clen;
      if (!/^xl\/(sharedStrings|workbook|worksheets\/sheet\d+)\.xml$|^xl\/_rels\/workbook\.xml\.rels$/.test(name)) continue;
      const start = local + 30 + dv.getUint16(local + 26, true) + dv.getUint16(local + 28, true);
      const data = u8.subarray(start, start + csize);
      if (method === 0) out.set(name, data);
      else if (method === 8) {
        const ds = new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
        out.set(name, new Uint8Array(await new Response(ds).arrayBuffer()));
      }
    }
    return out;
  }

  /* ── 읽기 ──────────────────────────────── */
  function colIndex(ref) { let n = 0; for (const ch of ref.replace(/\d+/g, "")) n = n * 26 + ch.charCodeAt(0) - 64; return n - 1; }

  async function readFirstSheet(buf, parseXML) {
    const files = await unzip(buf), dec = new TextDecoder();
    const xml = name => (files.has(name) ? parseXML(dec.decode(files.get(name))) : null);
    const shared = [];
    const ss = xml("xl/sharedStrings.xml");
    if (ss) for (const si of ss.getElementsByTagName("si")) shared.push([...si.getElementsByTagName("t")].map(t => t.textContent).join(""));
    let sheetPath = "xl/worksheets/sheet1.xml";
    const wb = xml("xl/workbook.xml"), rels = xml("xl/_rels/workbook.xml.rels");
    if (wb && rels) {
      const first = wb.getElementsByTagName("sheet")[0];
      const rid = first && (first.getAttribute("r:id") || first.getAttributeNS("http://schemas.openxmlformats.org/officeDocument/2006/relationships", "id"));
      for (const r of rels.getElementsByTagName("Relationship")) if (r.getAttribute("Id") === rid) sheetPath = "xl/" + r.getAttribute("Target").replace(/^\/?xl\//, "");
    }
    const sheet = xml(sheetPath);
    if (!sheet) throw new Error("엑셀의 첫 번째 시트를 찾지 못했어요.");
    const rows = [];
    for (const row of sheet.getElementsByTagName("row")) {
      const r = [];
      for (const c of row.getElementsByTagName("c")) {
        const t = c.getAttribute("t"), v = c.getElementsByTagName("v")[0];
        let val = "";
        if (t === "s" && v) val = shared[+v.textContent] || "";
        else if (t === "inlineStr") val = [...c.getElementsByTagName("t")].map(x => x.textContent).join("");
        else if (v) val = v.textContent;
        r[colIndex(c.getAttribute("r") || "A1")] = val;
      }
      rows.push(Array.from(r, x => x ?? ""));
    }
    return rows;
  }

  /* ── 쓰기 ──────────────────────────────── */
  const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;")
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, "");
  const colName = i => { let s = ""; i++; while (i) { const m = (i - 1) % 26; s = String.fromCharCode(65 + m) + s; i = Math.floor((i - 1) / 26); } return s; };

  /* sheets: [{name, rows: [[cell]], widths: [n], freeze: rowIndex|null, merges: ["A1:D1"], heights: {row: pt}}]
     cell: 값 또는 {v, s} — s는 스타일 이름(STYLES 키) */
  function writeWorkbook(sheets, styles) {
    const fills = ["none", "gray125"], fonts = [{}], xfs = [{ font: 0, fill: 0, wrap: false }], styleId = {};
    for (const [key, st] of Object.entries(styles)) {
      let fill = 0;
      if (st.fill) { fills.push(st.fill); fill = fills.length - 1; }
      let font = 0;
      if (st.bold || st.color || st.size) { fonts.push({ bold: st.bold, color: st.color, size: st.size }); font = fonts.length - 1; }
      xfs.push({ font, fill, wrap: st.wrap !== false });
      styleId[key] = xfs.length - 1;
    }
    const fontXML = f => `<font>${f.bold ? "<b/>" : ""}<sz val="${f.size || 11}"/>${f.color ? `<color rgb="FF${f.color}"/>` : ""}<name val="맑은 고딕"/></font>`;
    const fillXML = f => (f === "none" || f === "gray125") ? `<fill><patternFill patternType="${f}"/></fill>`
      : `<fill><patternFill patternType="solid"><fgColor rgb="FF${f}"/><bgColor indexed="64"/></patternFill></fill>`;
    const stylesXML = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">`
      + `<fonts count="${fonts.length}">${fonts.map(fontXML).join("")}</fonts><fills count="${fills.length}">${fills.map(fillXML).join("")}</fills>`
      + `<borders count="2"><border/><border><left style="thin"><color rgb="FFDCE2DF"/></left><right style="thin"><color rgb="FFDCE2DF"/></right><top style="thin"><color rgb="FFDCE2DF"/></top><bottom style="thin"><color rgb="FFDCE2DF"/></bottom></border></borders>`
      + `<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="${xfs.length}">`
      + xfs.map((x, i) => `<xf numFmtId="0" fontId="${x.font}" fillId="${x.fill}" borderId="${i ? 1 : 0}" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top"${x.wrap ? ' wrapText="1"' : ""}/></xf>`).join("")
      + `</cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>`;
    const sheetXML = sh => {
      const rows = sh.rows.map((row, ri) => {
        const ht = sh.heights && sh.heights[ri + 1] ? ` ht="${sh.heights[ri + 1]}" customHeight="1"` : "";
        return `<row r="${ri + 1}"${ht}>` + row.map((cell, ci) => {
          if (cell === null || cell === undefined || cell === "") return "";
          const v = typeof cell === "object" ? cell.v : cell, s = typeof cell === "object" && cell.s ? ` s="${styleId[cell.s]}"` : "";
          const ref = colName(ci) + (ri + 1);
          return typeof v === "number" ? `<c r="${ref}"${s}><v>${v}</v></c>` : `<c r="${ref}" t="inlineStr"${s}><is><t xml:space="preserve">${esc(v)}</t></is></c>`;
        }).join("") + "</row>";
      }).join("");
      const pane = sh.freeze ? `<sheetViews><sheetView workbookViewId="0"><pane ySplit="${sh.freeze}" topLeftCell="A${sh.freeze + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>` : "";
      const cols = sh.widths ? `<cols>${sh.widths.map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`).join("")}</cols>` : "";
      const merges = sh.merges && sh.merges.length ? `<mergeCells count="${sh.merges.length}">${sh.merges.map(m => `<mergeCell ref="${m}"/>`).join("")}</mergeCells>` : "";
      return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">${pane}${cols}<sheetData>${rows}</sheetData>${merges}</worksheet>`;
    };
    const ct = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>`
      + sheets.map((_, i) => `<Override PartName="/xl/worksheets/sheet${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join("") + `</Types>`;
    const rootRels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>`;
    const wb = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>`
      + sheets.map((s, i) => `<sheet name="${esc(s.name)}" sheetId="${i + 1}" r:id="rId${i + 1}"/>`).join("") + `</sheets></workbook>`;
    const wbRels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">`
      + sheets.map((_, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i + 1}.xml"/>`).join("")
      + `<Relationship Id="rId${sheets.length + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>`;
    const files = [
      { name: "[Content_Types].xml", data: enc.encode(ct) }, { name: "_rels/.rels", data: enc.encode(rootRels) },
      { name: "xl/workbook.xml", data: enc.encode(wb) }, { name: "xl/_rels/workbook.xml.rels", data: enc.encode(wbRels) },
      { name: "xl/styles.xml", data: enc.encode(stylesXML) },
      ...sheets.map((s, i) => ({ name: `xl/worksheets/sheet${i + 1}.xml`, data: enc.encode(sheetXML(s)) })),
    ];
    return zipStore(files);
  }

  const api = { writeWorkbook, readFirstSheet, unzip, zipStore, crc32 };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.MiniXLSX = api;
})(typeof window !== "undefined" ? window : globalThis);
