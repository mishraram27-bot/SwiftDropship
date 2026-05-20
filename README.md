# SwiftDropship

SwiftDropship is a Flask-based ecommerce application (server-rendered templates + SQLite).

## Run locally

1. Create a Python 3.11+ environment
2. Install dependencies from `pyproject.toml`
3. Run:

```bash
python app.py
```

The app starts on `http://localhost:5000`.

## Production entrypoint

Use `gunicorn wsgi:app` for production hosts such as Render, Railway, Fly.io, or a VPS.

Set `APP_BASE_URL` to the public site URL so email links and checkout redirects stay correct.
