"""WSGI entry point for gunicorn."""
from web.app import create_app

application = create_app()
