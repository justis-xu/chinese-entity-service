# chinese-entity-service / LAC

基于百度 LAC 的中文实体提取服务。

## 部署资源要求

| 资源 | 最低 | 推荐 |
|------|------|------|
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 2 GB |
| 磁盘 | 500 MB | 1 GB |

- 推理延迟：~5ms（短文本）
- 默认 2 个 worker 进程，并发无状态共享问题

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_BATCH` | `64` | 单次请求最多文本条数 |
| `MAX_TEXT_LEN` | `2000` | 单条文本最大字符数，超出自动截断 |
| `WORKERS` | `2` | uvicorn worker 进程数，建议不超过 CPU 核数 |
| `PORT` | `8000` | 监听端口 |

## 部署命令

### 构建镜像

```bash
docker build -t chinese-entity-lac .
```

### 启动容器

```bash
docker run -d \
  --name entity-lac \
  -p 8000:8000 \
  --memory=2g \
  --restart=unless-stopped \
  -e WORKERS=2 \
  -e MAX_BATCH=64 \
  -e MAX_TEXT_LEN=2000 \
  chinese-entity-lac
```

### 调整端口

```bash
docker run -d \
  --name entity-lac \
  -p 9000:8000 \       # 宿主机 9000 → 容器 8000
  --memory=2g \
  --restart=unless-stopped \
  chinese-entity-lac
```

### 查看日志

```bash
docker logs -f entity-lac
```

### 停止 / 删除

```bash
docker stop entity-lac
docker rm entity-lac
```

### 健康检查

```bash
curl http://localhost:8000/health
```

## CMD 说明

Dockerfile 默认启动命令：

```
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

如需修改 worker 数，通过环境变量 `WORKERS` 控制，需在 Dockerfile CMD 中引用，或直接覆盖：

```bash
docker run ... chinese-entity-lac \
  uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
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
{"status": "ok", "model": "lac"}
```

模型未加载完成时返回 `503`。
