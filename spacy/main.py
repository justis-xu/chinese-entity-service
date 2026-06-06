from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, "/app")
from shared.filters import filter_entities

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_BATCH = 64
MAX_TEXT_LEN = 2000

_nlp = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _nlp
    logger.info("Loading spaCy model...")
    try:
        import spacy
        _nlp = spacy.load("zh_core_web_sm")
        logger.info("spaCy model loaded")
    except Exception:
        logger.exception("Failed to load spaCy model")
        raise
    yield
    logger.info("Shutting down")


app = FastAPI(title="chinese-entity-service (spaCy)", lifespan=lifespan)


class ExtractRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1, max_length=MAX_BATCH)
    types: Optional[list[str]] = None


class ExtractResponse(BaseModel):
    entities: list[list[str]]


@app.get("/health")
def health():
    if _nlp is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return {"status": "ok", "model": "spacy"}


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    if _nlp is None:
        raise HTTPException(status_code=503, detail="Model not ready")

    texts = [t[:MAX_TEXT_LEN] for t in req.texts]

    try:
        entities = []
        for doc in _nlp.pipe(texts, batch_size=MAX_BATCH):
            tagged = [(ent.text, ent.label_) for ent in doc.ents]
            entities.append(filter_entities(tagged, req.types))
        return ExtractResponse(entities=entities)
    except Exception:
        logger.exception("Extraction failed")
        raise HTTPException(status_code=500, detail="Extraction failed")
