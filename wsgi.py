"""
WSGI entrypoint for Gunicorn.
Exposes the Flask server object that Gunicorn needs.
"""

from app.app import server

if __name__ == "__main__":
    server.run()
