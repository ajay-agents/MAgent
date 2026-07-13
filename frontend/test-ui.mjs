import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SS = (name) => path.join(__dirname, `${name}.png`);

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const page = await ctx.newPage();

const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push(`[${m.type()}] ${m.text()}`); });
page.on('pageerror', e => errors.push(`[pageerror] ${e.message}`));

// ── 1. Homepage ───────────────────────────────────────────────────────────────
console.log('1. Loading homepage...');
await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('01-homepage') });
console.log('   ✓ 01-homepage.png');

// ── 2. Auth modal — open + screenshot ────────────────────────────────────────
console.log('2. Opening auth modal...');
await page.locator('nav button', { hasText: /create email/i }).click();
await page.waitForSelector('text=Welcome to MailFlow AI', { timeout: 5000 });
await page.screenshot({ path: SS('02-auth-modal') });
console.log('   ✓ 02-auth-modal.png');

// ── 3. Login via the modal ────────────────────────────────────────────────────
console.log('3. Logging in via modal...');
// Ensure Login tab is active
const loginTab = page.locator('button', { hasText: /^Login$/ });
if (await loginTab.count()) await loginTab.click();
await page.waitForTimeout(200);

await page.locator('input[name="email"]').fill('test@example.com');
await page.locator('input[name="password"]').fill('Test1234!');

// Intercept the login response to debug
const [loginResp] = await Promise.all([
  page.waitForResponse(r => r.url().includes('/api/auth/login'), { timeout: 10000 }),
  page.locator('button[type="submit"]').click(),
]);
const loginStatus = loginResp.status();
const loginBody = await loginResp.text();
console.log(`   Login API → ${loginStatus}: ${loginBody.slice(0, 120)}`);

if (loginStatus !== 200) {
  console.log('   ✗ Login failed — injecting token directly instead');
  // Fallback: call the API via node-fetch and inject token into localStorage
  const resp = await fetch('http://localhost:8000/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'test@example.com', password: 'Test1234!' }),
  });
  if (!resp.ok) {
    // Try signup first then login
    await fetch('http://localhost:8000/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'test@example.com', password: 'Test1234!' }),
    });
    const r2 = await fetch('http://localhost:8000/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: 'test@example.com', password: 'Test1234!' }),
    });
    const data = await r2.json();
    await page.goto('http://localhost:5173');
    await page.evaluate((token) => {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify({ email: 'test@example.com' }));
    }, data.access_token);
    console.log('   Injected token via localStorage');
  } else {
    const data = await resp.json();
    await page.goto('http://localhost:5173');
    await page.evaluate((token) => {
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify({ email: 'test@example.com' }));
    }, data.access_token);
    console.log('   Injected token via localStorage');
  }
}

// ── 4. Dashboard ──────────────────────────────────────────────────────────────
console.log('4. Dashboard...');
await page.goto('http://localhost:5173/dashboard', { waitUntil: 'networkidle' });
const dashUrl = page.url();
console.log(`   URL: ${dashUrl}`);
await page.screenshot({ path: SS('03-dashboard') });
console.log('   ✓ 03-dashboard.png');

// ── 5. Create Email page ──────────────────────────────────────────────────────
console.log('5. Create Email...');
await page.goto('http://localhost:5173/create-email', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('04-create-email') });
console.log('   ✓ 04-create-email.png');

// Fill the form
await page.locator('input[placeholder="Your Name"]').fill('Alice');
await page.locator('input[placeholder="Recipient Name"]').fill('Bob');
await page.locator('input[placeholder="Recipient Email"]').fill('bob@example.com');
await page.locator('textarea').fill('We met at DevConf 2025 AI track — I wanted to follow up on automation tooling.');
await page.screenshot({ path: SS('05-form-filled') });
console.log('   ✓ 05-form-filled.png');

// ── 6. Drafts ─────────────────────────────────────────────────────────────────
console.log('6. Drafts...');
await page.goto('http://localhost:5173/drafts', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('06-drafts') });
console.log('   ✓ 06-drafts.png');

// ── 7. Scheduled Emails ───────────────────────────────────────────────────────
console.log('7. Scheduled Emails...');
await page.goto('http://localhost:5173/scheduled-emails', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('07-scheduled') });
console.log('   ✓ 07-scheduled.png');

// ── 8. Sent Emails ────────────────────────────────────────────────────────────
console.log('8. Sent Emails...');
await page.goto('http://localhost:5173/sent-emails', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('08-sent') });
console.log('   ✓ 08-sent.png');

// ── 9. Settings ───────────────────────────────────────────────────────────────
console.log('9. Settings...');
await page.goto('http://localhost:5173/settings', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('09-settings') });
console.log('   ✓ 09-settings.png');

// ── Summary ───────────────────────────────────────────────────────────────────
console.log('\n=== Console Errors ===');
if (errors.length === 0) console.log('None');
else errors.forEach(e => console.log(' ', e));

await browser.close();
console.log('\nAll screenshots done.');
