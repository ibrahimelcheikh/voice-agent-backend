const { record } = require('./lib/record');

const ZOOM = 1.5;

// Injected: zoom the 640px app to fill the frame + a visible click cursor (headless
// Chromium renders no OS cursor). Cursor lives on <body> which is NOT zoomed (#root is),
// so viewport mouse coords map 1:1.
const INJECT = `
#root{zoom:${ZOOM}}
`;
const CURSOR_JS = `
(() => {
  const c = document.createElement('div');
  c.id = '__cur';
  Object.assign(c.style, {position:'fixed',left:'-50px',top:'-50px',width:'26px',height:'26px',
    borderRadius:'50%',border:'2px solid #2E6BFF',background:'rgba(46,107,255,.22)',
    zIndex:2147483647,pointerEvents:'none',transform:'translate(-50%,-50%)',transition:'left .04s linear, top .04s linear'});
  const dot = document.createElement('div');
  Object.assign(dot.style,{position:'absolute',left:'50%',top:'50%',width:'6px',height:'6px',borderRadius:'50%',background:'#1E4FD8',transform:'translate(-50%,-50%)'});
  c.appendChild(dot);
  const attach=()=>{ (document.body||document.documentElement).appendChild(c); };
  attach();
  document.addEventListener('mousemove', e => { c.style.left=e.clientX+'px'; c.style.top=e.clientY+'px'; }, true);
  document.addEventListener('mousedown', e => {
    const r=document.createElement('div');
    Object.assign(r.style,{position:'fixed',left:e.clientX+'px',top:e.clientY+'px',width:'26px',height:'26px',
      borderRadius:'50%',border:'2px solid #2E6BFF',transform:'translate(-50%,-50%) scale(1)',opacity:'.9',
      zIndex:2147483646,pointerEvents:'none',transition:'transform .5s ease, opacity .5s ease'});
    (document.body||document.documentElement).appendChild(r);
    requestAnimationFrame(()=>{ r.style.transform='translate(-50%,-50%) scale(2.4)'; r.style.opacity='0'; });
    setTimeout(()=>r.remove(),520);
  }, true);
})();
`;

async function moveTo(page, loc, hold = 240) {
  await loc.scrollIntoViewIfNeeded().catch(() => {});
  const box = await loc.boundingBox();
  if (!box) throw new Error('no box for locator');
  const cx = box.x + box.width / 2, cy = box.y + Math.min(box.height / 2, 28);
  await page.mouse.move(cx, cy, { steps: 16 });
  await page.waitForTimeout(hold);
}
async function moveClick(page, loc) {
  await moveTo(page, loc);
  await loc.click();
  await page.waitForTimeout(500);
}
async function openNav(page, label) {
  const menu = page.locator('button:has(svg)').first();
  await moveClick(page, menu);              // open drawer
  await page.waitForTimeout(500);
  // Drawer nav items are <button>s; "Services" carries a "New" pill so match by role+regex.
  await moveClick(page, page.getByRole('button', { name: new RegExp(label) }).first());
  await page.waitForTimeout(400);
}

(async () => {
  await record(__dirname + '/clips-raw/03-dashboard.webm', async (page) => {
    await page.goto('http://localhost:8202/', { waitUntil: 'networkidle' });
    await page.addStyleTag({ content: INJECT });
    await page.evaluate(CURSOR_JS);
    await page.mouse.move(960, 300);
    await page.waitForTimeout(700);

    // Overview — pause on KPIs.
    await page.waitForTimeout(2400);

    // Conversations — Botox booking transcript is auto-expanded.
    await openNav(page, 'Conversations');
    await page.waitForTimeout(2800);

    // Services -> Botox detail.
    await openNav(page, 'Services');
    await page.waitForTimeout(900);
    await moveClick(page, page.getByText('Botox', { exact: true }).first());
    await page.waitForTimeout(2800);

    // Reports -> a report with its chart.
    await openNav(page, 'Reports');
    await page.waitForTimeout(800);
    await moveClick(page, page.getByText('Call Volume Trends', { exact: true }).first());
    await page.waitForTimeout(2800);

    // Settings -> General -> scroll to Holiday Hours.
    await openNav(page, 'Settings');
    await page.waitForTimeout(700);
    await page.getByText('Holiday Hours', { exact: true }).first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(2000);

    // Flip to Arabic RTL via the globe toggle (shows "ع" in EN mode).
    await moveClick(page, page.getByText('ع', { exact: true }).first());
    await page.waitForTimeout(3200);
  });
  console.log('dashboard recorded');
})();
