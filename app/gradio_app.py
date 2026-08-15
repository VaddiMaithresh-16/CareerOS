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

PROVIDERS = ["auto", "llama", "gemini", "openrouter", "nvidia", "none"]
PROVIDER_MODELS = {
    "auto": ["(uses config default)"],
    "llama": ["(uses config default)"],
    "gemini": ["gemini-flash-latest", "gemini-pro-latest"],
    "openrouter": [
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3-haiku",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "meta-llama/llama-3.1-70b-instruct",
        "meta-llama/llama-3.1-8b-instruct",
        "google/gemini-flash-1.5",
        "mistralai/mistral-large",
    ],
    "nvidia": [
        "meta/llama-3.1-70b-instruct",
        "meta/llama-3.1-8b-instruct",
        "nvidia/nemotron-3-ultra",
        "nvidia/nemotron-4-340b-instruct",
    ],
    "none": ["(no LLM)"],
}


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
    min_salary: float,
    posted_within_days: int,
    llm_provider: str,
    model_name: str,
):
    if not query.strip():
        return "Enter a role/query first."

    # API expects annual salary
    payload = {
        "query": query,
        "location": location or None,
        "remote_only": remote_only,
        "employment_type": employment_type or None,
        "experience_level": experience_level or None,
        "min_salary": min_salary if min_salary > 0 else None,
        "posted_within_days": posted_within_days if posted_within_days > 0 else None,
        "llm_provider": llm_provider if llm_provider != "auto" else None,
        "model_name": model_name if model_name and model_name != "(uses config default)" and model_name != "(no LLM)" else None,
    }
    payload = {k: v for k, v in payload.items() if v is not None}

    try:
        resp = httpx.post(f"{API_BASE}/jobs/match", json=payload, headers=_auth_headers(), timeout=60.0)
        resp.raise_for_status()
        jobs = resp.json()
    except httpx.HTTPError as e:
        return f"Search failed: {e}"

    if not jobs:
        return "No jobs matched hard filters."

    rows = []
    for j in jobs:
        # MatchedJobOut structure: {job: JobOut, hybrid_score, keyword_score, semantic_score, matched_skills, missing_skills, explanation, confidence}
        job = j["job"]
        salary = _format_monthly_inr(job["salary_min"], job["salary_max"], job["salary_currency"])
        rows.append(
            f"### {job['title']} — {job['company']}\n"
            f"- Location: {job['location_normalized']} ({job['remote']})\n"
            f"- Type: {job['employment_type']}\n"
            f"- Experience: {job['experience_level']}\n"
            f"- Salary: {salary}\n"
            f"- Verified: {job['verified']}\n"
            f"- Match: {j['hybrid_score']:.2f} (kw: {j['keyword_score']:.2f}, sem: {j['semantic_score']:.2f})\n"
            f"- Skills: {', '.join(j['matched_skills']) if j['matched_skills'] else 'none'}\n"
            f"- Missing: {', '.join(j['missing_skills']) if j['missing_skills'] else 'none'}\n"
            f"- Explanation: {j['explanation']}\n"
            f"- Apply: {job['apply_url']}\n"
        )
    return "\n---\n".join(rows)


def update_model_dropdown(provider: str):
    models = PROVIDER_MODELS.get(provider, PROVIDER_MODELS["auto"])
    return gr.Dropdown(choices=models, value=models[0], label="Model", interactive=True)


with gr.Blocks(title="CareerOS") as demo:
    gr.Markdown("# CareerOS — Job Search & Match")
    with gr.Row():
        query = gr.Textbox(label="Role / query", placeholder="e.g. backend engineer")
    with gr.Row():
        location = gr.Textbox(label="Location (optional)", value="Hyderabad, India")
        remote_only = gr.Checkbox(label="Remote only", value=False)
    with gr.Row():
        employment_type = gr.Dropdown(
            label="Employment Type",
            choices=["", "full_time", "part_time", "internship", "contract", "temporary"],
            value="",
            allow_custom_value=True,
        )
        experience_level = gr.Dropdown(
            label="Experience Level",
            choices=["", "intern", "fresher", "entry", "mid", "senior"],
            value="",
            allow_custom_value=True,
        )
    with gr.Row():
        min_salary = gr.Number(label="Minimum Salary (annual)", value=0, precision=0)
        posted_within_days = gr.Number(label="Posted Within (days)", value=0, precision=0)
    with gr.Row():
        llm_provider = gr.Dropdown(label="LLM Provider", choices=PROVIDERS, value="auto")
        model_name = gr.Dropdown(label="Model", choices=PROVIDER_MODELS["auto"], value=PROVIDER_MODELS["auto"][0])
    btn = gr.Button("Search & Match", variant="primary")
    output = gr.Markdown()

    llm_provider.change(fn=update_model_dropdown, inputs=llm_provider, outputs=model_name)

    btn.click(
        fn=search,
        inputs=[
            query,
            location,
            remote_only,
            employment_type,
            experience_level,
            min_salary,
            posted_within_days,
            llm_provider,
            model_name,
        ],
        outputs=output,
    )

if __name__ == "__main__":
    demo.launch()