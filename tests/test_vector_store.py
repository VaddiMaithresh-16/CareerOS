import shutil
import uuid

import pytest
from qdrant_client import QdrantClient

from app.services.vector_store import ensure_collection, index_job, semantic_search, COLLECTION


@pytest.fixture()
def client(tmp_path):
    path = tmp_path / "qdrant_test"
    c = QdrantClient(path=str(path))
    yield c
    c.close()


def test_index_and_search(client):
    ensure_collection(client)
    job_id = str(uuid.uuid4())
    index_job(client, job_id, "Backend Engineer", "Python and SQL role", ["Python", "SQL"])

    results = semantic_search(client, "Python backend role", limit=5)
    ids = [r[0] for r in results]
    assert job_id in ids
