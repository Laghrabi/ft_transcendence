# CareFlow Login and Register testing

Run from `frontend/`:

```sh
npm test
npm run build
npm run dev
```

The package file was valid and already had a working Vite build script.
`npm test` now runs nine API tests with simulated responses. They verify request
bodies, CSRF tokens, session cookies, missing tokens, credential errors, duplicate
email, server errors, malformed responses, and network errors. They do not create
real accounts.

The browser regression script is `frontend/tests/auth-browser.mjs`. It needs
Playwright, Chromium, its Linux libraries, and a running Vite server. Run
`node tests/auth-browser.mjs` from frontend when Playwright is installed locally,
or set `PLAYWRIGHT_MODULE` to an installed Playwright `index.mjs` absolute path.
`FRONTEND_URL` defaults to `http://127.0.0.1:5173`.

The browser script intercepts all authentication API requests. It checks required
fields, invalid email, whitespace name, password length/number/symbol rules,
confirmation, requirement indicators, navigation, loading, errors/retry,
registration reset, success messages, and overflow at 375/768/1440 pixels.

## Why the proxy fails

Vite forwards `/api` to `http://localhost:8000`. Nothing was listening there,
confirmed outside the sandbox. Current system Python also has no Django installed.

Docker Compose does not publish the backend's port 8000 to the host. Dockerfile
`EXPOSE 8000` alone does not make it reachable from host Vite. The container
entrypoint calls `daphne`, which is missing from `backend/requirements.txt`.
These need the backend owner's attention; backend files were not changed.

## Start Django locally

These are instructions, not commands executed during this review. From the
repository root, copy `.env.example` to `.env` only if `.env` does not already
exist, then replace the example Django secret with a development secret.

```sh
python3 -m venv /tmp/careflow-venv
. /tmp/careflow-venv/bin/activate
python -m pip install -r backend/requirements.txt
cd backend
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Current Django settings use SQLite, despite the PostgreSQL environment variables
and Compose service. `runserver` avoids the Docker Daphne entrypoint. If dependency
installation fails, ask the backend owner to check the pinned requirements.

## Real authentication is blocked

Starting Django alone is insufficient. `accounts/views.py` and `accounts/models.py`
are placeholders. Django routes include only admin and collaboration endpoints.
None of the expected authentication routes exist:

- `GET /api/auth/csrf/`
- `POST /api/auth/register/` with `{name, email, password}`
- `POST /api/auth/login/` with `{email, password}`
- `GET /api/auth/me/`

The frontend expects JSON responses, session cookies, and a CSRF token in JSON
(`csrfToken` or `csrf_token`) or a `csrftoken` cookie. Confirm that contract with
the backend owner. Backend must enforce password policy and administrator approval;
the frontend messages do not enforce those server rules. Keep CSRF enabled.

Once the endpoints exist and the server is reachable, test with disposable accounts:
registration/persistence, duplicate email, pending account rejection, administrator
approval, approved login, incorrect password, actual CSRF enforcement, and session
persistence through `/me/`.

Only Login and Register routes exist. Login currently shows a success message;
there is no dashboard destination. Privacy/terms links have no matching pages.
Production hosting must route `/api` to Django separately; the Vite proxy is for
development.

## Results from this review

- PASS: production build (`npm run build`).
- PASS: all nine API tests (`npm test`).
- PASS: Chromium browser script, including validation, navigation, loading,
  simulated success/failure and retry, and widths 375/768/1440; no runtime errors.
- BLOCKED: real Django registration/login, database persistence, approval,
  server-side password validation, session persistence, and actual CSRF enforcement.

Playwright and Chromium were downloaded as temporary testing tools without
changing frontend dependencies or the lockfile. The system dependency installer
required a sudo password and could not run. The two missing libraries (NSPR/NSS)
were downloaded and extracted into `/tmp/careflow-browser-libs` instead. The
browser check passed with `LD_LIBRARY_PATH` pointing to that directory.

Files changed during this review: frontend package test command, App root redirect,
Login/Register loading guards and busy accessibility state, Register fallback
error, API response/network error handling, the two test scripts, and this guide.
Existing CSS and Vite proxy changes were already present and were preserved.
