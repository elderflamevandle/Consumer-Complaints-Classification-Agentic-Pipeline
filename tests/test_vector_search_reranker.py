"""Tests for src/tools/vector_search.py — ChromaDB retrieval + HF reranker.

Coverage areas:
  1. _rerank_with_hf  — score parsing, ordering, all fallback paths
  2. retrieve_similar_cases — candidate pool size, reranker wiring, token guard,
     order mutation vs cosine baseline, and score field preservation
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.tools.vector_search import (
    _CANDIDATE_POOL,
    _RERANK_MODEL,
    RetrievedCase,
    _rerank_with_hf,
    retrieve_similar_cases,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _case(
    case_id: str,
    *,
    score: float = 0.5,
    narrative: str = "sample narrative",
    issue: str = "billing",
) -> RetrievedCase:
    return RetrievedCase(
        id=case_id,
        product="credit_card",
        issue=issue,
        date="2025-01-01",
        state="CA",
        narrative=narrative,
        score=score,
    )


def _chroma_results(
    rows: list[dict[str, Any]],
) -> dict[str, list[list[Any]]]:
    """Build a minimal fake ChromaDB query() response."""
    return {
        "ids": [[r["id"] for r in rows]],
        "documents": [[r.get("narrative", "") for r in rows]],
        "metadatas": [
            [
                {
                    "product": r.get("product", "credit_card"),
                    "issue": r.get("issue", "billing"),
                    "date": r.get("date", "2025-01-01"),
                    "state": r.get("state", "CA"),
                }
                for r in rows
            ]
        ],
        "distances": [[r.get("distance", 0.3) for r in rows]],
    }


def _mock_chroma_client(rows: list[dict[str, Any]]) -> MagicMock:
    """Return a mocked chromadb.PersistentClient whose collection returns `rows`."""
    collection = MagicMock()
    collection.query.return_value = _chroma_results(rows)
    client = MagicMock()
    client.get_collection.return_value = collection
    return client


def _hf_response(scores: list[float]) -> MagicMock:
    """Return a mock requests.Response whose .json() is a HF cross-encoder payload."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        [{"label": "1", "score": s}] for s in scores
    ]
    return mock_resp


# ---------------------------------------------------------------------------
# 1. _rerank_with_hf unit tests
# _rerank_with_hf returns (candidates, scores) — unpack both in every test.
# ---------------------------------------------------------------------------

