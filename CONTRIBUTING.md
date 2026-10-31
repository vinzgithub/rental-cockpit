# Contributing

🇫🇷 Les contributions et discussions en français sont bienvenues.

Thank you for your interest. Rental Cockpit is in preview and its licence is not decided yet, so contributions are discussed in issues before any pull request.

## Golden rule: no real data

Never put real data in an issue, a pull request, a test or a screenshot: no real invoice, no guest name, no booking reference, no address, no database file, no token or password. Use the built-in fictional demo, or synthetic files clearly labelled as such.

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
RENTAL_COCKPIT_DATA_DIR=./data uvicorn --factory rental_cockpit.app:create_app --reload --port 8080
```

- The business rules live in `src/rental_cockpit/engine/` and must stay plain Python, testable without the web layer.
- Every calculation rule comes with a test; every new API route checks rights on the server and is used by the interface (see `tests/test_app.py`).
- Interface texts exist in French and English (`static/js/i18n.js`); no technical code is ever shown to users.
- No inline script or style: the Content-Security-Policy forbids them.
- Run `python scripts/check_public_data.py` before committing.

## Support

Questions and bug reports go to GitHub issues. Security problems go to private reporting (see [SECURITY.md](SECURITY.md)).
