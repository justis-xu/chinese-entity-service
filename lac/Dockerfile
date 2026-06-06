FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 依赖先装，利用 Docker 层缓存
COPY lac/requirements.txt ./lac/requirements.txt
RUN uv pip install --system --no-cache -r lac/requirements.txt

# 构建时预下载模型，避免运行时下载失败
RUN python -c "from LAC import LAC; LAC(mode='lac')"

COPY shared/ ./shared/
COPY lac/main.py ./main.py

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
