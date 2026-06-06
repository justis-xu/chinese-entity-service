# chinese-entity-service / HanLP

基于 HanLP BERT 的中文实体提取服务，效果最优。

## 部署资源要求

| 资源 | 最低 | 推荐 |
|------|------|------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 2 GB | 3 GB |

- 推理延迟：~100ms（短文本，CPU）
- 默认 2 个 worker 进程，内存占用约 3GB，建议宿主机至少 4GB 可用内存
- 100ms 延迟可与向量检索（~200ms）并行，不在关键路径上

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_BATCH` | `64` | 单次请求最多文本条数 |
| `MAX_TEXT_LEN` | `2000` | 单条文本最大字符数，超出自动截断 |
| `WORKERS` | `2` | uvicorn worker 进程数，受内存限制，建议不超过 2 |
| `PORT` | `8000` | 监听端口 |
| `HANLP_HOME` | `/app/.hanlp` | 模型存储路径，已在镜像内预置，通常无需修改 |

## 部署命令

### 构建镜像

```bash
# 首次构建会下载 BERT 模型（约 400MB），需要网络
docker build -t chinese-entity-hanlp .
```

### 启动容器

```bash
docker run -d \
  --name entity-hanlp \
  -p 8000:8000 \
  --memory=8g \
  --restart=unless-stopped \
  -e WORKERS=2 \
  -e MAX_BATCH=64 \
  -e MAX_TEXT_LEN=2000 \
  chinese-entity-hanlp
```

### 调整端口

```bash
docker run -d \
  --name entity-hanlp \
  -p 9000:8000 \
  --memory=8g \
  --restart=unless-stopped \
  chinese-entity-hanlp
```

### 查看日志

```bash
docker logs -f entity-hanlp
```

### 停止 / 删除

```bash
docker stop entity-hanlp
docker rm entity-hanlp
```

### 健康检查

```bash
curl http://localhost:8000/health
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
| texts | string[] | 是 | 待提取文本，最多 `MAX_BATCH` 条 |
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
{"status": "ok", "model": "hanlp"}
```

模型未加载完成时返回 `503`。
