FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# 构建时预下载模型，避免运行时下载
RUN python -c "from LAC import LAC; LAC(mode='lac')"

ENV PYTHONUNBUFFERED=1
ENV WORKERS=2
ENV PORT=8000

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers $WORKERS
