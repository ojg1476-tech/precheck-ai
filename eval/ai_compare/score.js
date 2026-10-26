// 그냥 AI(A1·A2) vs 규칙(B) vs 규칙+기준표 AI(C) 채점. 사용: node score.js <compare.html>
const fs=require("fs");
const h=fs.readFileSync(process.argv[2],"utf8");
const sc=[...h.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
const env=new Function(sc[0]+"\n"+sc[1].split("const $=id=>")[0]+";return {DATA,CATS,rulesVerdict,altFlagged,runRules};")();
const {DATA,CATS,rulesVerdict,altFlagged,runRules}=env;
const qmap=JSON.parse(fs.readFileSync("qmap.json"));            // T -> Q
const t2q=qmap, q2t=Object.fromEntries(Object.entries(qmap).map(([t,q])=>[q,t]));
const loadA=f=>Object.fromEntries(JSON.parse(fs.readFileSync(f)).map(([q,v,y,w,alt])=>[q2t[q],{verdict:v,pen:y!=null?[y,w]:null,alt:alt??null}]));
const A1=loadA("A1.json"),A2=loadA("A2.json"),Craw=JSON.parse(fs.readFileSync("C.json"));
const B={},C={};
for(const r of DATA){const b=rulesVerdict(r);B[r.id]=b;const cat=Craw[t2q[r.id]];
  if(b.verdict!=="허용"){C[r.id]={...b,by:"rules",cat};continue;}
  const c=CATS[cat];C[r.id]={verdict:!c?"허용":cat==="P"?"자료필요":"위반",pen:c?c[1]:null,by:"ai",cat};}
const M={A1,A2,B,C},out={},misses={};
for(const [m,R] of Object.entries(M)){const s={det:[0,0],strong:[0,0],fp:[0,0],cond:[0,0],pen:[0,0],alt:[0,0]};misses[m]={det:[],fp:[],pen:[],alt:[],cond:[]};
  for(const r of DATA){const v=R[r.id];const f=v.verdict!=="허용";
    if(r.label==="violation"){s.det[1]++;s.strong[1]++;if(f)s.det[0]++;else misses[m].det.push(r.text);if(v.verdict==="위반")s.strong[0]++;
      if(r.pen&&v.verdict==="위반"){s.pen[1]++;if(v.pen&&v.pen[0]===r.pen[0]&&v.pen[1]===r.pen[1])s.pen[0]++;else misses[m].pen.push(`${r.text}: 정답 ${r.pen[0]}년/${r.pen[1]/1e4}만, 답 ${v.pen?v.pen[0]+"년/"+v.pen[1]/1e4+"만":"없음"}`);}
      if(v.alt&&v.verdict==="위반"){s.alt[1]++;const fl=runRules(v.alt,r.type).filter(x=>x.g!=="blue");if(fl.length){s.alt[0]++;misses[m].alt.push(`${r.text} → ${v.alt}`);}}}
    if(r.label==="allowed"){s.fp[1]++;if(v.verdict==="위반"){s.fp[0]++;misses[m].fp.push(r.text);}}
    if(r.label==="conditional"){s.cond[1]++;if(f)s.cond[0]++;else misses[m].cond.push(r.text);}}
  out[m]=s;}
let same=0;for(const r of DATA)if(A1[r.id].verdict===A2[r.id].verdict)same++;out.consistency=[same,DATA.length];
let altSame=0,altN=0;for(const r of DATA)if(A1[r.id].alt&&A2[r.id].alt){altN++;if(A1[r.id].alt===A2[r.id].alt)altSame++;}out.altIdentical=[altSame,altN];
fs.writeFileSync("results.json",JSON.stringify({metrics:out,misses},null,1));
const p=([a,b])=>b?`${(a/b*100).toFixed(1)}% (${a}/${b})`:"-";
for(const k of ["det","strong","fp","cond","pen","alt"]) console.log(k.padEnd(7),["A1","A2","B","C"].map(m=>p(out[m][k]).padEnd(16)).join(""));
console.log("consistency",p(out.consistency),"alt identical",p(out.altIdentical));
console.log(JSON.stringify(misses,null,1));
