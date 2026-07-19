const { chromium } = require('playwright-core');
const cp = require('child_process');
const SS='/tmp/claude-0/-home-user-voice-agent-backend/2ab1fad2-5e49-5e01-b398-8548f0158071/scratchpad/';
(async () => {
  const exe = cp.execSync("find /opt/pw-browsers -name chrome -type f | head -1").toString().trim();
  const b = await chromium.launch({ executablePath: exe, args:['--no-sandbox','--force-color-profile=srgb','--hide-scrollbars'] });
  const p = await b.newPage({ viewport:{width:1920,height:1080}, deviceScaleFactor:1 });
  const errs=[]; p.on('pageerror',e=>errs.push(e.message.slice(0,120)));
  await p.goto('http://localhost:8200/scenes/call.html', {waitUntil:'load'});
  const shots=[2000,5300,13500,19500,26500,31000];
  let last=0;
  for(const t of shots){ await p.waitForTimeout(t-last); last=t; await p.screenshot({path:SS+'call_'+t+'.png'}); }
  console.log('errors', JSON.stringify(errs.slice(0,4)));
  await b.close();
})();
