"""Gradio V1 UI (spec 3.6). Thin client over FastAPI — no business logic here."""

import httpx
import gradio as gr

API_BASE = "http://127.0.0.1:8000"


def search(query: str, location: str, remote_only: bool):
    if not query.strip():
        return "Enter a role/query first."
    payload = {"query": query, "location": location or None, "remote_only": remote_only}
    try:
        resp = httpx.post(f"{API_BASE}/jobs/search", json=payload, timeout=30.0)
        resp.raise_for_status()
        jobs = resp.json()
    except httpx.HTTPError as e:
        return f"Search failed: {e}"

    if not jobs:
        return "No jobs matched hard filters."

    rows = []
    for j in jobs:
        salary = "unknown"
        if j["salary_min"] is not None:
            salary = f"{j['salary_currency']} {j['salary_min']:.0f}-{j['salary_max']:.0f}"
        rows.append(
            f"### {j['title']} — {j['company']}\n"
            f"- Location: {j['location_normalized']} ({j['remote']})\n"
            f"- Type: {j['employment_type']}\n"
            f"- Salary: {salary}\n"
            f"- Verified: {j['verified']}\n"
            f"- Apply: {j['apply_url']}\n"
        )
    return "\n---\n".join(rows)


with gr.Blocks(title="CareerOS") as demo:
    gr.Markdown("# CareerOS — Job Search ")
    with gr.Row():
        query = gr.Textbox(label="Role / query", placeholder="e.g. backend engineer")
        location = gr.Textbox(label="Location (optional)")
        remote_only = gr.Checkbox(label="Remote only")
    btn = gr.Button("Search")
    output = gr.Markdown()
    btn.click(fn=search, inputs=[query, location, remote_only], outputs=output)

if __name__ == "__main__":
    demo.launch()
