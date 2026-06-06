from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from filters import filter_entities

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_BATCH = int(os.getenv("MAX_BATCH", "64"))
MAX_TEXT_LEN = int(os.getenv("MAX_TEXT_LEN", "2000"))

_ner = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _ner
    logger.info("Loading HanLP model...")
    try:
        import hanlp
        _ner = hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)
        logger.info("HanLP model loaded")
    except Exception:
        logger.exception("Failed to load HanLP model")
        raise
    yield
    logger.info("Shutting down")


app = FastAPI(title="chinese-entity-service (HanLP)", lifespan=lifespan)


class ExtractRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=MAX_BATCH)
    types: Optional[list[str]] = None


class ExtractResponse(BaseModel):
    entities: list[list[str]]


@app.get("/health")
def health():
    if _ner is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return {"status": "ok", "model": "hanlp"}


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    if _ner is None:
        raise HTTPException(status_code=503, detail="Model not ready")

    texts = [t[:MAX_TEXT_LEN] for t in req.texts]

    try:
        # HanLP NER: results[i] = [(text, tag, start, end), ...]
        results = _ner(texts)
        entities = []
        for sent_entities in results:
            tagged = [(text, tag) for text, tag, *_ in sent_entities]
            entities.append(filter_entities(tagged, req.types))
        return ExtractResponse(entities=entities)
    except Exception:
        logger.exception("Extraction failed")
        raise HTTPException(status_code=500, detail="Extraction failed")
