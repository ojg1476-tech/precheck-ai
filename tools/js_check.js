// 웹 버전과 똑같은 로직(runRules+dedupe)으로 검사 → JSON 출력. 사용: node js_check.js <type> < text
const fs=require("fs"),path=require("path");
let type=process.argv[2];
const src=fs.readFileSync(path.join(__dirname,"rules_web.js"),"utf8");
const {RULES,deobf}=new Function("type",src+";return {RULES,deobf};")(type);
const ORDER={red:0,amber:1,blue:2};
const text=fs.readFileSync(0,"utf8");
const run=t=>{const o=[];for(const r of RULES){if(!r.for.includes(type))continue;r.re.lastIndex=0;let m;
 while((m=r.re.exec(t))){if(!m[0].trim()){r.re.lastIndex++;continue;}const lead=m[0].length-m[0].trimStart().length;o.push({start:m.index+lead,end:m.index+m[0].length,grade:r.g});}}return o;};
const out=run(text);const d=deobf(text);const base=out.slice();
if(d.t!==text)for(const f of run(d.t)){const st=d.s[f.start],en=d.e[f.end-1];if(base.some(g=>g.start<en&&st<g.end))continue;out.push({start:st,end:en,grade:f.grade});}
out.sort((a,b)=>a.start-b.start||ORDER[a.grade]-ORDER[b.grade]||(b.end-b.start)-(a.end-a.start));
const res=[];for(const f of out){const l=res[res.length-1];if(l&&f.start<l.end){if(ORDER[f.grade]<ORDER[l.grade])res[res.length-1]=f;continue;}res.push(f);}
console.log(JSON.stringify(res));
