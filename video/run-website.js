const { record, smoothScrollTo } = require('./lib/record');

async function topOf(page, sel, offset = 90) {
  return await page.evaluate(({ sel, offset }) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return Math.max(0, r.top + window.scrollY - offset);
  }, { sel, offset });
}

(async () => {
  await record(__dirname + '/clips-raw/02-website.webm', async (page) => {
    // Abort render-blocking external fonts so the page paints instantly (offline).
    await page.route('**/*', (route) => {
      const u = route.request().url();
      if (u.includes('fonts.googleapis.com') || u.includes('fonts.gstatic.com')) return route.abort();
      return route.continue();
    });
    await page.goto('http://localhost:8201/index.html', { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(900);

    // Hero — let the Arabic/English chat animation play.
    await page.waitForTimeout(4200);

    const stops = [
      ['#features', 90, 2600],
      ['.show', 70, 2600],          // dark dashboard showcase
      ['.prob-grid', 150, 3400],    // missed-call stats (counters animate)
      ['.steps', 150, 2000],        // setup steps
      ['#pricing', 90, 2800],       // pricing
      ['#faq', 90, 1000],           // FAQ (then open one)
    ];
    for (const [sel, off, pause] of stops) {
      const y = await topOf(page, sel, off);
      if (y == null) { console.log('MISSING selector', sel); continue; }
      await smoothScrollTo(page, y, 1400, 46);
      await page.waitForTimeout(pause);
    }

    // Open the first FAQ item.
    const faqBtn = await page.$('.qa button');
    if (faqBtn) {
      const box = await faqBtn.boundingBox();
      if (box) { await page.mouse.move(box.x + 30, box.y + box.height / 2, { steps: 12 }); }
      await faqBtn.click();
      await page.waitForTimeout(2600);
    }

    // CTA finish.
    const cy = await topOf(page, '#cta', 90);
    if (cy != null) { await smoothScrollTo(page, cy, 1400, 46); await page.waitForTimeout(2800); }
  });
  console.log('website recorded');
})();
