// 웹 검사기의 rules.js → rules/rules.json (웹과 Python이 같은 기준을 쓰도록)
const fs=require("fs"),path=require("path");
const src=fs.readFileSync(path.join(__dirname,"rules_web.js"),"utf8");
const {R,PEN,S,CAT,RCAT,PRO}=new Function(src+";return {R,PEN,S,CAT,RCAT,PRO};")();
const pro=t=>{if(!PRO[t])throw new Error("정식 유형명 없음: "+t);return PRO[t];};
const CATX=Object.fromEntries(Object.entries(CAT).map(([k,v])=>[k,{...v,name:pro(v.name),easy:v.name}]));
const penKey=v=>v?Object.keys(PEN).find(k=>PEN[k]===v):null;
const rules=R.map(([re,g,t,why,alt,term,lawC,lawF,penC,penF,f,src],i)=>({
  id:"R"+String(i+1).padStart(2,"0"),pattern:re.source,ignore_case:re.flags.includes("i"),
  grade:g,label:pro(t),easy:t,why,alt,term,law_cos:lawC||null,law_food:lawF||null,
  penalty_cos:penKey(penC),penalty_food:penKey(penF),category_cos:RCAT[i][0]||null,category_food:RCAT[i][1]||null,applies_to:f,source:src}));
const out={version:"2026-10-29",note:"모든 처분·근거는 법령 원문과 KCIA 해설서(2025)에서 확인한 것만 씀. 기준표: https://claude.ai/artifact/8HRdhmVBaGQhDZA8AW4Psm",
  product_types:{cos:"일반 화장품",fcos:"기능성 화장품",food:"일반 식품",hfood:"건강기능식품"},
  grades:{red:"꼭 고치기",amber:"확인 필요",blue:"자료 챙기기"},penalties:PEN,sources:S,categories:CATX,rules};
fs.writeFileSync(path.join(__dirname,"..","rules","rules.json"),JSON.stringify(out,null,1));
// 웹 화면(web/)도 같은 규칙 파일과 예시 목록을 쓴다
// 건강기능식품 원료별 인정 기능성 (tools/build_hfood.py) — Python은 rules/hfood.json을 따로 읽는다
const hf=path.join(__dirname,"..","rules","hfood.json");
fs.writeFileSync(path.join(__dirname,"..","web","rules.json"),JSON.stringify(fs.existsSync(hf)?{...out,hfood:JSON.parse(fs.readFileSync(hf,"utf8"))}:out));
fs.copyFileSync(path.join(__dirname,"..","examples","sample_products.csv"),path.join(__dirname,"..","web","sample_products.csv"));
// '예시로 해보기'·'예시 넣기'에 쓰는 가상 상품들
fs.copyFileSync(path.join(__dirname,"..","examples","examples.json"),path.join(__dirname,"..","web","examples.json"));
console.log(rules.length+" rules, "+Object.keys(PEN).length+" penalty texts");
