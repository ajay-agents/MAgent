import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const page = await ctx.newPage();

const failed = [];
page.on('response', r => { if (r.status() === 404) failed.push(r.url()); });

// Login first
await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
await page.locator('nav button', { hasText: /create email/i }).click();
await page.waitForTimeout(500);
const loginTab = page.locator('button', { hasText: /^login$/i });
if (await loginTab.count()) await loginTab.click();
await page.locator('input[name="email"]').fill('test@example.com');
await page.locator('input[name="password"]').fill('Test1234!');
await page.locator('button[type="submit"]').click();
await page.waitForURL('**/dashboard', { timeout: 10000 }).catch(() => {});

// Visit all pages
for (const route of ['/dashboard', '/create-email', '/drafts', '/scheduled-emails', '/sent-emails', '/settings']) {
  await page.goto(`http://localhost:5173${route}`, { waitUntil: 'networkidle' });
}

console.log('404 URLs:');
failed.forEach(u => console.log(' ', u));
if (!failed.length) console.log('  None');

await browser.close();
