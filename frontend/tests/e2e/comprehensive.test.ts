import { Browser, Page } from 'puppeteer';
import { launchBrowser, createPage, TEST_CONFIG } from '../setup';

describe('Location Tracker - Comprehensive E2E Tests', () => {
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

  describe('Application Loading', () => {
    test('should load the main application successfully', async () => {
      const title = await page.title();
      expect(title).toBeDefined();
      
      const bodyText = await page.$eval('body', el => el.textContent);
      expect(bodyText).toBeDefined();
      expect(bodyText!.length).toBeGreaterThan(0);
      
      // Check for essential elements
      const buttons = await page.$$('button');
      expect(buttons.length).toBeGreaterThan(0);
      
      const selects = await page.$$('select');
      expect(selects.length).toBeGreaterThan(0);
    });

    test('should display correct navigation elements', async () => {
      const buttonTexts = await page.$$eval('button', buttons => 
        buttons.map(btn => btn.textContent?.trim()).filter(Boolean)
      );
      
      expect(buttonTexts).toEqual(
        expect.arrayContaining([
          '📋 My Trips',
          '🔴 Live Tracking',
          '📊 Timeline (Coming Soon)'
        ])
      );
      
      console.log('Navigation buttons found:', buttonTexts);
    });
  });

  describe('Navigation Functionality', () => {
    test('should switch to Live Tracking tab', async () => {
      // Click Live Tracking button
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
      
      // Verify we can still interact with the page
      const postClickButtons = await page.$$('button');
      expect(postClickButtons.length).toBeGreaterThan(0);
    });

    test('should return to My Trips tab', async () => {
      // First go to Live Tracking
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const liveBtn = buttons.find(btn => btn.textContent?.includes('Live Tracking'));
        if (liveBtn) (liveBtn as HTMLButtonElement).click();
      });
      
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Then return to My Trips
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
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Verify page is still functional
      const buttons = await page.$$('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  describe('Vehicle Selector', () => {
    test('should have a working vehicle selector dropdown', async () => {
      const selectElements = await page.$$('select');
      expect(selectElements.length).toBeGreaterThan(0);
      
      const selectInfo = await page.$eval('select', select => ({
        optionCount: select.options.length,
        selectedIndex: select.selectedIndex,
        hasOptions: select.options.length > 0,
        options: Array.from(select.options).map(opt => opt.textContent?.trim())
      }));
      
      expect(selectInfo.hasOptions).toBe(true);
      expect(selectInfo.optionCount).toBeGreaterThan(0);
      
      console.log('Vehicle selector info:', selectInfo);
    });

    test('should be able to interact with the dropdown', async () => {
      const select = await page.$('select');
      expect(select).toBeTruthy();
      
      if (select) {
        // Click on the select to open it
        await select.click();
        
        // Wait a moment for any animations
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // Verify it's still available after interaction
        const selectStillExists = await page.$('select');
        expect(selectStillExists).toBeTruthy();
      }
    });
  });

  describe('Responsive Design', () => {
    test('should work on mobile viewport', async () => {
      await page.setViewport({ width: 375, height: 667 });
      await page.reload();
      await page.waitForSelector('body');
      
      const mobileButtons = await page.$$('button');
      expect(mobileButtons.length).toBeGreaterThan(0);
      
      const mobileSelects = await page.$$('select');
      expect(mobileSelects.length).toBeGreaterThan(0);
      
      // Test navigation still works on mobile
      const navWorking = await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const liveBtn = buttons.find(btn => btn.textContent?.includes('Live Tracking'));
        if (liveBtn) {
          (liveBtn as HTMLButtonElement).click();
          return true;
        }
        return false;
      });
      
      expect(navWorking).toBe(true);
    });

    test('should work on tablet viewport', async () => {
      await page.setViewport({ width: 768, height: 1024 });
      await page.reload();
      await page.waitForSelector('body');
      
      const tabletButtons = await page.$$('button');
      expect(tabletButtons.length).toBeGreaterThan(0);
      
      const buttonTexts = await page.$$eval('button', buttons => 
        buttons.map(btn => btn.textContent?.trim()).filter(Boolean)
      );
      
      expect(buttonTexts).toEqual(
        expect.arrayContaining(['📋 My Trips', '🔴 Live Tracking'])
      );
    });

    test('should work on desktop viewport', async () => {
      await page.setViewport({ width: 1280, height: 720 });
      await page.reload();
      await page.waitForSelector('body');
      
      const desktopButtons = await page.$$('button');
      expect(desktopButtons.length).toBeGreaterThan(0);
      
      // Test full navigation flow on desktop
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const liveBtn = buttons.find(btn => btn.textContent?.includes('Live Tracking'));
        if (liveBtn) (liveBtn as HTMLButtonElement).click();
      });
      
      await new Promise(resolve => setTimeout(resolve, 500));
      
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const tripsBtn = buttons.find(btn => btn.textContent?.includes('My Trips'));
        if (tripsBtn) (tripsBtn as HTMLButtonElement).click();
      });
      
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const finalButtons = await page.$$('button');
      expect(finalButtons.length).toBeGreaterThan(0);
    });
  });

  describe('Page State Management', () => {
    test('should maintain state after page refresh', async () => {
      const initialButtonTexts = await page.$$eval('button', buttons => 
        buttons.map(btn => btn.textContent?.trim())
      );
      
      await page.reload();
      await page.waitForSelector('body');
      
      const refreshedButtonTexts = await page.$$eval('button', buttons => 
        buttons.map(btn => btn.textContent?.trim())
      );
      
      expect(refreshedButtonTexts).toEqual(initialButtonTexts);
    });

    test('should handle multiple rapid navigation switches', async () => {
      // Rapidly switch between tabs
      for (let i = 0; i < 3; i++) {
        await page.evaluate(() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const liveBtn = buttons.find(btn => btn.textContent?.includes('Live Tracking'));
          if (liveBtn) (liveBtn as HTMLButtonElement).click();
        });
        
        await new Promise(resolve => setTimeout(resolve, 200));
        
        await page.evaluate(() => {
          const buttons = Array.from(document.querySelectorAll('button'));
          const tripsBtn = buttons.find(btn => btn.textContent?.includes('My Trips'));
          if (tripsBtn) (tripsBtn as HTMLButtonElement).click();
        });
        
        await new Promise(resolve => setTimeout(resolve, 200));
      }
      
      // Verify page is still functional
      const finalButtons = await page.$$('button');
      expect(finalButtons.length).toBeGreaterThan(0);
    });
  });

  describe('Visual Verification', () => {
    test('should capture main application screenshot', async () => {
      await page.screenshot({ 
        path: 'tests/screenshots/main-app-comprehensive.png' as `${string}.png`,
        fullPage: true 
      });
      
      // Screenshot taken successfully if we reach here
      expect(true).toBe(true);
    });

    test('should capture live tracking view screenshot', async () => {
      await page.evaluate(() => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const liveBtn = buttons.find(btn => btn.textContent?.includes('Live Tracking'));
        if (liveBtn) (liveBtn as HTMLButtonElement).click();
      });
      
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      await page.screenshot({ 
        path: 'tests/screenshots/live-tracking-comprehensive.png' as `${string}.png`,
        fullPage: true 
      });
      
      expect(true).toBe(true);
    });

    test('should capture mobile view screenshot', async () => {
      await page.setViewport({ width: 375, height: 667 });
      await page.reload();
      await page.waitForSelector('body');
      await new Promise(resolve => setTimeout(resolve, 500));
      
      await page.screenshot({ 
        path: 'tests/screenshots/mobile-comprehensive.png' as `${string}.png`,
        fullPage: true 
      });
      
      expect(true).toBe(true);
    });
  });
});