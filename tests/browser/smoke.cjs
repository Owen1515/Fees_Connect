/* Run against an already-started local Django server; screenshots are review evidence. */
const { chromium } = require('playwright');
const fs = require('node:fs');
(async () => {
  const browser = await chromium.launch({headless: true});
  const errors = [];
  fs.mkdirSync('artifacts/browser', {recursive: true});
  for (const width of [390, 1440]) {
    const page = await browser.newPage({viewport: {width, height: 1000}});
    page.on('pageerror', error => errors.push(error.message));
    for (const [name, path] of [['home','/'], ['login','/accounts/login/'], ['register','/accounts/register/'], ['demo','/demo/']]) {
      const response = await page.goto((process.env.TEST_BASE_URL || 'http://127.0.0.1:8000') + path);
      if (response.status() !== 200) errors.push(`${path}: ${response.status()}`);
      await page.screenshot({path: `artifacts/browser/${name}-${width}.png`, fullPage: true});
      if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)) errors.push(`${path}: horizontal overflow at ${width}`);
    }
    await page.close();
  }
  await browser.close();
  if (errors.length) throw new Error(errors.join('\n'));
  console.log('Public pages rendered without console errors or horizontal overflow; inspect the screenshots.');
})().catch(error => { console.error(error.message); process.exitCode = 1; });
