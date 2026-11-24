from fastapi.testclient import TestClient

from findex.index import build_index
from findex.web.app import Settings, create_app, get_index, get_settings


def test_routes(corpus):
    app = create_app("sync")
    ix = build_index(corpus, positions=True)
    app.dependency_overrides[get_index] = lambda: ix
    app.dependency_overrides[get_settings] = lambda: Settings(corpus_path=corpus)
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}
    result = client.get("/search", params={"q": "python", "k": 1}).json()
    assert result["total"] == 2
    assert len(result["results"]) == 1
    assert client.get("/search", params={"q": "python", "k": 0}).status_code == 422
    assert client.get("/search", params={"q": "("}).status_code == 422
    assert client.get("/search", params={"q": "python", "page": 2, "k": 1}).json()["results"][0]["doc_id"] != result["results"][0]["doc_id"]
    assert client.get("/docs/999").status_code == 404
    assert client.get("/docs/0").status_code == 200
    assert client.get("/stats").json()["documents"] == 2
    assert client.get("/").status_code == 200
    assert "<mark>" in client.get("/", params={"q": "python"}).text
    assert client.get("/doc/0").status_code == 200
    assert client.get("/docs").status_code == 200
    assert "x-request-id" in client.get("/health").headers


def test_unloaded():
    app = create_app()
    app.dependency_overrides[get_index] = lambda: None
    client = TestClient(app)
    assert client.get("/health").status_code == 503
