const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');

async function test() {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  const screenshotsDir = path.resolve('../docs/verification/phase-08');
  fs.mkdirSync(screenshotsDir, { recursive: true });
  
  try {
    await page.goto('http://localhost:5174/', { waitUntil: 'networkidle', timeout: 30000 });
    console.log('SUCCESS: page loaded');
    const title = await page.title();
    console.log('Title:', title);
    
    // Fill form
    await page.fill('input[name="origin"]', 'Chicago, IL');
    await page.fill('input[name="destination"]', 'Denver, CO');
    await page.fill('input[name="departureLocal"]', '2026-10-25T08:00');
    await page.fill('input[name="loadWeightLb"]', '34000');
    
    // Submit
    await page.click('button:has-text("Find route options")');
    
    // Wait for results
    await page.waitForSelector('text=Live route options', { timeout: 60000 });
    
    // Wait for map to render
    await page.waitForTimeout(5000);
    
    // Take full page screenshot
    await page.screenshot({ path: path.join(screenshotsDir, 'phase8-full-page.png'), fullPage: true });
    console.log('Full page screenshot saved');
    
    // Check for map container
    const mapExists = await page.locator('.maplibregl-map').count();
    console.log('Map container found:', mapExists > 0);
    
    // Check for route lines
    const routeLines = await page.locator('.maplibregl-layer').count();
    console.log('Map layers found:', routeLines);
    
    // Take map viewport screenshot
    await page.screenshot({ path: path.join(screenshotsDir, 'phase8-map-viewport.png') });
    console.log('Map viewport screenshot saved');
    
    // Check for route cards
    const routeCards = await page.locator('article').count();
    console.log('Route cards found:', routeCards);
    
    // Check for recommendation section
    const recommendationSection = await page.locator('text=Route recommendation').count();
    console.log('Recommendation section found:', recommendationSection > 0);
    
    // Check for map legend
    const legend = await page.locator('text=Route Risk Legend').count();
    console.log('Map legend found:', legend > 0);
    
  } catch (e) {
    console.log('ERROR:', e.message);
    console.log(e.stack);
  }
  await browser.close();
}
test();