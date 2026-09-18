"""Tests for the HTTP service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from schwa.lexicon import Lexicon
from schwa.restore import LexiconRestorer
from schwa_api.main import MAX_CHARACTERS, RateLimiter, app, get_restorer
from schwa_api.restorers import Loaded

SENTENCES = ["Səncə nədən başlayaq?", "İşıq söndü.", "Qız məktəbə getdi."]


@pytest.fixture
def client() -> TestClient:
    lexicon = Lexicon.from_sentences(SENTENCES)
    loaded = Loaded(LexiconRestorer(lexicon), {"lexicon": "test"})
    app.dependency_overrides[get_restorer] = lambda: loaded
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestRestore:
    def test_restores_the_text(self, client: TestClient):
        response = client.post("/v1/restore", json={"text": "sence neden baslayaq?"})
        assert response.status_code == 200
        assert response.json()["text"] == "səncə nədən başlayaq?"

    def test_reports_each_change_with_its_span(self, client: TestClient):
        changes = client.post("/v1/restore", json={"text": "isiq sondu."}).json()["changes"]
        assert changes[0] == {"start": 0, "end": 4, "from": "isiq", "to": "işıq"}

    def test_unchanged_text_reports_no_changes(self, client: TestClient):
        body = client.post("/v1/restore", json={"text": "hello world"}).json()
        assert body["text"] == "hello world"
        assert body["changes"] == []

    def test_refuses_text_beyond_the_limit(self, client: TestClient):
        response = client.post("/v1/restore", json={"text": "a" * (MAX_CHARACTERS + 1)})
        assert response.status_code == 422

    def test_empty_text_is_fine(self, client: TestClient):
        assert client.post("/v1/restore", json={"text": ""}).json()["text"] == ""


class TestInfo:
    def test_reports_the_restorer_in_use(self, client: TestClient):
        body = client.get("/v1/info").json()
        assert body["restorer"] == "lexicon"
        assert body["sources"] == {"lexicon": "test"}
        assert body["stores_text"] is False

    def test_health_is_plain(self, client: TestClient):
        assert client.get("/health").json() == {"status": "ok"}


class TestRateLimiter:
    def test_allows_up_to_the_allowance(self):
        limiter = RateLimiter(allowance=2, window=60)
        assert limiter.check("1.2.3.4", now=0)
        assert limiter.check("1.2.3.4", now=1)
        assert not limiter.check("1.2.3.4", now=2)

    def test_forgets_requests_older_than_the_window(self):
        limiter = RateLimiter(allowance=1, window=60)
        assert limiter.check("1.2.3.4", now=0)
        assert not limiter.check("1.2.3.4", now=30)
        assert limiter.check("1.2.3.4", now=61)

    def test_counts_each_address_separately(self):
        limiter = RateLimiter(allowance=1, window=60)
        assert limiter.check("1.2.3.4", now=0)
        assert limiter.check("5.6.7.8", now=0)
