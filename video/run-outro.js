const { record } = require('./lib/record');
(async () => {
  await record(__dirname + '/clips-raw/05-outro.webm', async (page) => {
    await page.goto('http://localhost:8200/scenes/outro.html', { waitUntil: 'load' });
    await page.waitForTimeout(6200);
  });
  console.log('outro recorded');
})();
