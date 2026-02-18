# statsmed web app – production image for use behind Caddy
FROM python:3.12-slim

WORKDIR /app

# Install package + web extras and gunicorn
COPY pyproject.toml .
COPY statsmed ./statsmed
COPY web ./web
COPY wsgi.py .

RUN pip install --no-cache-dir -e ".[web]" gunicorn

EXPOSE 5000

# Production server; Caddy reverse-proxies to this port
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "wsgi:application"]
