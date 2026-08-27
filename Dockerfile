FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV RACE_HOST=0.0.0.0
ENV RACE_PORT=8000

WORKDIR /app

COPY server.py README.md ./
COPY static ./static

RUN useradd --create-home --shell /usr/sbin/nologin raceapp \
    && mkdir -p /app/data /app/static/videos \
    && chown -R raceapp:raceapp /app

USER raceapp

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2).read()"

CMD ["python", "server.py"]
