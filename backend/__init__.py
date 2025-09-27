"""Backend package initializer.

Expose commonly used symbols for tests and imports:
  from backend import app, init_db, get_db
"""
from .app import app, init_db, get_db
