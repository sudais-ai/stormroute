"""
Concrete app/type detection for the stormroute package.

Loads gitignored `backend/.env` (if present) into os.environ via python-dotenv
so any entry point (manage.py, shell, tests, WSGI/ASGI) sees real secrets.
The file stays optional: in CI/deployment values come from real environment
variables and `.env` may not exist.
"""

from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent

load_dotenv(_BACKEND_DIR / ".env")
