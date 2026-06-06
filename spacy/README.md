# chinese-entity-service / spaCy

基于 spaCy zh_core_web_sm 的中文实体提取服务。

## 部署资源要求

| 资源 | 最低 | 推荐 |
|------|------|------|
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 2 GB |
| 磁盘 | 500 MB | 1 GB |

- 推理延迟：~20ms（短文本）
- 默认 2 个 worker 进程，并发无状态共享问题
- 中文 NER 效果弱于 HanLP，适合英中混合文本场景

## 构建与启动

```bash
# 单独构建
docker build -t chinese-entity-spacy .

# 单独运行
docker run -p 8000:8000 --memory=2g chinese-entity-spacy
```

## API

### POST /extract

提取实体。

**请求**

```json
{
  "texts": ["李明在北京参加了阿里巴巴的发布会"],
  "types": ["PER", "LOC", "ORG"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| texts | string[] | 是 | 待提取文本，最多 64 条 |
| types | string[] | 否 | 过滤实体类型，不传返回全部 |

支持的类型：

| 类型 | 含义 |
|------|------|
| PER | 人名 |
| LOC | 地名 |
| ORG | 机构名 |
| TIME | 时间 |

**响应**

```json
{
  "entities": [["李明", "北京", "阿里巴巴"]]
}
```

`entities[i]` 对应 `texts[i]` 的实体列表，顺序一一对应。

**错误码**

| 状态码 | 含义 |
|--------|------|
| 422 | 请求参数格式错误 |
| 500 | 推理失败 |
| 503 | 模型未就绪 |

### GET /health

健康检查。

**响应**

```json
{"status": "ok", "model": "spacy"}
```

模型未加载完成时返回 `503`。
