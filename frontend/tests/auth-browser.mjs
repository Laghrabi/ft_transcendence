// Requires Playwright and Chromium; see docs/auth-testing.md.
import assert from 'node:assert/strict';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const base = process.env.FRONTEND_URL || 'http://127.0.0.1:5173';
const errors = [];
page.on('pageerror', error => errors.push(error.message));
let posts = [];
let mode = 'success';
let release;
await page.route('**/api/auth/**', async route => {
  const path = new URL(route.request().url()).pathname;
  if (path.endsWith('/csrf/')) return route.fulfill({ json: { csrfToken: 'test-token' } });
  if (path.endsWith('/me/')) return route.fulfill({ json: { name: 'Test Staff' } });
  posts.push({ path, body: route.request().postDataJSON(), headers: route.request().headers() });
  if (mode === 'delay') await new Promise(resolve => { release = resolve; });
  if (mode === 'error') return route.fulfill({ status: 400, json: { detail: 'Account pending approval.' } });
  if (mode === 'proxy') return route.fulfill({ status: 500, body: '' });
  if (mode === 'network') return route.abort();
  return route.fulfill({ json: { message: 'Registration successful. Awaiting administrator approval.' } });
});
const submit = () => page.locator('button[type=submit]').click();
const alert = () => page.getByRole('alert');
async function expectText(locator, text) {
  await locator.filter({ hasText: text }).waitFor();
}
async function registerFields(password = 'Strong123!', confirm = password, name = ' Test Staff ') {
  await page.locator('#register-name').fill(name);
  await page.locator('#register-email').fill('staff@example.com');
  await page.locator('#register-password').fill(password);
  await page.locator('#register-confirm').fill(confirm);
}
try {
  await page.goto(base);
  await page.waitForURL('**/login');
  await submit();
  assert.equal(posts.length, 0);
  assert.equal(await page.locator('#email').evaluate(el => el.validity.valueMissing), true);
  await page.locator('#email').fill('invalid');
  await page.locator('#password').fill('password');
  await submit();
  assert.equal(await page.locator('#email').evaluate(el => el.validity.typeMismatch), true);
  assert.equal(posts.length, 0);
  await page.getByRole('link', { name: 'Register hospital staff' }).click();
  await page.waitForURL('**/register');
  await submit();
  assert.equal(await page.locator('#register-name').evaluate(el => el.validity.valueMissing), true);
  await registerFields('Strong123!', 'Strong123!', '   ');
  await submit();
  await expectText(alert(), 'Please enter your full name.');
  await registerFields('Short1!');
  await submit();
  assert.equal(await page.locator('#register-password').evaluate(el => el.validity.tooShort), true);
  for (const password of ['Password!', 'Password1']) {
    await registerFields(password);
    await submit();
    await expectText(alert(), 'Please meet all password requirements.');
  }
  await registerFields('Strong123!', 'Different123!');
  await submit();
  await expectText(alert(), 'Passwords do not match.');
  assert.equal(posts.length, 0);
  await registerFields();
  assert.equal(await page.locator('.requirement-met').count(), 3);
  mode = 'delay';
  await submit();
  await expectText(page.locator('button[type=submit]'), 'Creating account...');
  assert.equal(await page.locator('button[type=submit]').isDisabled(), true);
  assert.equal(posts.length, 1);
  mode = 'success'; release();
  await expectText(page.getByRole('status'), 'Awaiting administrator approval');
  assert.equal(await page.locator('#register-password').inputValue(), '');
  assert.equal(await page.locator('#register-confirm').inputValue(), '');
  assert.equal(posts[0].body.name, 'Test Staff');
  assert.equal(posts[0].headers['x-csrftoken'], 'test-token');
  await registerFields(); mode = 'error'; await submit();
  await expectText(alert(), 'Account pending approval.');
  assert.equal(await page.locator('button[type=submit]').isEnabled(), true);
  await page.getByRole('link', { name: 'Sign In', exact: true }).click();
  await page.waitForURL('**/login');
  await page.locator('#email').fill('staff@example.com');
  await page.locator('#password').fill('Strong123!');
  mode = 'error'; await submit();
  await expectText(alert(), 'Account pending approval.');
  mode = 'proxy'; await submit();
  await expectText(alert(), 'service is unavailable');
  mode = 'network'; await submit();
  await expectText(alert(), 'Unable to reach');
  mode = 'delay'; await submit();
  await expectText(page.locator('button[type=submit]'), 'Signing in...');
  assert.equal(await page.locator('button[type=submit]').isDisabled(), true);
  mode = 'success'; release();
  await expectText(page.getByRole('status'), 'Welcome, Test Staff!');
  assert.equal(await page.locator('button[type=submit]').isEnabled(), true);
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ['/login', '/register']) {
      await page.goto(base + path);
      await page.locator('button[type=submit]').waitFor();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${path} overflows at ${width}px`);
      assert.equal(await page.locator('button[type=submit]').isVisible(), true);
    }
  }
  assert.deepEqual(errors, []);
  console.log('PASS: native validation, whitespace name, all password rules, confirmation, requirement indicators, links, root redirect, loading, success/reset, API errors/retry, CSRF header, responsive widths 375/768/1440; no runtime errors. API responses were mocked.');
} finally {
  await browser.close();
}
