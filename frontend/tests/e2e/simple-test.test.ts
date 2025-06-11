import puppeteer, { Browser, Page } from 'puppeteer';
import { launchBrowser, createPage, TEST_CONFIG } from '../setup';

describe('Location Tracker - Simple Test', () => {
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
  });

  afterEach(async () => {
    await page.close();
  });

  test('should load the application', async () => {
    // Wait for the page to load
    await page.waitForSelector('body');
    
    // Get the page title
    const title = await page.title();
    expect(title).toBeDefined();
    
    // Check if there are buttons on the page
    const buttons = await page.$$('button');
    expect(buttons.length).toBeGreaterThan(0);
    
    // Take a screenshot
    await page.screenshot({ path: 'tests/screenshots/simple-test.png' });
  });

  test('should have navigation elements', async () => {
    await page.waitForSelector('body');
    
    // Check for common navigation elements
    const buttons = await page.$$eval('button', buttons => 
      buttons.map(btn => btn.textContent?.trim())
    );
    
    expect(buttons.length).toBeGreaterThan(0);
    console.log('Found buttons:', buttons);
  });
});