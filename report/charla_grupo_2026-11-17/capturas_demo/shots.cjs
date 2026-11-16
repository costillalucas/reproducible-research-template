const {spawn}=require('node:child_process');const fs=require('node:fs/promises');
const OUT=process.argv[2];const R='/home/chanoscopio/Documents/LucasC/reproducible-research-template/report/';
const chrome=spawn('google-chrome',['--headless','--no-sandbox','--disable-gpu','--no-first-run','--hide-scrollbars','--remote-debugging-port=9241','--user-data-dir=/tmp/claude-1000/-home-chanoscopio-Documents-LucasC-reproducible-research-template/4ed7ebfb-b381-45d4-b897-262a546c8d04/scratchpad/charla40/chrome','about:blank'],{stdio:'ignore'});
let ws,next=1;const pend=new Map();const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const call=(m,p={})=>new Promise((res,rej)=>{const id=next++;pend.set(id,{res,rej});ws.send(JSON.stringify({id,method:m,params:p}))});
async function run(e){const r=await call('Runtime.evaluate',{expression:e,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(e+' :: '+JSON.stringify(r.exceptionDetails.exception?.description||r.exceptionDetails.text));return r.result.value}
async function shot(n){await sleep(500);const s=await call('Page.captureScreenshot',{format:'png'});await fs.writeFile(OUT+'/'+n+'.png',Buffer.from(s.data,'base64'));console.log('saved',n)}
async function load(u){await call('Page.navigate',{url:'file://'+R+u});for(let i=0;i<100;i++){if(await run("document.readyState==='complete'"))break;await sleep(100)}await sleep(1000)}
const click=a=>run(`document.querySelector('[data-action="${a}"]').click()`);
(async()=>{let t;for(let i=0;i<100;i++){try{t=await(await fetch('http://127.0.0.1:9241/json')).json();break}catch{await sleep(100)}}
ws=new WebSocket(t.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r));
ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id&&pend.has(m.id)){const p=pend.get(m.id);pend.delete(m.id);m.error?p.rej(Error(JSON.stringify(m.error))):p.res(m.result)}});
await call('Runtime.enable');await call('Page.enable');await call('Emulation.setDeviceMetricsOverride',{width:1600,height:900,deviceScaleFactor:1,mobile:false});
const steps=JSON.parse(process.argv[3]);
for(const [page,list] of Object.entries(steps)){await load(page);for(const [name,js] of list){try{await run(js);await shot(name)}catch(e){console.log('FAIL',name,e.message.slice(0,300))}}}
chrome.kill();process.exit(0)})().catch(e=>{console.log(e);chrome.kill();process.exit(1)});
