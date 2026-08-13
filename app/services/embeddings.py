"""Local embeddings (spec 3.3 'prefer local embedding model for cost/privacy').

Sandbox note: real sentence-transformer weights need a Hugging Face download,
not reachable from this environment's network allowlist. HashingVectorizer
gives deterministic, dependency-free local vectors so the retrieval pipeline
is real and testable now. Swap in a real local model (e.g. bge-small via
sentence-transformers) when running somewhere with model-hub access — the
EmbeddingProvider interface below doesn't change either way.
"""

from typing import Protocol

from sklearn.feature_extraction.text import HashingVectorizer

_VECTOR_SIZE = 256

_vectorizer = HashingVectorizer(
    n_features=_VECTOR_SIZE,
    alternate_sign=False,
    norm="l2",
)


class EmbeddingProvider(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class LocalHashingEmbedding:
    dim = _VECTOR_SIZE

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        matrix = _vectorizer.transform(texts)
        return matrix.toarray().tolist()


def get_embedding_provider() -> EmbeddingProvider:
    return LocalHashingEmbedding()
