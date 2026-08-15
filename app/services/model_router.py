"""Model router (spec section 6). Deterministic rules decide the path — LLMs never
override hard filters/eligibility (spec 2.1). Structured output is validated with
Pydantic before it's trusted (spec 51: 'never invent missing data').

Model note (Aug 2026): don't hard-pin a Gemini version string — Google retires
dated model IDs on a rolling schedule (2.0 Flash line is already gone). Use the
rolling alias 'gemini-flash-latest' (config default) so this doesn't silently
404 when a version is sunset.
"""

import json
from typing import Protocol

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings

settings = get_settings()


class MatchExplanation(BaseModel):
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    explanation: str = "unknown"
    confidence: float = 0.0


class LLMProvider(Protocol):
    async def structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...


class LlamaCppProvider:
    """Local, private, cheap — first choice for high-volume classification (spec 6.2)."""

    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        payload = {
            "model": "local",
            "messages": [
                {"role": "system", "content": "Respond ONLY with JSON matching the required schema. No prose."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"]
            return schema.model_validate(json.loads(raw))
        except (httpx.ConnectError, httpx.TimeoutException):
            # Fail fast — don't hang for 30s if llama.cpp isn't running
            raise


class GeminiProvider:
    """Online escalation for harder ambiguity/reasoning (spec 6.2). Cheapest capable model."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": schema.model_json_schema(),
            },
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, params={"key": self.api_key}, json=payload)
            resp.raise_for_status()
            raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return schema.model_validate(json.loads(raw))


class NullProvider:
    """No LLM configured. Returns unknown/empty rather than inventing anything (spec 2.3)."""

    async def structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        return schema()


class ModelRouter:
    """Routing policy per spec 6.2: deterministic rules first, then llama.cpp, then Gemini escalation."""

    def __init__(self, llama: LLMProvider | None, gemini: LLMProvider | None):
        self._llama = llama
        self._gemini = gemini

    async def explain_match(self, job_title: str, job_description: str, candidate_skills: list[str]) -> MatchExplanation:
        prompt = (
            "Candidate skills: " + ", ".join(candidate_skills) + "\n"
            f"Job title: {job_title}\nJob description: {job_description}\n\n"
            "Return JSON with: matched_skills (subset of candidate skills present in the JD), "
            "missing_skills (JD-required skills the candidate lacks), explanation (1-2 sentences, "
            "grounded only in the text above — never invent skills or experience not stated), "
            "confidence (0-1)."
        )

        # local first — cheap, private, high volume (spec 48 cost priority)
        if self._llama:
            try:
                result = await self._llama.structured(prompt, MatchExplanation)
                if result.confidence >= 0.6:
                    return result
            except (httpx.HTTPError, ValidationError, KeyError, json.JSONDecodeError):
                pass  # fall through to escalation, fail explicit not silent

        # confidence-based escalation to Gemini (spec 49)
        if self._gemini:
            try:
                return await self._gemini.structured(prompt, MatchExplanation)
            except (httpx.HTTPError, ValidationError, KeyError, json.JSONDecodeError):
                pass

        return MatchExplanation(explanation="unknown — no LLM provider available or all providers failed")


def get_model_router() -> ModelRouter:
    # Short timeout for llama so we fail fast if server isn't running
    llama = LlamaCppProvider(settings.llama_cpp_base_url, timeout=5.0) if settings.llama_cpp_base_url else None
    gemini = GeminiProvider(settings.gemini_api_key, settings.gemini_model) if settings.gemini_api_key else None

    if settings.llm_provider_mode == "llama":
        gemini = None
    elif settings.llm_provider_mode == "gemini":
        llama = None
    elif settings.llm_provider_mode == "none":
        llama = gemini = None

    return ModelRouter(llama, gemini)
