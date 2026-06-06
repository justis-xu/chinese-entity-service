FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY spacy/requirements.txt ./spacy/requirements.txt
RUN uv pip install --system --no-cache -r spacy/requirements.txt && \
    python -m spacy download zh_core_web_sm

COPY shared/ ./shared/
COPY spacy/main.py ./main.py

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
