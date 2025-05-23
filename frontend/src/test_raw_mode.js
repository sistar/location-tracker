// This is a manual test script that can be run in the browser console to test the raw GPS mode
// It assumes you're already on the location tracker app

/**
 * Test the raw GPS mode functionality
 */
function testRawGpsMode() {
  console.log("Starting raw GPS mode test...");
  
  // Test setup - ensure we're starting from a clean state
  console.log("1. Setting up test environment...");
  
  // Check if the raw GPS mode button exists
  const rawGpsModeButton = Array.from(document.querySelectorAll('button')).find(btn => 
    btn.textContent?.includes('View Raw GPS Data')
  );
  
  if (!rawGpsModeButton) {
    console.error("❌ Raw GPS mode button not found. Is the UI updated with the new feature?");
    return;
  }
  
  console.log("✓ Raw GPS mode button found");
  
  // Click the button to enter raw GPS mode
  console.log("2. Entering Raw GPS mode...");
  rawGpsModeButton.click();
  
  // Wait for data to load and UI to update
  setTimeout(() => {
    // Check if we're in raw GPS mode by looking for the mode indicator
    const modeText = Array.from(document.querySelectorAll('div')).find(div => 
      div.textContent?.includes('Mode: Raw GPS Data')
    );
    
    if (!modeText) {
      console.error("❌ Mode indicator not found. UI may not have updated correctly.");
      return;
    }
    
    console.log("✓ Successfully entered Raw GPS mode");
    
    // Check for raw data points
    const rawPointCount = document.body.textContent.match(/(\d+) raw data points/);
    if (rawPointCount && parseInt(rawPointCount[1]) > 0) {
      console.log(`✓ Found ${rawPointCount[1]} raw data points`);
    } else {
      console.error("❌ No raw data points were found or count not displayed");
    }
    
    // Check for days selector
    const daysSelector = document.querySelector('#raw-days-select');
    if (daysSelector) {
      console.log("✓ Days selector found");
      
      // Try changing the days value
      console.log("3. Testing days selection change...");
      daysSelector.value = '3';
      
      // Dispatch a change event
      const event = new Event('change', { bubbles: true });
      daysSelector.dispatchEvent(event);
      
      console.log("✓ Changed days selection to 3 days");
    } else {
      console.error("❌ Days selector not found");
    }
    
    // Check for refresh button
    const refreshButton = Array.from(document.querySelectorAll('button')).find(btn => 
      btn.textContent?.includes('Refresh')
    );
    
    if (refreshButton) {
      console.log("✓ Refresh button found");
    } else {
      console.error("❌ Refresh button not found");
    }
    
    // Now try to go back to normal mode
    console.log("4. Returning to Live Tracking mode...");
    const backToLiveButton = Array.from(document.querySelectorAll('button')).find(btn => 
      btn.textContent?.includes('Switch to Live Tracking')
    );
    
    if (backToLiveButton) {
      backToLiveButton.click();
      console.log("✓ Clicked return to Live Tracking button");
      
      // Wait for UI to update
      setTimeout(() => {
        const normalModeText = Array.from(document.querySelectorAll('div')).find(div => 
          div.textContent?.includes('Mode: Live Tracking')
        );
        
        if (normalModeText) {
          console.log("✓ Successfully returned to Live Tracking mode");
          console.log("All tests completed successfully!");
        } else {
          console.error("❌ Failed to return to Live Tracking mode");
        }
      }, 1000);
    } else {
      console.error("❌ Return to Live Tracking button not found");
    }
  }, 2000);
}

// Instructions to use this test
console.log(`
Raw GPS Mode Manual Test Script
------------------------------
To run this test:
1. Ensure you're on the location tracker app
2. Run this script by calling testRawGpsMode() in the console
3. Check console for test results

This script will:
- Check for the Raw GPS mode button
- Enter Raw GPS mode
- Verify data is displayed
- Test changing the days selector
- Return to Live Tracking mode
`);

// Use this function to run the test
// testRawGpsMode();