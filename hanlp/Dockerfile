FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

ENV HANLP_HOME=/app/.hanlp
RUN python -c "import hanlp; hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)"
