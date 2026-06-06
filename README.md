# chinese-entity-service

中文实体提取服务，支持三种可替换后端。统一 API 接口，切换后端无需修改调用代码。

## 后端对比

| | LAC | HanLP | spaCy |
|--|-----|-------|-------|
| 效果 | 一般 | 好 | 一般 |
| 推理延迟 | ~5ms | ~100ms | ~20ms |
| 内存（单进程） | ~300MB | ~1.5GB | ~400MB |
| 推荐场景 | 高并发、低成本 | 效果优先 | 英中混合 |

**推荐：HanLP**，效果最好，100ms 可与向量检索并行执行不影响总延迟。

## 本地对比测试

```bash
docker-compose up --build
```

- LAC：http://localhost:8001
- HanLP：http://localhost:8002
- spaCy：http://localhost:8003

## 各服务文档

- [lac/README.md](lac/README.md)
- [hanlp/README.md](hanlp/README.md)
- [spacy/README.md](spacy/README.md)

## 过滤逻辑

各服务内置 `filters.py`，负责标签归一化与泛化词过滤。修改过滤逻辑时需同步更新三个服务目录中的文件。
