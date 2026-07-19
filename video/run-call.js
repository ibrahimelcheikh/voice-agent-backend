const { record } = require('./lib/record');
(async () => {
  await record(__dirname + '/clips-raw/04-call.webm', async (page) => {
    await page.goto('http://localhost:8200/scenes/call.html', { waitUntil: 'load' });
    await page.waitForTimeout(33500);
  });
  console.log('call recorded');
})();
