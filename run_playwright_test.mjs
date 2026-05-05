import { chromium } from 'playwright';
import { runAdversarialBrowserPlaythrough } from './tools/web_qa/adversarial_browser_playthrough.mjs';

async function main() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Create a wrapper object that matches what the script expects for `tab.playwright`
  const tab = {
    playwright: page,
    dev: {
      logs: async ({ limit }) => [] // Stubbed out for now, can implement full CDP log capture if needed
    },
    url: async () => page.url(),
    goto: async (url) => page.goto(url),
    back: async () => page.goBack(),
    forward: async () => page.goForward(),
    reload: async () => page.reload()
  };

  // Add the domSnapshot method that the script expects
  page.domSnapshot = async () => page.content();
  
  // Wrap screenshot to mock return object expecting an image with a toBase64 method
  const originalScreenshot = page.screenshot.bind(page);
  page.screenshot = async (options) => {
    const buffer = await originalScreenshot(options);
    return {
      toBase64: async () => buffer.toString('base64'),
      buffer
    };
  };

  try {
    const results = await runAdversarialBrowserPlaythrough({
      tab,
      baseUrl: 'http://127.0.0.1:8000', // Fastapi backend serving dist
      outputDir: './output/playwright-test-run'
    });
    console.log(`Playwright test completed. Passed assertions: ${results.passedAssertions}, Failed: ${results.failedAssertions}, Findings: ${results.findingCount}`);
    if (results.failedAssertions > 0 || results.findingCount > 0) {
      console.log('Issues found. Check output directory for details.');
    }
  } catch (error) {
    console.error('Playwright test failed fatally:', error);
  } finally {
    await browser.close();
  }
}

main();