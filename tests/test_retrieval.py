from app.services.embeddings import get_embedding_provider
from app.services.reranker import ScoredJob, keyword_score, rerank


def test_embedding_deterministic():
    emb = get_embedding_provider()
    v1 = emb.embed("backend engineer python")
    v2 = emb.embed("backend engineer python")
    assert v1 == v2
    assert len(v1) == emb.dim


def test_embedding_different_text_different_vector():
    emb = get_embedding_provider()
    v1 = emb.embed("backend engineer")
    v2 = emb.embed("marketing manager")
    assert v1 != v2


def test_keyword_score_full_overlap():
    assert keyword_score("backend engineer", "Backend Engineer role", "python sql") == 1.0


def test_keyword_score_no_overlap():
    assert keyword_score("backend engineer", "Marketing Manager", "seo") == 0.0


def test_rerank_orders_by_hybrid_score():
    jobs = [
        ScoredJob(job_id="a", keyword_score=0.2, semantic_score=0.2),
        ScoredJob(job_id="b", keyword_score=0.9, semantic_score=0.9),
    ]
    top = rerank(jobs, top_k=2)
    assert top[0].job_id == "b"


def test_rerank_respects_top_k():
    jobs = [ScoredJob(job_id=str(i), keyword_score=i / 10, semantic_score=0.0) for i in range(10)]
    top = rerank(jobs, top_k=3)
    assert len(top) == 3