class TestRerankWithHF:

    def test_reranks_candidates_by_hf_score(self) -> None:
        """Candidate with the highest HF score must be ranked first."""
        candidates = [_case("A", score=0.9), _case("B", score=0.8), _case("C", score=0.7)]
        # Reranker says B is most relevant
        hf_scores = [0.60, 0.95, 0.40]

        with patch("src.tools.vector_search.requests.post", return_value=_hf_response(hf_scores)):
            result, scores = _rerank_with_hf("query", candidates, "fake-token")

        assert [c.id for c in result] == ["B", "A", "C"]
        assert scores == sorted(scores, reverse=True)

    def test_accepts_bare_float_scores(self) -> None:
        """HF API can return bare floats instead of label-score dicts."""
        candidates = [_case("X"), _case("Y")]
        mock_resp = MagicMock()
        mock_resp.json.return_value = [0.3, 0.95]

        with patch("src.tools.vector_search.requests.post", return_value=mock_resp):
            result, scores = _rerank_with_hf("query", candidates, "tok")

        assert result[0].id == "Y"
        assert result[1].id == "X"
        assert scores[0] > scores[1]

    def test_fallback_on_network_error(self) -> None:
        """ConnectionError must return original order with empty scores list."""
        candidates = [_case("A", score=0.9), _case("B", score=0.8)]

        with patch(
            "src.tools.vector_search.requests.post",
            side_effect=ConnectionError("timeout"),
        ):
            result, scores = _rerank_with_hf("query", candidates, "tok")

        assert [c.id for c in result] == ["A", "B"]
        assert scores == []

    def test_fallback_on_http_error(self) -> None:
        """Non-2xx HTTP response must fall back to original order with empty scores."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")
        candidates = [_case("A"), _case("B")]

        with patch("src.tools.vector_search.requests.post", return_value=mock_resp):
            result, scores = _rerank_with_hf("query", candidates, "bad-token")

        assert [c.id for c in result] == ["A", "B"]
        assert scores == []

    def test_fallback_on_mismatched_score_count(self) -> None:
        """Score list shorter than candidates must trigger fallback with empty scores."""
        candidates = [_case("A"), _case("B"), _case("C")]
        mock_resp = MagicMock()
        mock_resp.json.return_value = [[{"label": "1", "score": 0.9}]]  # only 1 item

        with patch("src.tools.vector_search.requests.post", return_value=mock_resp):
            result, scores = _rerank_with_hf("query", candidates, "tok")

        assert [c.id for c in result] == ["A", "B", "C"]
        assert scores == []

    def test_sends_correct_url_and_auth_header(self) -> None:
        """API call must target the configured HF model URL with Bearer auth."""
        candidates = [_case("Z")]

        with patch(
            "src.tools.vector_search.requests.post",
            return_value=_hf_response([0.9]),
        ) as mock_post:
            _rerank_with_hf("my query", candidates, "my-token")

        url, = mock_post.call_args.args
        assert _RERANK_MODEL in url
        assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer my-token"

    def test_sends_query_narrative_pairs(self) -> None:
        """Payload inputs must be [query, narrative] pairs for every candidate."""
        candidates = [
            _case("1", narrative="first doc"),
            _case("2", narrative="second doc"),
        ]

        with patch(
            "src.tools.vector_search.requests.post",
            return_value=_hf_response([0.8, 0.6]),
        ) as mock_post:
            _rerank_with_hf("test query", candidates, "tok")

        sent_pairs = mock_post.call_args.kwargs["json"]["inputs"]
        assert sent_pairs == [
            {"text": "test query", "text_pair": "first doc"},
            {"text": "test query", "text_pair": "second doc"},
        ]

    def test_empty_candidates_returns_empty(self) -> None:
        """Zero candidates must return ([], []) without calling the API."""
        with patch("src.tools.vector_search.requests.post") as mock_post:
            result, scores = _rerank_with_hf("q", [], "tok")

        assert result == []
        assert scores == []
        mock_post.assert_not_called()


# ---------------------------------------------------------------------------
# 2. retrieve_similar_cases integration tests
# ---------------------------------------------------------------------------

class TestRetrieveSimilarCases:

    def test_fetches_candidate_pool_not_just_limit(self) -> None:
        """ChromaDB must be queried for _CANDIDATE_POOL records, not just limit."""
        rows = [
            {"id": str(i), "narrative": f"case {i}", "distance": 0.05 * i}
            for i in range(_CANDIDATE_POOL)
        ]
        client = _mock_chroma_client(rows)

        with (
            patch("chromadb.PersistentClient", return_value=client),
            patch.dict(os.environ, {"HF_TOKEN": ""}, clear=False),
        ):
            retrieve_similar_cases(query_text="billing fraud", limit=5)

        n_results = client.get_collection.return_value.query.call_args.kwargs["n_results"]
        assert n_results >= _CANDIDATE_POOL, (
            f"Expected ChromaDB fetch >= {_CANDIDATE_POOL}, got {n_results}"
        )

    def test_returns_exactly_limit_results(self) -> None:
        """Return count must equal `limit` regardless of reranking."""
        rows = [
            {"id": str(i), "narrative": f"n {i}", "distance": 0.05 * i}
            for i in range(_CANDIDATE_POOL)
        ]
        client = _mock_chroma_client(rows)
        scores = list(range(_CANDIDATE_POOL, 0, -1))

        with (
            patch("chromadb.PersistentClient", return_value=client),
            patch("src.tools.vector_search.requests.post", return_value=_hf_response(scores)),
            patch.dict(os.environ, {"HF_TOKEN": "tok"}),
        ):
            result = retrieve_similar_cases(query_text="test", limit=5)

        assert len(result) == 5

    def test_reranker_not_called_when_token_absent(self) -> None:
        """No HF_TOKEN → _rerank_with_hf must never be invoked."""
        rows = [
            {"id": str(i), "narrative": f"n {i}", "distance": 0.05 * i}
            for i in range(_CANDIDATE_POOL)
        ]
        client = _mock_chroma_client(rows)

        with (
            patch("chromadb.PersistentClient", return_value=client),
            patch("src.tools.vector_search._rerank_with_hf") as mock_rerank,
            patch.dict(os.environ, {"HF_TOKEN": ""}),
        ):
            retrieve_similar_cases(query_text="test", limit=5)

        mock_rerank.assert_not_called()

    def test_reranker_called_when_token_present(self) -> None:
        """HF_TOKEN present → _rerank_with_hf must be called with all 10 candidates."""
        rows = [
            {"id": str(i), "narrative": f"n {i}", "distance": 0.05 * i}
            for i in range(_CANDIDATE_POOL)
        ]
        client = _mock_chroma_client(rows)

        with (
            patch("chromadb.PersistentClient", return_value=client),
            patch(
                "src.tools.vector_search._rerank_with_hf",
                # must return (candidates, scores) tuple now
                side_effect=lambda q, candidates, token, **kw: (candidates, [0.9] * len(candidates)),
            ) as mock_rerank,
            patch.dict(os.environ, {"HF_TOKEN": "my-token"}),
        ):
            retrieve_similar_cases(query_text="billing dispute", limit=5)

        mock_rerank.assert_called_once()
        _q, passed_candidates, passed_token = mock_rerank.call_args.args
        assert passed_token == "my-token"
        assert len(passed_candidates) == _CANDIDATE_POOL

    def test_reranker_promotes_lower_cosine_candidate(self) -> None:
        """A candidate outside the cosine top-5 must appear in results when reranked up."""
        # Cosine order: id 0 (best, distance 0) … id 9 (worst, distance 0.45)
        rows = [
            {"id": str(i), "narrative": f"narrative {i}", "distance": 0.05 * i}
            for i in range(_CANDIDATE_POOL)
        ]
        # Reranker says id 9 (index 9) is most relevant, descending from there
        rerank_scores = list(range(_CANDIDATE_POOL))  # [0,1,2,...,9] → id 9 gets 9
        client = _mock_chroma_client(rows)

        with (
            patch("chromadb.PersistentClient", return_value=client),
            patch("src.tools.vector_search.requests.post", return_value=_hf_response(rerank_scores)),
            patch.dict(os.environ, {"HF_TOKEN": "tok"}),
        ):
            result = retrieve_similar_cases(query_text="complaint", limit=5)

        # Top result must be id 9, which was rank-10 by cosine similarity
        assert result[0].id == "9"
        returned_ids = [c.id for c in result]
        assert returned_ids == ["9", "8", "7", "6", "5"]

    def test_cosine_score_preserved_after_reranking(self) -> None:
        """RetrievedCase.score must reflect cosine distance, not the HF rerank score."""
        rows = [
            {"id": "A", "narrative": "first",  "distance": 0.1},  # cosine score 0.9
            {"id": "B", "narrative": "second", "distance": 0.5},  # cosine score 0.5
        ]
        # Reranker promotes B above A
        client = _mock_chroma_client(rows)

        with (
            patch("chromadb.PersistentClient", return_value=client),
            patch("src.tools.vector_search.requests.post", return_value=_hf_response([0.2, 0.95])),
            patch.dict(os.environ, {"HF_TOKEN": "tok"}),
        ):
            result = retrieve_similar_cases(query_text="q", limit=2)

        assert result[0].id == "B"
        assert abs(result[0].score - 0.5) < 1e-5   # cosine score for B (1 - 0.5)
        assert result[1].id == "A"
        assert abs(result[1].score - 0.9) < 1e-5   # cosine score for A (1 - 0.1)

    def test_empty_collection_returns_empty_list(self) -> None:
        """Missing collection must return [] without raising."""
        client = MagicMock()
        client.get_collection.side_effect = Exception("not found")

        with patch("chromadb.PersistentClient", return_value=client):
            result = retrieve_similar_cases(query_text="anything", limit=5)

        assert result == []

    def test_reranker_fallback_preserves_cosine_order(self) -> None:
        """If the reranker API errors, results must fall back to cosine-sorted order."""
        rows = [
            {"id": str(i), "narrative": f"n {i}", "distance": 0.05 * i}
            for i in range(_CANDIDATE_POOL)
        ]
        client = _mock_chroma_client(rows)

        with (
            patch("chromadb.PersistentClient", return_value=client),
            patch(
                "src.tools.vector_search.requests.post",
                side_effect=ConnectionError("network down"),
            ),
            patch.dict(os.environ, {"HF_TOKEN": "tok"}),
        ):
            result = retrieve_similar_cases(query_text="fraud", limit=5)

        # Without reranking, best cosine score = lowest distance = id "0"
        assert result[0].id == "0"
        assert len(result) == 5
