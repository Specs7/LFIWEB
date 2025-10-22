"""Backend package initializer for LFIWEB.

This file makes `backend` a proper Python package so imports like
`from backend.app import app` work when the project root is on sys.path.
"""

__all__ = ["app"]
"""Backend package initializer.

Expose commonly used symbols for tests and imports:
  from backend import app, init_db, get_db
"""
from .app import app, init_db, get_db
