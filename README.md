# chinese-entity-service

中文实体提取服务，支持三种可替换后端（LAC、HanLP、spaCy）。统一 API 接口，切换后端无需修改调用代码。

## 后端对比

| | LAC | HanLP | spaCy |
|--|-----|-------|-------|
| 效果 | 一般 | 好 | 一般 |
| 推理延迟 | ~5ms | ~100ms | ~20ms |
| 单 worker 内存 | ~300MB | ~1.5GB | ~400MB |
| 推荐 worker 数 | 4 | 2 | 4 |
| 推荐场景 | 高并发、低成本 | 效果优先 | 英中混合 |

**推荐：HanLP**，效果最好，100ms 延迟可与向量检索（~200ms）并行，不在关键路径上。

## 接口

所有后端接口完全一致，切换服务地址即可。

### POST /extract

```
POST /extract
Content-Type: application/json

{
  "texts": ["李明在北京参加了阿里巴巴的发布会"],
  "types": ["PER", "LOC", "ORG"]   // 可选，不传返回全部类型
}
```

```json
{
  "entities": [["李明", "北京", "阿里巴巴"]]
}
```

支持的实体类型：

| 类型 | 含义 | 示例 |
|------|------|------|
| PER | 人名 | 李明、张三 |
| LOC | 地名 | 北京、上海、中关村 |
| ORG | 机构名 | 阿里巴巴、清华大学 |
| TIME | 时间 | 明天、2024年、三月份 |

### GET /health

```json
{"status": "ok", "model": "hanlp"}
```

模型未加载完成返回 `503`，可作为部署平台健康检查路径。

## 部署资源

| | LAC | HanLP | spaCy |
|--|-----|-------|-------|
| CPU | 4 核 | 4 核 | 4 核 |
| 内存 | 2GB | 8GB | 2GB |
| 磁盘 | 1GB | 3GB | 1GB |
| 推荐 workers | 4 | 2 | 4 |

## 启动命令

```bash
# LAC / spaCy（4 workers，充分利用 4 核）
cd /models/<挂载路径> && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# HanLP（2 workers，内存限制）
cd /models/<挂载路径> && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_BATCH` | `64` | 单次请求最多文本条数 |
| `MAX_TEXT_LEN` | `2000` | 单条文本最大字符数，超出自动截断 |
| `INFER_TIMEOUT` | `5.0` | 等待推理锁超时秒数，超出返回 429（HanLP 默认 10.0） |

## 稳定性说明

- **模型预热**：服务启动时自动执行一次空推理，消除首请求延迟
- **并发安全**：每个 worker 进程内部通过 Semaphore 串行推理，避免线程竞争
- **限流保护**：并发超出时返回 429，而非无限等待导致雪崩
- **健康检查**：模型加载完成前 `/health` 返回 503，平台不会提前转入流量

## 本地对比测试

```bash
docker-compose up --build
# LAC：http://localhost:8001
# HanLP：http://localhost:8002
# spaCy：http://localhost:8003

# 运行测试脚本
python test.py --url http://localhost:8001
python test.py --url http://localhost:8002 --concurrent 10
```

## 仓库结构

```
├── lac/           # LAC 服务
│   ├── Dockerfile.base   # CI 构建基础镜像
│   ├── Dockerfile        # 本地开发
│   ├── main.py
│   ├── filters.py
│   ├── requirements.txt
│   └── README.md
├── hanlp/         # HanLP 服务（同上）
├── spacy/         # spaCy 服务（同上）
├── docker-compose.yml    # 本地一键启动
└── test.py               # 验证脚本
```

## 过滤逻辑

各服务内置 `filters.py`，负责将各模型原始标签归一化为统一类型（PER/LOC/ORG/TIME），并过滤泛化词。修改过滤逻辑时需同步更新三个服务目录中的文件。
