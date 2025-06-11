import puppeteer, { Browser, Page } from 'puppeteer';

export const TEST_CONFIG = {
  baseUrl: 'http://localhost:5173',
  timeout: 30000,
  headless: true,
  viewport: {
    width: 1280,
    height: 720
  }
};

export const launchBrowser = async (): Promise<Browser> => {
  return await puppeteer.launch({
    headless: TEST_CONFIG.headless,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu'
    ]
  });
};

export const createPage = async (browser: Browser): Promise<Page> => {
  const page = await browser.newPage();
  await page.setViewport(TEST_CONFIG.viewport);
  
  // Increase timeout for slow operations
  page.setDefaultTimeout(TEST_CONFIG.timeout);
  page.setDefaultNavigationTimeout(TEST_CONFIG.timeout);
  
  // Mock geolocation to avoid permission dialogs
  await page.setGeolocation({ latitude: 37.7749, longitude: -122.4194 });
  
  return page;
};

export const waitForPageLoad = async (page: Page): Promise<void> => {
  await page.waitForSelector('body', { timeout: TEST_CONFIG.timeout });
};

// Global test utilities - disabled for now
// declare global {
//   namespace jest {
//     interface Matchers<R> {
//       toMatchScreenshot(name: string): R;
//     }
//   }
// }