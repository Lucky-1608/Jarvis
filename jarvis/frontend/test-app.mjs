import { chromium } from 'playwright';

(async () => {
  console.log('Starting Playwright...');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`BROWSER ERROR: ${msg.text()}`);
    } else {
      console.log(`BROWSER LOG: ${msg.text()}`);
    }
  });

  page.on('pageerror', error => {
    console.log(`PAGE ERROR: ${error.message}`);
  });

  console.log('Navigating to http://localhost:5173...');
  try {
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    console.log('Page loaded successfully.');
    
    const errorText = await page.evaluate(() => document.body.innerText);
    if (errorText.includes('React Crashed')) {
      console.log('React Crashed!');
      console.log(errorText.substring(0, 500));
    } else {
      console.log('No React crash detected on Home page.');
    }
    
    console.log('Clicking on Memory page link...');
    await page.click('text="Memory"');
    await page.waitForTimeout(1000);
    
    const memoryText = await page.evaluate(() => document.body.innerText);
    if (memoryText.includes('React Crashed')) {
      console.log('React Crashed on Memory page!');
    } else {
      console.log('Memory page loaded. Current URL:', page.url());
    }

  } catch (err) {
    console.log('Navigation failed:', err.message);
  } finally {
    await browser.close();
  }
})();
