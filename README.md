# chinese-entity-service

中文命名实体识别（NER）服务，提供统一的 HTTP 接口，支持多种模型后端。所有后端接口完全一致，切换只需改服务地址，调用代码无需改动。

## 背景

中文 NER 可用的开源方案很多，但工程可用性差异很大：

- **LAC**（百度）：底层依赖 PaddlePaddle，Python 3.12 不兼容，2021 年后停止维护，**已移除**
- **HanLP**：中文专精，BERT 模型效果好，但 CPU 下延迟 300ms+，内存消耗大，**已移除**（适合有 GPU 的离线批处理场景）
- **spaCy**：Explosion AI 出品，工业界标准 NLP 库，mem0 等主流项目的底层依赖，工程稳定性最佳；`zh_core_web_lg` 在 CPU 下延迟 30-80ms，**生产首选**

**最终选型：spaCy lg**，满足 <200ms 延迟要求，长期维护有商业公司背书。

---

## 后端对比

| | spaCy sm | spaCy lg |
|--|----------|----------|
| 底层模型 | zh_core_web_sm | zh_core_web_lg |
| CPU 推理延迟 | ~10-30ms | ~30-80ms |
| 单 worker 内存 | ~200MB | ~600MB |
| NER 效果 | 一般 | 好 |
| 维护状态 | 商业团队，持续更新 | 同左 |
| 推荐场景 | 高并发低成本 | **在线生产** |

---

## 接口

### POST /extract

提取文本中的命名实体。

**请求**

```json
{
  "texts": ["李明在北京参加了阿里巴巴的发布会", "马云创立了淘宝"],
  "types": ["PER", "LOC", "ORG"]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `texts` | `string[]` | 是 | 待提取文本，最多 `MAX_BATCH` 条 |
| `types` | `string[]` | 否 | 过滤实体类型，不传返回全部类型 |

**响应**

```json
{
  "entities": [
    ["李明", "北京", "阿里巴巴"],
    ["马云", "淘宝"]
  ]
}
```

`entities[i]` 对应 `texts[i]` 提取出的实体列表，顺序与输入一一对应。

**实体类型**

| 类型 | 含义 | 示例 |
|------|------|------|
| `PER` | 人名 | 李明、马云 |
| `LOC` | 地名（含城市、国家、设施） | 北京、中关村 |
| `ORG` | 机构名 | 阿里巴巴、清华大学 |

**错误码**

| 状态码 | 说明 |
|--------|------|
| `429` | 并发请求超出限制，稍后重试 |
| `503` | 模型尚未加载完成 |
| `500` | 推理内部错误 |

---

### GET /health

```json
{"status": "ok", "model": "zh_core_web_lg"}
```

模型加载完成前返回 `503`，可直接作为部署平台的健康检查路径。

---

## 部署

### 资源要求

| | spaCy sm | spaCy lg |
|--|----------|----------|
| 内存（2 workers） | 1GB | 4GB |
| 磁盘 | ~200MB | ~1GB |
| Python 版本 | 3.12 | 3.12 |
| NER 通过率 | ~48% | ~74% |
| 延迟 p95（单条） | ~13ms | ~16ms |
| QPS（10 并发） | ~160 | ~150 |
| >200ms 占比 | <0.1% | <0.1% |

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SPACY_MODEL` | `zh_core_web_lg` | spaCy 模型，可选 `zh_core_web_sm` / `zh_core_web_lg` |
| `MAX_BATCH` | `64` | 单次请求最多文本条数 |
| `MAX_TEXT_LEN` | `2000` | 单条文本最大字符数，超出自动截断 |
| `INFER_TIMEOUT` | `5.0` | 推理锁等待超时（秒），超出返回 429 |
| `WORKERS` | `2` | uvicorn worker 数，每个 worker 独立加载模型，影响内存用量 |

### 本地启动

```bash
docker compose up --build

# spaCy sm：http://localhost:8001
# spaCy lg：http://localhost:8002
```

### 测试与压测

```bash
# 测试单个服务
python test.py --url http://localhost:8002

# 并发压测（默认 5 并发）
python test.py --url http://localhost:8002 --concurrent 10

# 对比所有服务（延迟、效果、p95/p99 一次看完）
python test.py --all
```

---

## 稳定性设计

- **模型预热**：启动时执行一次空推理，消除首请求冷启动延迟
- **并发安全**：每个 worker 进程内通过 Semaphore 串行推理，避免多线程竞争模型实例
- **限流保护**：并发超出时立即返回 429，防止请求积压导致雪崩
- **健康检查**：`/health` 在模型就绪前返回 503，确保平台不会提前导入流量

---

## 仓库结构

```
├── spacy/                # spaCy 服务（sm/lg 共用同一镜像，SPACY_MODEL 环境变量切换）
│   ├── Dockerfile
│   ├── Dockerfile.base
│   ├── main.py
│   ├── filters.py
│   └── requirements.txt
├── lac/                  # 已停用（PaddlePaddle 依赖，Python 3.12 不兼容，2021 年停止维护）
├── docker-compose.yml    # 本地一键启动全部服务
└── test.py               # 功能验证 + 延迟压测脚本
```

## 过滤逻辑

各服务内置 `filters.py`，负责两件事：

1. **标签归一化**：将各模型的原始标签（如 spaCy 的 `PERSON`/`GPE`，HanLP 的 `NR`/`NS`）统一映射为 `PER/LOC/ORG/TIME`
2. **噪声过滤**：去除单字实体和泛化词（如"公司"、"地方"、"用户"等无意义提取结果）

修改过滤逻辑时只需更新 `spacy/filters.py`。
