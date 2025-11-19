# Webstore (BitRealm Games)

A small Flask-based e-commerce demo webstore with PWA support, offline caching, and an admin/seller interface. This repository contains the app code, templates, static assets (CSS/JS/images), and a service worker for offline support.

## Features

- Flask backend with SQLite database
- Bootstrap 5 frontend with responsive templates
- Product listing/detail pages, cart, checkout flow
- Admin and seller views (basic CRUD UI)
- Progressive Web App (PWA) support with `static/manifest.json` and `static/sw.js`
- Offline-friendly: product pages and static assets cached by the service worker
- Password strength UI on registration (client-side) and server-side password validation
- Custom site logo and raster favicons (PNG/ICO) under `static/img/favicon/`

## Project structure (important files)

- `app.py` — Flask application and routes
- `setup_db.py` — initializes the SQLite DB (sample schema)
- `requirements.txt` — Python dependencies
- `templates/` — Jinja2 templates (pages and partials)
- `static/` — static assets (CSS, JS, images, `manifest.json`, `sw.js`)
  - `static/img/logo.svg` — site logo
  - `static/img/favicon/` — generated PNG/ICO favicons
- `templates/register.html` — registration page with password strength UI
- `static/js/password_strength.js` — client-side password strength logic

## Quick start (Windows / PowerShell)

1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

2. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Initialize the database (if required)

```powershell
python setup_db.py
```

4. Run the app (development)

```powershell
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
flask run --host=0.0.0.0 --port=5000
```

Alternatively run directly with Python if `app.py` calls `app.run()` when executed.

## PWA / Service Worker notes

- The PWA manifest is at `static/manifest.json` and the service worker at `static/sw.js`.
- Browsers and OS may cache icons and service workers. If you've updated icons or the SW and don't see changes:
  - Open DevTools → Application (Chrome) / Storage (Firefox)
  - Under Service Workers, click `Unregister` for this site
  - Clear site data (Application → Clear storage)
  - Reload the page and re-install the PWA (if needed)

This project includes raster PNG icons and a multi-size `.ico` under `static/img/favicon/` to improve OS-level icon support for shortcuts and installations.

## Regenerating icons (notes)

If you want to recreate the PNG/ICO favicons from the SVG logo, you can use Python + Pillow. Example outline:

1. Ensure Pillow is installed

```powershell
pip install pillow
```

2. Run a small Python script that loads `static/img/logo.svg` (or draws the logo) and saves PNGs at multiple sizes (16, 32, 48, 128, 192, 512) and an ICO containing common sizes.

(There is no committed icon-generation script in the repo; if you want, I can add a `scripts/generate_icons.py` file that does this using Pillow.)

## Development notes & tips

- To force clients to pick up a changed service worker, update the SW `CACHE_NAME` constant (version bump) in `static/sw.js` and redeploy. Users still may need to unregister or reload to pick up changes.
- The registration page applies client-side password quality hints in `static/js/password_strength.js` and server-side enforcement in `app.py`. Adjust validation rules there as needed (length, complexity, and blacklist checks).
- Static assets and templates live in `static/` and `templates/`. Keep layout partials in `templates/` (e.g., `head_includes.html`, `footer.html`) for shared markup.

## Tests / CI

No tests or CI workflow are included by default. Recommended next steps:

- Add unit tests (pytest) for key routes and auth flows
- Add a GitHub Actions workflow to run tests on push/PR

## Contributing

Open an issue or PR for bugfixes, improvements, or feature requests. If you want me to add CSRF protection, Content Security Policy headers, or a CI workflow, tell me which you'd prefer next and I can implement it.

## License

This repository contains example/demo code — add your license file here if you have one.

---

If you'd like, I can also add a small `scripts/generate_icons.py` to automate PNG/ICO generation, or add a `README` section for running the Lighthouse audit and recommended lighthouse settings. Want me to add the icon-generator script now?