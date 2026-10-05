// Node >=22, Chrome. No npm dependencies. Artifacts go to /tmp.
const {spawn}=require('node:child_process');
const fs=require('node:fs/promises');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const assert=require('node:assert/strict');
const pageUrl=pathToFileURL(path.join(__dirname,'index.html')).href;
const chrome=spawn(process.env.CHROME_BIN||'google-chrome',['--headless','--no-sandbox','--disable-gpu','--no-first-run','--remote-debugging-port=9237','--user-data-dir=/tmp/fpm-v2-browser','about:blank'],{stdio:'ignore'});
let ws,next=1;const pending=new Map(),errors=[];
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function call(method,params={}){return new Promise((resolve,reject)=>{const id=next++;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}))})}
async function run(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value}
async function click(action){await run(`document.querySelector('[data-action="${action}"]').click()`)}
async function screenshot(name){await sleep(80);const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});await fs.writeFile('/tmp/fpm-v2-'+name+'.png',Buffer.from(shot.data,'base64'))}
(async()=>{
 let tabs;for(let i=0;i<100;i++){try{tabs=await(await fetch('http://127.0.0.1:9237/json')).json();break}catch{await sleep(100)}}if(!tabs)throw Error('Chrome unavailable');
 ws=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r));ws.addEventListener('message',e=>{const m=JSON.parse(e.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params)});
 await call('Runtime.enable');await call('Page.enable');await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});await call('Page.navigate',{url:pageUrl});
 let loaded=false;for(let i=0;i<150;i++){if(await run("document.readyState==='complete' && document.querySelectorAll('#dots button').length===14")){loaded=true;break}await sleep(100)}if(!loaded)console.log(await run("({url:location.href,ready:document.readyState,title:document.title,dots:document.querySelectorAll('#dots button').length})"),JSON.stringify(errors));assert.ok(loaded,'page ready');
 await sleep(1200);assert.equal(await run('scene'),0,'no auto advance');assert.equal(await run("$('math').open"),false);
 for(const sample of ['amplitud','fase','mixta']){await click('sample:'+sample);assert.equal(await run("document.querySelector('#visualL img').src===D.samples[sampleName].truth.amp"),true)}
 for(let i=0;i<14;i++){
  await run(`navigate(${i})`);assert.equal(await run('scene'),i);assert.equal(await run("$('math').open"),false);assert.equal(await run("$('helpL').open"),false);
  assert.ok((await run("$('title').textContent")).length>5);assert.equal(await run('document.documentElement.scrollWidth<=window.innerWidth'),true,`desktop overflow ${i}`);
  if(i===1){for(let p=0;p<4;p++){await click('pattern:'+p);assert.equal(await run('pattern'),p)}await screenshot('frequencies')}
  if(i===2){await run("$('aperture').value='2';$('aperture').dispatchEvent(new Event('input',{bubbles:true}))");assert.equal(await run("document.querySelector('#visualR img').src===D.gratings[1].captures[2]"),true)}
  if(i===3){await click('angle:1');assert.equal(await run("document.querySelector('#visualR img').src===D.angleImages[1]"),true);await screenshot('angle')}
  if(i===4){assert.equal(await run("document.querySelectorAll('[data-led]').length"),49);await click('led:'+await run('D.selected[2]'));assert.equal(await run("$('labelR').textContent"),'Campo oscuro');await click('enhance');assert.equal(await run("document.querySelector('#visualR img').src===D.samples[sampleName].enhanced[led]"),true);await screenshot('capture')}
  if(i===5){await click('overlap:1');assert.equal(await run('D.overlap[1].fraction'),0);await click('overlap:0');assert.ok(await run('D.overlap[0].fraction>0'));await screenshot('overlap')}
  if(i===6){await click('phase:1');assert.equal(await run("[...document.querySelectorAll('#visualR img')].every((im,j)=>im.src===D.samples.fase.phaseOn[j])"),true)}
  if(i===8){
   assert.equal(await run("document.querySelector('[data-action=compare]').disabled"),true);
   for(const j of [0,1,2]){
    await click('correctionLed:'+j);assert.equal(await run('predicted'),false);
    await run("document.querySelector('[data-action=simulate]').focus()");await click('simulate');
    assert.equal(await run("document.querySelector('#visualR img').src===D.samples[sampleName].corrections[correctionLed].comparisons[correctionLed].before"),true);
    assert.equal(await run("document.activeElement.dataset.action"),'simulate');
   }
   await screenshot('prediction');await click('compare');
   assert.equal(await run("document.querySelectorAll('#visualL img,#visualR img').length"),6);
   await screenshot('comparison');
  }
  if(i===9){await click('correctionLed:2');assert.equal(await run('correctionLed'),2)}
  if(i===10){
   assert.equal(await run("document.querySelector('[data-action=correction]').disabled"),true);
   await click('returnCorrection');
   assert.equal(await run("document.querySelectorAll('#visualL img').length"),2);
   await click('correction');assert.equal(await run("document.querySelector('#visualR img').src===D.samples[sampleName].corrections[correctionLed].spectrumAfter"),true);assert.equal(await run("document.querySelectorAll('.pulse-dot').length"),22);await screenshot('correction');await click('returnCorrection');assert.equal(await run('correctionOn'),false);assert.equal(await run("document.querySelector('[data-action=correction]').disabled"),true)}
  if(i===11){await click('consequences');assert.equal(await run("[...document.querySelectorAll('#visualR img')].every((im,j)=>im.src===D.samples[sampleName].corrections[correctionLed].comparisons[j].after)"),true);assert.equal(await run("document.querySelectorAll('.score-row>div').length"),3);await screenshot('shared-correction')}
  if(i===12){await click('object');assert.equal(await run("document.querySelector('#visualR img').src===D.samples[sampleName].corrections[correctionLed].after.amp"),true)}
  assert.equal(await run("!!$('loss')"),i===13,'loss chart only at end');
 }
 await run("document.querySelector('[data-action=run]').focus()");await click('run');await sleep(1100);assert.equal(await run("document.activeElement.dataset.action"),'run');assert.equal(await run('playing'),true);await click('run');assert.equal(await run('playing'),false);
 await run("$('iteration').value='15';$('iteration').dispatchEvent(new Event('input',{bubbles:true}))");assert.equal(await run("document.querySelector('#visualL img').src===D.samples[sampleName].recon[15].amp"),true);
 await run('iteration=29;cycle=2;render()');await click('run');await sleep(1100);assert.equal(await run('iteration'),30);assert.equal(await run('playing'),false);await screenshot('convergence');
 await run("$('math').open=true;navigate(0)");assert.equal(await run("$('math').open"),false);

 // Capture sweep: actual visited windows, same LED for image and pupil, pause and stop.
 await run('navigate(4)');await click('resetSweep');
 assert.equal(await run('visited.size'),1);
 await run(`document.querySelector('[data-led="1"]').focus();document.querySelector('[data-led="1"]').click()`);
 assert.equal(await run('visited.size'),2);assert.equal(await run("document.activeElement.dataset.led"),'1');
 await click('resetSweep');await click('sweep');await sleep(1000);
 assert.equal(await run('led'),1);await click('sweep');const pausedLed=await run('led');await sleep(1000);assert.equal(await run('led'),pausedLed);
 await click('resetSweep');await click('sweep');
 await run("(async()=>{for(let i=0;i<60&&sweepPlaying;i++){sweepLast=performance.now()-1000;await new Promise(r=>setTimeout(r,35))}})()");
 assert.equal(await run('led'),48);assert.equal(await run('visited.size'),49);assert.equal(await run('sweepPlaying'),false);
 assert.equal(await run("document.querySelector('#visualR img').src===(enhance?D.samples[sampleName].enhanced:D.samples[sampleName].captures)[led]"),true);
 assert.equal(await run("(()=>{const c=document.querySelector('#visualR .spectrum svg circle:last-of-type');return +c.getAttribute('cx')===64-D.leds[led][0]*10 && +c.getAttribute('cy')===64-D.leds[led][1]*10})()"),true);
 await screenshot('coverage');await click('sweep');assert.equal(await run('led'),0);assert.equal(await run('visited.size'),1);
 await run('navigate(5)');assert.equal(await run('sweepPlaying'),false);
 // Isolated example must not change the selected sample.
 await run('navigate(0)');await click('sample:amplitud');await run('navigate(6)');await click('phase:1');assert.equal(await run('sampleName'),'amplitud');
 for(const sample of ['amplitud','fase','mixta']){
  await run('navigate(0)');await click('sample:'+sample);await run('navigate(8)');
  assert.equal(await run('predicted'),false);await click('simulate');
  assert.equal(await run("document.querySelector('#visualR img').src===D.samples[sampleName].corrections[correctionLed].comparisons[correctionLed].before"),true);
  await run('navigate(13)');await click('truth');
  for(const it of [0,15,30]){
   await run(`$('iteration').focus();$('iteration').value='${it}';$('iteration').dispatchEvent(new Event('input',{bubbles:true}))`);
   assert.equal(await run("document.activeElement.id"),'iteration');
   assert.equal(await run(`(()=>{const images=[...document.querySelectorAll('#visualL img')];return images.length===4 && images[0].src===D.samples[sampleName].recon[${it}].amp && images[1].src===D.samples[sampleName].recon[${it}].phase && images[2].src===D.samples[sampleName].truth.amp && images[3].src===D.samples[sampleName].truth.phase})()`),true);
  }
  assert.equal(await run("document.querySelector('[data-action=run]').textContent"),'↺ Repetir');
 }
 await screenshot('truth-comparison');
 await click('run');await click('truth');assert.equal(await run('playing'),true,'comparison does not pause playback');await click('run');
 // Mobile screens and in-screen stages, then real Next navigation from the bottom.
 for(const width of [390,320]){
  await call('Emulation.setDeviceMetricsOverride',{width,height:844,deviceScaleFactor:1,mobile:true});
  for(let i=0;i<14;i++){
   await run(`navigate(${i})`);assert.equal(await run('document.documentElement.scrollWidth<=innerWidth'),true,`mobile overflow ${width} screen ${i}`);
   assert.equal(await run("$('title').getBoundingClientRect().top>=0 && $('title').getBoundingClientRect().bottom<innerHeight"),true,'heading visible');
  }
  await run('navigate(8)');if(await run('comparing'))await click('predictionBack');await click('simulate');await screenshot('mobile-prediction-'+width);await click('compare');
  assert.equal(await run('document.documentElement.scrollWidth<=innerWidth'),true);
  await run('navigate(10)');await click('returnCorrection');await click('correction');
  assert.equal(await run('document.documentElement.scrollWidth<=innerWidth'),true);await screenshot('mobile-correction-'+width);
  await run('navigate(4)');assert.ok(await run("document.querySelector('[data-led]').getBoundingClientRect().width>=30"));await screenshot('mobile-capture-'+width);
  await run('navigate(13);compareTruth=true;render()');assert.equal(await run('document.documentElement.scrollWidth<=innerWidth'),true);await screenshot('mobile-truth-'+width);
  await run('navigate(8);window.scrollTo(0,document.documentElement.scrollHeight)');await run("$('next').click()");
  assert.equal(await run('scene'),9);assert.equal(await run("$('title').getBoundingClientRect().top>=0"),true,'Next scrolls to heading');
 }
 await call('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
 await run('navigate(8)');if(await run('comparing'))await click('predictionBack');await click('simulate');assert.equal(await run("document.querySelectorAll('animateMotion').length"),0);
 assert.equal(errors.length,0,JSON.stringify(errors));console.log('PASS: numerical image mappings; guided prediction and two-stage correction; 49-LED coverage/pause/end; 3 samples and truth at 0/15/30; keyboard focus; final replay label; 14 screens at desktop/390/320; mobile scroll; reduced motion; no JS exceptions.');
})().catch(e=>{console.error(e);process.exitCode=1}).finally(()=>{if(ws)ws.close();chrome.kill()});
