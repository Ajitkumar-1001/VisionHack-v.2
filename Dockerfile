# Cloud Run container contract (PRD §19): binds 0.0.0.0, reads $PORT, stateless,
# no reliance on local persistent storage. One service — FastAPI, engine and the
# static UI all ship in this image (§19 bans a separate frontend deployment).
FROM python:3.12-slim

WORKDIR /app

# Dependencies before source so an edit to app/ doesn't re-run pip.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/app/
COPY config/ /app/config/

# Overridden by Cloud Run at runtime; 8080 is the local default.
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

CMD exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
