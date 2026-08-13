import pytest

from app.services.model_router import ModelRouter, MatchExplanation


@pytest.mark.asyncio
async def test_router_no_providers_returns_unknown_not_invented():
    router = ModelRouter(llama=None, gemini=None)
    result = await router.explain_match("Backend Engineer", "Needs Python", ["Python"])
    assert isinstance(result, MatchExplanation)
    assert result.matched_skills == []
    assert "unknown" in result.explanation.lower()


class _FakeLlama:
    async def structured(self, prompt, schema):
        return schema(matched_skills=["Python"], missing_skills=["Go"], explanation="ok", confidence=0.9)


class _FakeLlamaLowConfidence:
    async def structured(self, prompt, schema):
        return schema(matched_skills=[], missing_skills=[], explanation="unsure", confidence=0.1)


class _FakeGemini:
    async def structured(self, prompt, schema):
        return schema(matched_skills=["Python"], missing_skills=[], explanation="gemini says ok", confidence=0.95)


@pytest.mark.asyncio
async def test_router_uses_llama_when_confident():
    router = ModelRouter(llama=_FakeLlama(), gemini=_FakeGemini())
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "ok"


@pytest.mark.asyncio
async def test_router_escalates_to_gemini_when_llama_unconfident():
    router = ModelRouter(llama=_FakeLlamaLowConfidence(), gemini=_FakeGemini())
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "gemini says ok"
