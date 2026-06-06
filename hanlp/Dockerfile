FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY hanlp/requirements.txt ./hanlp/requirements.txt
RUN uv pip install --system --no-cache -r hanlp/requirements.txt

# 预下载模型到镜像内，运行时无需网络
ENV HANLP_HOME=/app/.hanlp
RUN python -c "import hanlp; hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)"

COPY shared/ ./shared/
COPY hanlp/main.py ./main.py

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
