FROM python:3.12-slim-bookworm AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

RUN rm -f /etc/apt/sources.list.d/*

RUN echo "deb http://mirrors.aliyun.com/debian/ bookworm main contrib non-free" > /etc/apt/sources.list.d/aliyun.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list.d/aliyun.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list.d/aliyun.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install uv --no-cache-dir && uv --version
ENV UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

ENV HANLP_HOME=/app/.hanlp
RUN python -c "import hanlp; hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)"

COPY . .

ENV PYTHONUNBUFFERED=1

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-2}
