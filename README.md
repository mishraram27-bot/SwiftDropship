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

## GitHub Pages

This repository includes a GitHub Pages workflow that publishes static content from `docs/`.

Important: GitHub Pages does not run Python/Flask processes, so the full dynamic app (auth, cart, checkout, admin, DB) must be deployed on a Python host.
