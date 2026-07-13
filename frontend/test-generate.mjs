import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SS = (name) => path.join(__dirname, `${name}.png`);

// Get a JWT token via the API
const loginResp = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ email: 'test@example.com', password: 'Test1234!' }),
});
const { access_token: token } = await loginResp.json();
console.log('Token acquired:', token.slice(0, 20) + '...');

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const page = await ctx.newPage();

const errors = [];
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', e => errors.push(e.message));

// Inject auth token
await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
await page.evaluate((t) => {
  localStorage.setItem('token', t);
  localStorage.setItem('user', JSON.stringify({ email: 'test@example.com' }));
}, token);

// ── 1. Dashboard — initial stats (should be 0) ───────────────────────────────
console.log('\n1. Dashboard — initial stats...');
await page.goto('http://localhost:5173/dashboard', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('gen-01-dashboard-before') });
console.log('   ✓ gen-01-dashboard-before.png');

// ── 2. Create Email — fill form ───────────────────────────────────────────────
console.log('\n2. Create Email — filling form...');
await page.goto('http://localhost:5173/create-email', { waitUntil: 'networkidle' });
await page.locator('input[placeholder="Your Name"]').fill('Ajay');
await page.locator('input[placeholder="Recipient Name"]').fill('Sarah');
await page.locator('input[placeholder="Recipient Email"]').fill('sarah@acmecorp.com');
await page.locator('textarea').fill('Sarah leads growth at Acme Corp. I want to explore a partnership around AI tooling.');
await page.screenshot({ path: SS('gen-02-form-filled') });
console.log('   ✓ gen-02-form-filled.png');

// ── 3. Click Generate and wait for result ────────────────────────────────────
console.log('\n3. Clicking Generate Email...');
const [genResponse] = await Promise.all([
  page.waitForResponse(r => r.url().includes('/api/emails/generate'), { timeout: 30000 }),
  page.locator('button', { hasText: /Generate Email/i }).click(),
]);
const genStatus = genResponse.status();
const genData = await genResponse.json();
console.log(`   API status: ${genStatus}`);
console.log(`   Email ID:   ${genData.id}`);
console.log(`   Model:      ${genData.ai_model}`);
console.log(`   Subject:    ${genData.subject}`);
console.log(`   Cost:       $${genData.estimated_cost_usd}`);

// Wait for preview to appear
await page.waitForSelector('text=' + genData.subject.slice(0, 20), { timeout: 5000 }).catch(() => {});
await page.waitForTimeout(500);
await page.screenshot({ path: SS('gen-03-email-generated') });
console.log('   ✓ gen-03-email-generated.png');

// ── 4. Open Schedule modal ───────────────────────────────────────────────────
console.log('\n4. Testing Schedule modal...');
await page.locator('button', { hasText: /Schedule/i }).last().click();
await page.waitForTimeout(400);
await page.screenshot({ path: SS('gen-04-schedule-modal') });
console.log('   ✓ gen-04-schedule-modal.png');

// Fill schedule date/time and submit
const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
const dateStr = tomorrow.toISOString().split('T')[0];
await page.locator('input[type="date"]').fill(dateStr);
await page.locator('input[type="time"]').fill('09:00');

const [schedResp] = await Promise.all([
  page.waitForResponse(r => r.url().includes('/schedule'), { timeout: 10000 }),
  page.locator('button', { hasText: /^Schedule$/ }).last().click(),
]);
console.log(`   Schedule API: ${schedResp.status()}`);
await page.waitForTimeout(400);
await page.screenshot({ path: SS('gen-05-scheduled-success') });
console.log('   ✓ gen-05-scheduled-success.png');

// ── 5. Scheduled Emails — should now show 1 email ────────────────────────────
console.log('\n5. Scheduled Emails page...');
await page.goto('http://localhost:5173/scheduled-emails', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('gen-06-scheduled-list') });
console.log('   ✓ gen-06-scheduled-list.png');

// ── 6. Cancel schedule — moves back to draft ─────────────────────────────────
console.log('\n6. Cancelling schedule...');
const cancelBtn = page.locator('table button').nth(2); // trash icon
const [cancelResp] = await Promise.all([
  page.waitForResponse(r => r.url().includes('/schedule') && r.request().method() === 'DELETE', { timeout: 10000 }),
  cancelBtn.click(),
]);
console.log(`   Cancel API: ${cancelResp.status()}`);
await page.waitForTimeout(400);
await page.screenshot({ path: SS('gen-07-after-cancel') });
console.log('   ✓ gen-07-after-cancel.png');

// ── 7. Drafts — email should be back as draft ────────────────────────────────
console.log('\n7. Drafts page — email should be back...');
await page.goto('http://localhost:5173/drafts', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('gen-08-drafts-with-email') });
console.log('   ✓ gen-08-drafts-with-email.png');

// ── 8. Dashboard — stats should now show 1 generated ────────────────────────
console.log('\n8. Dashboard — stats after generation...');
await page.goto('http://localhost:5173/dashboard', { waitUntil: 'networkidle' });
await page.screenshot({ path: SS('gen-09-dashboard-after') });
console.log('   ✓ gen-09-dashboard-after.png');

// ── Summary ───────────────────────────────────────────────────────────────────
console.log('\n=== Console Errors ===');
const realErrors = errors.filter(e => !e.includes('404'));
if (realErrors.length === 0) console.log('None');
else realErrors.forEach(e => console.log(' ', e));

await browser.close();
console.log('\nAll done.');
