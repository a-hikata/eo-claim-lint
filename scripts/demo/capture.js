/**
 * Capture the GitHub screenshots the demo GIF is built from.
 *
 * Every frame is a real page of a real pull request that ran the published
 * action. Nothing here draws a mock GitHub interface.
 *
 * GitHub shows the merge box and the Actions log only to signed-in viewers, so
 * the first run opens a browser window and waits for a sign-in. The browser
 * profile is written to --profile; delete that directory afterwards, since it
 * holds a live GitHub session.
 *
 * Run it twice: once while the pull request is still failing (for the red
 * frames), and again after pushing the evidence fix (for the green frames).
 *
 *   node capture.js \
 *     --repo        a-hikata/eo-claim-lint-demo-recording \
 *     --pr          2 \
 *     --red-job-url https://github.com/OWNER/REPO/actions/runs/<run>/job/<job> \
 *     --fix-sha     <sha of the commit that adds the evidence> \
 *     --out         ./frames \
 *     --profile     ./gh-profile
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

function args() {
  const out = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    out[process.argv[i].replace(/^--/, '')] = process.argv[i + 1];
  }
  for (const k of ['repo', 'pr', 'red-job-url', 'fix-sha', 'out', 'profile']) {
    if (!out[k]) throw new Error(`missing --${k}`);
  }
  return out;
}

/** Remove everything that is about the viewer rather than the pull request. */
async function clean(page) {
  await page.evaluate(() => {
    const kill = [
      '.AppHeader', 'header.AppHeader', '.js-header-wrapper', '.HeaderMenu',
      '.js-notice', '.flash', '.js-flash-alert', '.js-cookie-consent',
      'footer', '.footer', '[data-testid="notification-indicator"]',
    ];
    for (const sel of kill) document.querySelectorAll(sel).forEach((e) => e.remove());
    document.querySelectorAll('div[role="alert"]').forEach((e) => e.remove());
  });
  await page.waitForTimeout(300);
}

async function signedInAs(page) {
  return page.evaluate(() => {
    const m = document.querySelector('meta[name="user-login"]');
    return m ? m.getAttribute('content') : '';
  });
}

async function shoot(page, file, url, { expandStep } = {}) {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(6000);
  if (expandStep) {
    try {
      await page.locator(`text=${expandStep}`).first().click({ timeout: 8000 });
      await page.waitForTimeout(5000);
    } catch (e) {
      console.warn(`could not expand "${expandStep}": ${e.message}`);
    }
  }
  await clean(page);
  await page.screenshot({ path: file, fullPage: true });
  console.log('captured', path.basename(file));
}

(async () => {
  const a = args();
  const R = `https://github.com/${a.repo}`;
  fs.mkdirSync(a.out, { recursive: true });

  const ctx = await chromium.launchPersistentContext(a.profile, {
    headless: false,
    viewport: { width: 1400, height: 1000 },
    deviceScaleFactor: 2,
    colorScheme: 'light',
    reducedMotion: 'reduce',
  });
  const page = ctx.pages()[0] || (await ctx.newPage());

  await page.goto('https://github.com/login', { waitUntil: 'domcontentloaded' });
  let who = await signedInAs(page);
  if (!who) {
    console.log('Sign in to GitHub in the open window; capture resumes automatically.');
    const deadline = Date.now() + 15 * 60 * 1000;
    while (Date.now() < deadline && !who) {
      await page.waitForTimeout(4000);
      who = await signedInAs(page).catch(() => '');
    }
  }
  if (!who) throw new Error('timed out waiting for sign-in');
  console.log('signed in as', who);

  const f = (n) => path.join(a.out, n);

  // Red: the pull request as opened, with evidence still an empty list.
  await shoot(page, f('pr-red-files.png'), `${R}/pull/${a.pr}/files`);
  await shoot(page, f('pr-red-conversation.png'), `${R}/pull/${a.pr}`);
  await shoot(page, f('job-red-log.png'), a['red-job-url'],
    { expandStep: 'Run a-hikata/eo-claim-lint@v0' });

  // Green: the same pull request once one evidence reference is added.
  await shoot(page, f('pr-fix-diff.png'), `${R}/pull/${a.pr}/commits/${a['fix-sha']}`);
  await shoot(page, f('pr-green-conversation.png'), `${R}/pull/${a.pr}`);

  console.log('\nDone. Now delete the browser profile:');
  console.log(`  rm -rf ${a.profile}`);
  await ctx.close();
})();
