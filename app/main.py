"""FastAPI entrypoint. Phase 1 vertical slice: API -> normalize -> dedup -> MySQL -> filter."""

import logging

from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Base, engine, get_db
from app.middleware import RequestContextMiddleware, RateLimitMiddleware, require_api_key
from app.schemas import JobOut, SearchRequest, MatchRequest, MatchedJobOut
from app.services.job_api_adapter import get_adapter
from app.services.normalize import normalize_job
from app.services.dedup import upsert_job
from app.services.filters import apply_hard_filters
from app.models import Job

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("careeros")
settings = get_settings()

app = FastAPI(title="CareerOS", version="0.2.0")

app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)
app.add_middleware(RequestContextMiddleware)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs/search", response_model=list[JobOut], dependencies=[Depends(require_api_key)])
async def search_jobs(req: SearchRequest, db: Session = Depends(get_db)):
    """Discover -> Normalize -> Dedup -> Filter. Ranking/matching/LLM layers are Phase 2+."""
    adapter = get_adapter()
    raw_postings = await adapter.search(req.query, req.location)
    logger.info("search fetched=%d query=%s", len(raw_postings), req.query)

    for raw in raw_postings:
        normalized = normalize_job(raw)
        _, created = upsert_job(db, normalized)
        if created:
            logger.info("job inserted source=%s source_id=%s", normalized.source, normalized.source_id)

    all_jobs = db.execute(select(Job)).scalars().all()
    filtered = apply_hard_filters(all_jobs, req)
    return filtered


@app.get("/jobs/{job_id}", response_model=JobOut, dependencies=[Depends(require_api_key)])
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="job not found")
    return job


@app.post("/jobs/match", response_model=list[MatchedJobOut], dependencies=[Depends(require_api_key)])
async def match_jobs(req: MatchRequest, db: Session = Depends(get_db)):
    """Full pipeline (spec section 4): discover -> normalize -> dedup -> filter
    -> hybrid retrieve -> rerank -> evidence-based explain. Stops before human
    review — nothing here marks anything as applied without a separate approval call.
    """
    from app.graph import run_match_workflow

    thread_id = f"match-{id(req)}"
    ranked = await run_match_workflow(db, req, thread_id)

    out = []
    for entry in ranked:
        job = db.get(Job, entry["job_id"])
        if not job:
            continue
        out.append(
            MatchedJobOut(
                job=JobOut.model_validate(job),
                keyword_score=entry["keyword_score"],
                semantic_score=entry["semantic_score"],
                hybrid_score=entry["hybrid_score"],
                matched_skills=entry.get("matched_skills", []),
                missing_skills=entry.get("missing_skills", []),
                explanation=entry.get("explanation", "unknown"),
                confidence=entry.get("confidence", 0.0),
            )
        )
    return out


@app.post("/jobs/{job_id}/verify", response_model=JobOut, dependencies=[Depends(require_api_key)])
async def verify_job(job_id: str, db: Session = Depends(get_db)):
    """Firecrawl-backed verification pass. Sets verified=True only on a positive
    confirmed result — reachability alone is not enough (spec 2.3: never guess)."""
    from fastapi import HTTPException
    from datetime import datetime, timezone
    from app.services.verification import verify_job_posting

    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")

    result = await verify_job_posting(job.apply_url, job.title, job.company)
    job.verified = result.verified
    job.verified_at = datetime.now(timezone.utc) if result.verified else job.verified_at
    if not result.verified and ("closed" in result.reason.lower() or "filled" in result.reason.lower()):
        job.is_active = False
    db.commit()
    db.refresh(job)
    return job

