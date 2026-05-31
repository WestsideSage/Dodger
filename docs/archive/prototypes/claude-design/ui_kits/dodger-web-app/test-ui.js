const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error') console.error('PAGE ERROR LOG:', msg.text());
    else console.log('PAGE LOG:', msg.text());
  });
  page.on('pageerror', error => console.error('PAGE UNCAUGHT ERROR:', error.message));

  const url = 'http://localhost:8080/index.html';
  console.log('Navigating to', url);
  await page.goto(url, { waitUntil: 'networkidle0' });

  // Click tabs
  const tabs = ['roster', 'dynasty', 'standings', 'post-match'];
  for (const tab of tabs) {
    console.log('Clicking', tab);
    await page.evaluate((tabId) => {
      // Find the button inside left-nav
      const buttons = Array.from(document.querySelectorAll('.nav-item'));
      const btn = buttons.find(b => b.textContent.toLowerCase().includes(tabId));
      if (btn) btn.click();
      else console.error('BUTTON NOT FOUND:', tabId);
    }, tab);
    await new Promise(r => setTimeout(r, 500)); // Wait a bit for React to render
  }

  await browser.close();
  process.exit(0);
})();
