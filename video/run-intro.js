const { record } = require('./lib/record');
(async () => {
  await record(__dirname + '/clips-raw/01-intro.webm', async (page) => {
    await page.goto('http://localhost:8200/scenes/intro.html', { waitUntil: 'load' });
    await page.waitForTimeout(6200);
  });
  console.log('intro recorded');
})();
