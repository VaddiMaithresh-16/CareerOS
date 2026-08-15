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


class _FakeNVIDIA:
    async def structured(self, prompt, schema):
        return schema(matched_skills=["Python"], missing_skills=[], explanation="nvidia says ok", confidence=0.9)


class _FakeOpenRouter:
    async def structured(self, prompt, schema):
        return schema(matched_skills=["Python"], missing_skills=[], explanation="openrouter says ok", confidence=0.9)


class _FakeNVIDIALowConfidence:
    async def structured(self, prompt, schema):
        return schema(matched_skills=[], missing_skills=[], explanation="nvidia unsure", confidence=0.1)


class _FakeOpenRouterLowConfidence:
    async def structured(self, prompt, schema):
        return schema(matched_skills=[], missing_skills=[], explanation="openrouter unsure", confidence=0.1)


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


@pytest.mark.asyncio
async def test_router_escalates_to_nvidia_when_llama_unconfident():
    router = ModelRouter(
        llama=_FakeLlamaLowConfidence(),
        gemini=_FakeGemini(),
        nvidia=_FakeNVIDIA()
    )
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "nvidia says ok"


@pytest.mark.asyncio
async def test_router_escalates_to_openrouter_when_llama_nvidia_fail():
    router = ModelRouter(
        llama=_FakeLlamaLowConfidence(),
        gemini=_FakeGemini(),
        nvidia=_FakeNVIDIALowConfidence(),
        openrouter=_FakeOpenRouter()
    )
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "openrouter says ok"


@pytest.mark.asyncio
async def test_router_full_fallback_chain_llama_nvidia_openrouter_gemini():
    """Auto mode: llama -> nvidia -> openrouter -> gemini"""
    router = ModelRouter(
        llama=_FakeLlamaLowConfidence(),
        nvidia=_FakeNVIDIALowConfidence(),
        openrouter=_FakeOpenRouterLowConfidence(),
        gemini=_FakeGemini(),
    )
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "gemini says ok"


@pytest.mark.asyncio
async def test_router_explicit_provider_mode_openrouter():
    router = ModelRouter(
        llama=_FakeLlama(),
        openrouter=_FakeOpenRouter(),
        provider_mode="openrouter"
    )
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "openrouter says ok"


@pytest.mark.asyncio
async def test_router_explicit_provider_mode_nvidia():
    router = ModelRouter(
        llama=_FakeLlama(),
        nvidia=_FakeNVIDIA(),
        provider_mode="nvidia"
    )
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "nvidia says ok"


@pytest.mark.asyncio
async def test_router_explicit_provider_mode_llama():
    router = ModelRouter(
        llama=_FakeLlama(),
        gemini=_FakeGemini(),
        provider_mode="llama"
    )
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "ok"


@pytest.mark.asyncio
async def test_router_explicit_provider_mode_gemini():
    router = ModelRouter(
        llama=_FakeLlama(),
        gemini=_FakeGemini(),
        provider_mode="gemini"
    )
    result = await router.explain_match("x", "y", ["Python"])
    assert result.explanation == "gemini says ok"
