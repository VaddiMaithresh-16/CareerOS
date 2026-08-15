"""Gradio V1 UI (spec 3.6). Thin client over FastAPI — no business logic here."""

import os
import httpx
import gradio as gr

API_BASE = os.getenv("CAREEROS_API_BASE", "http://127.0.0.1:8000")
API_KEY = os.getenv("CAREEROS_API_KEY", "").strip()

DEFAULT_LOCATION = "Hyderabad, India"
EMPLOYMENT_TYPES = ["", "full_time", "part_time", "internship", "contract", "temporary"]
EXPERIENCE_LEVELS = ["", "intern", "fresher", "entry", "mid", "senior"]

# Display salary as monthly INR (API stores annual)
MONTHS_PER_YEAR = 12


def _auth_headers() -> dict:
    if API_KEY:
        return {"X-API-Key": API_KEY}
    return {}


def _format_monthly_inr(salary_min: float | None, salary_max: float | None, currency: str) -> str:
    """Convert annual salary to monthly INR for display."""
    if salary_min is None or salary_max is None:
        return "unknown"
    # Convert to monthly
    monthly_min = salary_min / MONTHS_PER_YEAR
    monthly_max = salary_max / MONTHS_PER_YEAR
    # Format with Indian numbering (lakhs/crores) or standard
    def fmt(val: float) -> str:
        if val >= 1_00_00_000:  # 1 crore
            return f"₹{val/1_00_00_000:.2f} Cr"
        if val >= 1_00_000:  # 1 lakh
            return f"₹{val/1_00_000:.2f} L"
        return f"₹{val:,.0f}"
    return f"{fmt(monthly_min)} - {fmt(monthly_max)} / month"


def search(
    query: str,
    location: str,
    remote_only: bool,
    employment_type: str,
    experience_level: str,
    min_salary_monthly: float,
    posted_within_days: int,
):
    if not query.strip():
        return "Enter a role/query first."

    # Convert monthly min_salary to annual for API (API expects annual)
    min_salary_annual = min_salary_monthly * MONTHS_PER_YEAR if min_salary_monthly > 0 else None

    payload = {
        "query": query,
        "location": location or None,
        "remote_only": remote_only,
        "employment_type": employment_type or None,
        "experience_level": experience_level or None,
        "min_salary": min_salary_annual,
        "posted_within_days": posted_within_days if posted_within_days > 0 else None,
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        resp = httpx.post(f"{API_BASE}/jobs/search", json=payload, headers=_auth_headers(), timeout=30.0)
        resp.raise_for_status()
        jobs = resp.json()
    except httpx.HTTPError as e:
        return f"Search failed: {e}"

    if not jobs:
        return "No jobs matched hard filters."

    rows = []
    for j in jobs:
        salary = _format_monthly_inr(j["salary_min"], j["salary_max"], j["salary_currency"])
        rows.append(
            f"### {j['title']} — {j['company']}\n"
            f"- Location: {j['location_normalized']} ({j['remote']})\n"
            f"- Type: {j['employment_type']}\n"
            f"- Experience: {j['experience_level']}\n"
            f"- Salary: {salary}\n"
            f"- Verified: {j['verified']}\n"
            f"- Apply: {j['apply_url']}\n"
        )
    return "\n---\n".join(rows)


with gr.Blocks(title="CareerOS") as demo:
    gr.Markdown("# CareerOS — Job Search")
    with gr.Row():
        query = gr.Textbox(label="Role / query", placeholder="e.g. backend engineer")
    with gr.Row():
        location = gr.Textbox(label="Location", value=DEFAULT_LOCATION, placeholder="e.g. Hyderabad, India")
        remote_only = gr.Checkbox(label="Remote only", value=False)
    with gr.Row():
        employment_type = gr.Dropdown(label="Employment Type", choices=EMPLOYMENT_TYPES, value="", allow_custom_value=True)
        experience_level = gr.Dropdown(label="Experience Level", choices=EXPERIENCE_LEVELS, value="", allow_custom_value=True)
    with gr.Row():
        min_salary = gr.Number(label="Minimum Salary (monthly, ₹)", value=0, precision=0)
        posted_within_days = gr.Number(label="Posted Within (days)", value=0, precision=0)
    btn = gr.Button("Search", variant="primary")
    output = gr.Markdown()
    btn.click(
        fn=search,
        inputs=[query, location, remote_only, employment_type, experience_level, min_salary, posted_within_days],
        outputs=output,
    )

if __name__ == "__main__":
    demo.launch()
