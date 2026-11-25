import test from 'node:test';
import assert from 'node:assert/strict';
import { registerUser, loginUser, getCurrentUser } from '../src/api/auth.js';

const json = (data, status = 200) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json' },
});

function mockFetch(t, replies, cookie = '') {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (...args) => {
    calls.push(args);
    const reply = replies.shift();
    if (reply instanceof Error) throw reply;
    assert.ok(reply, 'Unexpected request');
    return reply;
  });
  const previousDocument = Object.getOwnPropertyDescriptor(globalThis, 'document');
  Object.defineProperty(globalThis, 'document', { configurable: true, value: { cookie } });
  t.after(() => {
    if (previousDocument) Object.defineProperty(globalThis, 'document', previousDocument);
    else delete globalThis.document;
  });
  return calls;
}

test('registration sends CSRF header, cookies and expected fields', async t => {
  const calls = mockFetch(t, [json({ csrfToken: 'token' }), json({ message: 'Pending approval' }, 201)]);
  assert.deepEqual(await registerUser('Staff', 'staff@example.com', 'Safe123!'), { message: 'Pending approval' });
  assert.equal(calls[0][0], '/api/auth/csrf/');
  assert.equal(calls[0][1].credentials, 'include');
  assert.equal(calls[1][0], '/api/auth/register/');
  assert.equal(calls[1][1].method, 'POST');
  assert.equal(calls[1][1].credentials, 'include');
  assert.equal(calls[1][1].headers['X-CSRFToken'], 'token');
  assert.deepEqual(JSON.parse(calls[1][1].body), { name: 'Staff', email: 'staff@example.com', password: 'Safe123!' });
});

test('login supports the CSRF cookie and retrieves current user', async t => {
  const calls = mockFetch(t, [json({}), json({}), json({ name: 'Staff' })], 'other=value; csrftoken=cookie-token');
  await loginUser('staff@example.com', 'Safe123!');
  assert.equal(calls[1][0], '/api/auth/login/');
  assert.equal(calls[1][1].headers['X-CSRFToken'], 'cookie-token');
  assert.deepEqual(JSON.parse(calls[1][1].body), { email: 'staff@example.com', password: 'Safe123!' });
  assert.deepEqual(await getCurrentUser(), { name: 'Staff' });
  assert.equal(calls[2][0], '/api/auth/me/');
  assert.equal(calls[2][1].credentials, 'include');
});

test('missing CSRF token prevents the POST', async t => {
  const calls = mockFetch(t, [json({})]);
  await assert.rejects(loginUser('a@b.com', 'password'), /CSRF token/);
  assert.equal(calls.length, 1);
});

for (const [label, response, expected] of [
  ['invalid credentials', json({ detail: 'Invalid credentials.' }, 401), /Invalid credentials/],
  ['duplicate email', json({ email: ['Email already registered.'] }, 400), /Email already registered/],
  ['CSRF rejection', json({ detail: 'CSRF Failed' }, 403), /CSRF Failed/],
  ['proxy failure', new Response('', { status: 500 }), /service is unavailable/],
  ['malformed success', new Response('<html>'), /unexpected response/],
  ['network failure', new TypeError('Failed to fetch'), /Unable to reach/],
]) {
  test(label, async t => {
    mockFetch(t, [json({ csrf_token: 'token' }), response]);
    await assert.rejects(loginUser('a@b.com', 'password'), expected);
  });
}
