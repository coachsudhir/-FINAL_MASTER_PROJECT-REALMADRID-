"""
WSGI entrypoint for Gunicorn.

Deploys the canonical dashboard app, which lives in dashboard/app. We put the
dashboard/ directory on sys.path so `from app.app import server` resolves to
dashboard/app/app.py (that module then adds dashboard/app to the path for its
own internal `config`/`utils`/`pages` imports).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard"))

from app.app import server

if __name__ == "__main__":
    server.run()
