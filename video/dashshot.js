const { chromium } = require('playwright-core');
const cp = require('child_process');
(async () => {
  const exe = cp.execSync("find /opt/pw-browsers -name chrome -type f | head -1").toString().trim();
  const b = await chromium.launch({ executablePath: exe, args:['--no-sandbox'] });
  const p = await b.newPage({ viewport:{width:1920,height:1080}, deviceScaleFactor:1 });
  const errs=[]; p.on('pageerror',e=>errs.push(e.message.slice(0,140)));
  await p.goto('http://localhost:8202/', {waitUntil:'networkidle'});
  await p.waitForTimeout(1500);
  await p.screenshot({path:'/tmp/claude-0/-home-user-voice-agent-backend/2ab1fad2-5e49-5e01-b398-8548f0158071/scratchpad/dash0.png'});
  console.log('errors', JSON.stringify(errs.slice(0,4)));
  await b.close();
})();
