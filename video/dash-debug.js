const { chromium } = require('playwright-core');
const cp = require('child_process');
const SS = '/tmp/claude-0/-home-user-voice-agent-backend/2ab1fad2-5e49-5e01-b398-8548f0158071/scratchpad/';
(async () => {
  const exe = cp.execSync("find /opt/pw-browsers -name chrome -type f | head -1").toString().trim();
  const b = await chromium.launch({ executablePath: exe, args:['--no-sandbox','--force-color-profile=srgb','--hide-scrollbars'] });
  const p = await b.newPage({ viewport:{width:1920,height:1080}, deviceScaleFactor:1 });
  const log=(...a)=>console.log(...a);
  await p.goto('http://localhost:8202/', {waitUntil:'networkidle'});
  await p.addStyleTag({content:'body{zoom:1.5}'});
  await p.waitForTimeout(1000);
  await p.screenshot({path:SS+'d1-overview.png'});
  // menu button = first button with an svg in the sticky top bar
  const menu = p.locator('button:has(svg)').first();
  log('menu visible?', await menu.isVisible());
  await menu.click(); await p.waitForTimeout(700);
  await p.screenshot({path:SS+'d2-drawer.png'});
  // click Conversations in drawer
  const conv = p.getByText('Conversations', {exact:true});
  log('conversations count', await conv.count());
  await conv.first().click(); await p.waitForTimeout(900);
  await p.screenshot({path:SS+'d3-convos.png'});
  await b.close();
})();
