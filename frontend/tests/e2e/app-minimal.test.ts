import { Browser, Page } from 'puppeteer';
import { launchBrowser, createPage, TEST_CONFIG } from '../setup';

describe('Location Tracker - Minimal Test', () => {
  let browser: Browser;
  let page: Page;

  beforeAll(async () => {
    browser = await launchBrowser();
  });

  afterAll(async () => {
    await browser.close();
  });

  beforeEach(async () => {
    page = await createPage(browser);
    await page.goto(TEST_CONFIG.baseUrl);
    await page.waitForSelector('body');
  });

  afterEach(async () => {
    await page.close();
  });

  test('should load the application', async () => {
    const title = await page.title();
    expect(title).toBeDefined();
    
    const bodyText = await page.$eval('body', el => el.textContent);
    expect(bodyText).toBeDefined();
    expect(bodyText!.length).toBeGreaterThan(0);
  });

  test('should have navigation buttons', async () => {
    const buttonTexts = await page.$$eval('button', buttons => 
      buttons.map(btn => btn.textContent?.trim()).filter(Boolean)
    );
    
    expect(buttonTexts.length).toBeGreaterThan(0);
    expect(buttonTexts).toEqual(
      expect.arrayContaining(['📋 My Trips', '🔴 Live Tracking'])
    );
    
    console.log('Navigation buttons found:', buttonTexts);
  });

  test('should switch tabs successfully', async () => {
    // Click Live Tracking
    const liveTrackingClicked = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const liveBtn = buttons.find(btn => btn.textContent?.includes('Live Tracking'));
      if (liveBtn) {
        (liveBtn as HTMLButtonElement).click();
        return true;
      }
      return false;
    });
    
    expect(liveTrackingClicked).toBe(true);
    
    // Wait for any state changes
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Click back to My Trips
    const tripsClicked = await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const tripsBtn = buttons.find(btn => btn.textContent?.includes('My Trips'));
      if (tripsBtn) {
        (tripsBtn as HTMLButtonElement).click();
        return true;
      }
      return false;
    });
    
    expect(tripsClicked).toBe(true);
  });

  test('should have working dropdown selector', async () => {
    const selectElements = await page.$$('select');
    expect(selectElements.length).toBeGreaterThan(0);
    
    const selectInfo = await page.$eval('select', select => ({
      optionCount: select.options.length,
      selectedIndex: select.selectedIndex,
      hasOptions: select.options.length > 0
    }));
    
    expect(selectInfo.hasOptions).toBe(true);
    console.log('Select element info:', selectInfo);
  });

  test('should be responsive', async () => {
    // Test mobile
    await page.setViewport({ width: 375, height: 667 });
    await page.reload();
    await page.waitForSelector('body');
    
    const mobileButtons = await page.$$('button');
    expect(mobileButtons.length).toBeGreaterThan(0);
    
    // Test desktop
    await page.setViewport({ width: 1280, height: 720 });
    await page.reload();
    await page.waitForSelector('body');
    
    const desktopButtons = await page.$$('button');
    expect(desktopButtons.length).toBeGreaterThan(0);
  });

  test('should take basic screenshots', async () => {
    await page.screenshot({ 
      path: 'tests/screenshots/app-main.png' as `${string}.png`,
      fullPage: true 
    });
    
    // Switch to live tracking and screenshot
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const liveBtn = buttons.find(btn => btn.textContent?.includes('Live Tracking'));
      if (liveBtn) (liveBtn as HTMLButtonElement).click();
    });
    
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    await page.screenshot({ 
      path: 'tests/screenshots/live-tracking.png' as `${string}.png`,
      fullPage: true 
    });
    
    // Screenshots taken successfully if we reach here
    expect(true).toBe(true);
  });
});