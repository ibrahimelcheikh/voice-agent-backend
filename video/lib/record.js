// Reusable 1920x1080 Playwright recorder. Records the page for the duration your
// driver() takes, saves a webm to clips-raw/, then this module returns its path.
const { chromium } = require('playwright-core');
const fs = require('fs');
const cp = require('child_process');

const CHROME = cp.execSync("find /opt/pw-browsers -name chrome -type f | head -1").toString().trim();

async function record(outWebm, driver) {
  const rawDir = '/home/user/voice-agent-backend/video/clips-raw';
  fs.mkdirSync(rawDir, { recursive: true });
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-gpu', '--use-gl=swiftshader', '--enable-unsafe-swiftshader',
           '--enable-features=Vulkan', '--force-color-profile=srgb', '--hide-scrollbars',
           '--autoplay-policy=no-user-gesture-required'],
  });
  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
    recordVideo: { dir: rawDir, size: { width: 1920, height: 1080 } },
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERR: ' + e.message));
  try {
    await driver(page);
  } catch (e) {
    console.error('DRIVER ERROR:', e.message);
    try { await page.screenshot({ path: outWebm.replace(/\.webm$/, '-ERROR.png') }); } catch (_) {}
    await ctx.close();
    await browser.close();
    throw e;
  }
  const vpath = await page.video().path();
  await ctx.close();          // finalizes the webm
  fs.copyFileSync(vpath, outWebm);
  await browser.close();
  if (errors.length) console.log('  page errors:', JSON.stringify(errors.slice(0, 4)));
  return outWebm;
}

// Smooth incremental scroll helper (never jump-cuts).
async function smoothScrollTo(page, targetY, ms = 1200, steps = 40) {
  const startY = await page.evaluate(() => window.scrollY);
  for (let i = 1; i <= steps; i++) {
    const t = i / steps;
    const eased = 0.5 - 0.5 * Math.cos(Math.PI * t); // easeInOut
    const y = startY + (targetY - startY) * eased;
    await page.evaluate(v => window.scrollTo(0, v), y);
    await page.waitForTimeout(ms / steps);
  }
}

module.exports = { record, smoothScrollTo };
