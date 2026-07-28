import puppeteer from 'puppeteer-core';

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true
  });
  console.log('Browser launched.');
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => {
    console.log('PAGE ERROR MESSAGE:', error.message);
    console.log('PAGE ERROR STACK:', error.stack);
  });
  page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure()?.errorText));

  console.log('Navigating to http://localhost:3005...');
  try {
    await page.goto('http://localhost:3005', { waitUntil: 'networkidle2', timeout: 10000 });
  } catch (err) {
    console.log('Goto error:', err.message);
  }
  
  console.log('Wait 2s for any late errors...');
  await new Promise(r => setTimeout(r, 2000));
  
  console.log('Page HTML snippet:');
  const html = await page.content();
  console.log(html.substring(0, 300) + '...');
  
  await browser.close();
})();
