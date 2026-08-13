"""Hard eligibility filters. Pure Python/logic. LLMs must never override these (spec 2.1)."""

from datetime import datetime, timezone, timedelta

from app.models import Job
from app.schemas import SearchRequest


def passes_hard_filters(job: Job, req: SearchRequest) -> bool:
    if not job.is_active:
        return False

    if req.employment_type and req.employment_type != "unknown":
        if job.employment_type != req.employment_type:
            return False

    if req.experience_level and req.experience_level != "unknown":
        if job.experience_level != req.experience_level:
            return False

    if req.remote_only and job.remote != "remote":
        return False

    if req.location:
        loc = req.location.lower()
        if loc not in job.location_normalized.lower() and job.remote != "remote":
            return False

    if req.min_salary is not None:
        # unknown salary is not excluded — unknown != ineligible (spec 2.3), just unscored on this axis
        if job.salary_max is not None and job.salary_max < req.min_salary:
            return False

    if req.posted_within_days is not None and job.posted_at is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=req.posted_within_days)
        posted = job.posted_at if job.posted_at.tzinfo else job.posted_at.replace(tzinfo=timezone.utc)
        if posted < cutoff:
            return False
        # posted_at unknown (None) is not excluded — same unknown != ineligible rule

    return True


def apply_hard_filters(jobs: list[Job], req: SearchRequest) -> list[Job]:
    return [j for j in jobs if passes_hard_filters(j, req)]
