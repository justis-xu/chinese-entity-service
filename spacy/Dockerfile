FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt && \
    python -m spacy download zh_core_web_sm

COPY . .

ENV PYTHONUNBUFFERED=1
ENV WORKERS=2
ENV PORT=8000

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers $WORKERS
