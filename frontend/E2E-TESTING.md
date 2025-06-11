# E2E Testing with Puppeteer

This document describes the end-to-end (E2E) testing setup for the Location Tracker frontend application using Puppeteer.

## Overview

The E2E testing suite provides comprehensive regression testing for the Location Tracker application, including:

- **Navigation Testing**: Tab switching, responsive design, basic UI interactions
- **Location Tracking**: Map functionality, vehicle selection, live tracking features  
- **Drivers Logs**: Form submission, data display, CRUD operations
- **Visual Regression**: Screenshot comparisons across different states and viewports

## Setup

### Prerequisites

- Node.js 18+ 
- Chrome/Chromium browser (installed automatically with Puppeteer)
- Development server running on `http://localhost:5173`

### Installation

Dependencies are already installed if you've run `npm install` in the frontend directory:

```bash
cd frontend
npm install
```

Key testing dependencies:
- `puppeteer` - Headless browser automation
- `jest` - Test framework
- `pixelmatch` - Image comparison for visual regression
- `pngjs` - PNG image processing

## Running Tests

### Quick Start

```bash
# Run all E2E tests with automatic dev server management
./tests/run-e2e.sh

# Or run specific test suites
./tests/run-e2e.sh navigation
./tests/run-e2e.sh location  
./tests/run-e2e.sh logs
./tests/run-e2e.sh visual
```

### Manual Test Execution

```bash
# Start dev server first
npm run dev

# Run tests (in another terminal)
npm run test:e2e                    # All E2E tests
npm run test:visual                 # Visual regression only
npm run test tests/e2e/app-navigation.test.ts  # Specific test file
```

### Available Scripts

- `npm run test` - Run all tests
- `npm run test:e2e` - Run E2E tests only
- `npm run test:visual` - Run visual regression tests only
- `npm run test:watch` - Run tests in watch mode
- `npm run test:coverage` - Run tests with coverage report
- `npm run test:ci` - Run tests in CI mode

## Test Structure

```
tests/
├── e2e/
│   ├── app-navigation.test.ts      # Navigation and UI tests
│   ├── location-tracking.test.ts   # Location and map tests
│   ├── drivers-logs.test.ts        # Form and data tests
│   └── visual-regression.test.ts   # Visual comparison tests
├── utils/
│   └── visual-regression.ts        # Screenshot utilities
├── screenshots/
│   ├── baseline/                   # Reference screenshots
│   ├── actual/                     # Current test screenshots
│   └── diff/                       # Difference images
├── setup.ts                        # Test configuration
└── run-e2e.sh                      # Test runner script
```

## Visual Regression Testing

### How It Works

1. **Baseline Creation**: First test run creates reference screenshots
2. **Comparison**: Subsequent runs compare new screenshots against baselines
3. **Diff Generation**: Differences are highlighted in generated diff images
4. **Threshold**: Tests fail if differences exceed 0.1% of pixels

### Managing Baselines

```bash
# Update baselines (when UI changes are intentional)
rm -rf tests/screenshots/baseline/*
npm run test:visual

# Review differences
open tests/screenshots/diff/
```

### Screenshot Naming Convention

Screenshots are named descriptively:
- `main-app-loaded.png` - Initial app state
- `live-tracking-map.png` - Map view
- `form-filled-state.png` - Filled form
- `responsive-mobile-small.png` - Mobile viewport

## Test Configuration

### Browser Settings

```typescript
// tests/setup.ts
export const TEST_CONFIG = {
  baseUrl: 'http://localhost:5173',
  timeout: 30000,
  headless: true,
  viewport: { width: 1280, height: 720 }
};
```

### Mock API Responses

Tests use mocked API responses for consistency:

```typescript
await page.route('**/api/location**', route => {
  route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      lat: '37.7749',
      lon: '-122.4194',
      timestamp: Date.now()
    })
  });
});
```

## Writing Tests

### Basic Test Structure

```typescript
import { launchBrowser, createPage, TEST_CONFIG } from '../setup';
import { expectScreenshotMatch } from '../utils/visual-regression';

describe('My Test Suite', () => {
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

  test('should do something', async () => {
    await page.waitForSelector('[data-testid="my-element"]');
    await expectScreenshotMatch(page, 'my-test-state');
  });
});
```

### Best Practices

1. **Use data-testid attributes** for reliable element selection
2. **Mock external APIs** to avoid flaky tests
3. **Wait for elements** before interactions
4. **Use descriptive screenshot names**
5. **Test responsive behavior** across viewport sizes
6. **Group related tests** in describe blocks

### Data Test IDs

Add `data-testid` attributes to components for reliable testing:

```tsx
<button data-testid="add-log-button" onClick={handleClick}>
  Add Log
</button>

<div data-testid="trips-overview">
  {/* content */}
</div>
```

## CI Integration

### GitHub Actions

Create `.github/workflows/e2e-tests.yml`:

```yaml
name: E2E Tests

on:
  pull_request:
  push:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: cd frontend && npm ci
      
      - name: Run E2E tests
        run: cd frontend && npm run test:ci
      
      - name: Upload screenshots on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: screenshot-diffs
          path: frontend/tests/screenshots/diff/
```

## Troubleshooting

### Common Issues

1. **Tests timeout**: Increase timeout in `setup.ts` or specific tests
2. **Screenshots differ**: Check for dynamic content (timestamps, etc.)
3. **Server not starting**: Ensure port 5173 is available
4. **Browser launch fails**: Check Puppeteer installation

### Debug Mode

Run tests with browser visible:

```typescript
// In setup.ts, change:
headless: false  // Shows browser window
```

### Performance

- Tests run headless by default for speed
- Parallel execution with Jest's `--maxWorkers` flag
- Screenshot comparison is optimized with pixelmatch

## Maintenance

### Regular Tasks

1. **Update baselines** when UI intentionally changes
2. **Review failed tests** for legitimate regressions
3. **Clean up old screenshots** periodically
4. **Update test dependencies** regularly

### Monitoring

- Watch for flaky tests in CI
- Monitor test execution time
- Review visual regression patterns
- Update browser versions with Puppeteer updates