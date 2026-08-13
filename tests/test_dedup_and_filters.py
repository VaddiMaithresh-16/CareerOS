import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.schemas import RawJobPosting, SearchRequest
from app.services.normalize import normalize_job
from app.services.dedup import upsert_job
from app.services.filters import apply_hard_filters


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _raw(source_id="1", url="https://acme.com/jobs/1", title="Backend Engineer"):
    return RawJobPosting(
        source="mock",
        source_id=source_id,
        title=title,
        company="Acme",
        location_raw="Remote",
        employment_type_raw="Full-time",
        description="desc",
        apply_url=url,
        posted_at_raw="2026-08-01",
        salary_raw="$80,000 - $100,000",
    )


def test_upsert_creates_new_job(db_session):
    job = normalize_job(_raw())
    row, created = upsert_job(db_session, job)
    assert created is True
    assert row.title == "Backend Engineer"


def test_upsert_dedupes_same_url(db_session):
    job1 = normalize_job(_raw(url="https://acme.com/jobs/1?utm=a"))
    job2 = normalize_job(_raw(url="https://acme.com/jobs/1?utm=b"))
    _, created1 = upsert_job(db_session, job1)
    _, created2 = upsert_job(db_session, job2)
    assert created1 is True
    assert created2 is False  # same URL after normalization -> dedup


def test_upsert_dedupes_same_content_different_url(db_session):
    job1 = normalize_job(_raw(source_id="1", url="https://boardA.com/jobs/1"))
    job2 = normalize_job(_raw(source_id="2", url="https://boardB.com/jobs/1"))
    _, created1 = upsert_job(db_session, job1)
    _, created2 = upsert_job(db_session, job2)
    assert created1 is True
    assert created2 is False  # same title+company+location -> content dedup


def test_hard_filter_remote_only(db_session):
    job = normalize_job(_raw())
    row, _ = upsert_job(db_session, job)
    row.remote = "onsite"
    db_session.commit()

    req = SearchRequest(query="backend", remote_only=True)
    result = apply_hard_filters([row], req)
    assert result == []


def test_hard_filter_min_salary_excludes_below(db_session):
    job = normalize_job(_raw())
    row, _ = upsert_job(db_session, job)  # salary_max = 100000

    req = SearchRequest(query="backend", min_salary=200000)
    assert apply_hard_filters([row], req) == []

    req_ok = SearchRequest(query="backend", min_salary=50000)
    assert apply_hard_filters([row], req_ok) == [row]


def test_hard_filter_unknown_salary_not_excluded(db_session):
    job = normalize_job(_raw())
    row, _ = upsert_job(db_session, job)
    row.salary_min = None
    row.salary_max = None
    db_session.commit()

    req = SearchRequest(query="backend", min_salary=200000)
    assert apply_hard_filters([row], req) == [row]  # unknown != ineligible, spec 2.3


def test_hard_filter_experience_level(db_session):
    job = normalize_job(_raw(title="Backend Intern"))
    row, _ = upsert_job(db_session, job)

    req_match = SearchRequest(query="backend", experience_level="intern")
    assert apply_hard_filters([row], req_match) == [row]

    req_miss = SearchRequest(query="backend", experience_level="senior")
    assert apply_hard_filters([row], req_miss) == []


def test_hard_filter_posted_within_days(db_session):
    import datetime as dt

    job = normalize_job(_raw())
    row, _ = upsert_job(db_session, job)
    row.posted_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=40)
    db_session.commit()

    req_recent = SearchRequest(query="backend", posted_within_days=7)
    assert apply_hard_filters([row], req_recent) == []

    req_wide = SearchRequest(query="backend", posted_within_days=60)
    assert apply_hard_filters([row], req_wide) == [row]
