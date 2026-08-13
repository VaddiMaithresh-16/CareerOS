from app.schemas import RawJobPosting
from app.services.normalize import (
    normalize_job,
    normalize_url,
    parse_location,
    parse_employment_type,
    parse_salary,
)


def test_normalize_url_strips_tracking_params():
    a = normalize_url("https://Example.com/jobs/1?utm_source=x&ref=y")
    b = normalize_url("https://example.com/jobs/1")
    assert a == b


def test_parse_location_remote():
    loc, remote = parse_location("Remote (India)")
    assert remote == "remote"


def test_parse_location_unknown_when_empty():
    loc, remote = parse_location("")
    assert loc == "unknown"
    assert remote == "unknown"


def test_parse_employment_type_known():
    assert parse_employment_type("Full-Time") == "full_time"
    assert parse_employment_type("Internship") == "internship"


def test_parse_employment_type_unknown_never_guessed():
    assert parse_employment_type("Freelance-ish gig") == "unknown"


def test_parse_experience_level_intern():
    from app.services.normalize import parse_experience_level

    assert parse_experience_level("Software Intern", "") == "intern"


def test_parse_experience_level_fresher():
    from app.services.normalize import parse_experience_level

    assert parse_experience_level("Fresher - Backend Developer", "") == "fresher"


def test_parse_experience_level_senior():
    from app.services.normalize import parse_experience_level

    assert parse_experience_level("Senior Backend Engineer", "") == "senior"


def test_parse_experience_level_unknown_when_no_marker():
    from app.services.normalize import parse_experience_level

    assert parse_experience_level("Backend Engineer", "Build things with Python.") == "unknown"


def test_parse_salary_range():
    lo, hi, cur = parse_salary("₹8,00,000 - ₹12,00,000")
    assert lo == 800000
    assert hi == 1200000
    assert cur == "INR"


def test_parse_salary_none_when_missing():
    lo, hi, cur = parse_salary(None)
    assert lo is None and hi is None and cur == "unknown"


def test_normalize_job_end_to_end():
    raw = RawJobPosting(
        source="mock",
        source_id="1",
        title="  Backend Engineer  ",
        company="Acme",
        location_raw="Hybrid - Hyderabad",
        employment_type_raw="Full-time",
        description="desc",
        apply_url="https://acme.com/jobs/1?utm=x",
        posted_at_raw="2026-08-01",
        salary_raw="$80,000 - $100,000",
    )
    job = normalize_job(raw)
    assert job.title == "Backend Engineer"
    assert job.remote == "hybrid"
    assert job.employment_type == "full_time"
    assert job.salary_currency == "USD"
    assert job.url_hash and job.content_hash
