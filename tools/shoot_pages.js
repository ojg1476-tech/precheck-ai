// eval/page_test/pages/*.html → 같은 이름 .png (세로로 긴 한 장)
const {chromium}=require("playwright");const fs=require("fs"),path=require("path");
(async()=>{const dir=path.join(__dirname,"..","eval","page_test","pages");const b=await chromium.launch();
for(const f of fs.readdirSync(dir).filter(f=>f.endsWith(".html"))){const p=await b.newPage({viewport:{width:860,height:1000}});
 await p.goto("file://"+path.join(dir,f));await p.waitForTimeout(300);
 await p.screenshot({path:path.join(dir,f.replace(".html",".png")),fullPage:true});
 console.log(f, await p.evaluate(()=>document.body.scrollHeight));await p.close();}
await b.close();})();
