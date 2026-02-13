"""Tests for the verification agent system."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from verification.schemas import SubAgentFinding, VerificationResult
from verification.tools import check_business_website, _extract_text
from verification.agent import verify_candidate, verify_candidates


class TestSubAgentFinding:
    def test_minimal(self):
        f = SubAgentFinding(source="test", finding="found something")
        assert f.source == "test"
        assert f.supports_eligibility is None


class TestVerificationResult:
    def test_defaults(self):
        r = VerificationResult(verdict="unlikely")
        assert r.confidence == 50
        assert r.is_chain is False


class TestExtractText:
    def test_strips_tags(self):
        html = "<html><body><h1>Hello</h1><p>World</p></body></html>"
        text = _extract_text(html)
        assert "Hello" in text and "World" in text
        assert "<" not in text


class TestCheckBusinessWebsite:
    @pytest.mark.asyncio
    async def test_no_website(self):
        result = await check_business_website("", {})
        assert result.source == "business_website"
        assert "No website" in result.finding

    @pytest.mark.asyncio
    async def test_invalid_url(self):
        with patch("verification.tools.asyncio.sleep", new_callable=AsyncMock), patch("httpx.AsyncClient") as MockClient:
            mock_ctx = AsyncMock()
            mock_ctx.get.side_effect = httpx.ConnectError("DNS resolution failed")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await check_business_website("http://does-not-exist.example", {})

        assert result.is_error is True


class TestVerifyCandidate:
    @pytest.mark.asyncio
    async def test_verify_candidate_parses_llm_json(self):
        business = {"name": "Test Biz", "city": "Wooster", "website": "https://example.com", "category": "restaurant", "address": "1 Main"}
        settlement = {
            "settlement_name": "Test Settlement",
            "defendant": "Defendant",
            "summary": "Summary",
            "eligible_class_description": "Merchants",
            "eligible_actions": ["accepted cards"],
            "eligible_industries": ["restaurant"],
            "eligible_geography": "US",
            "eligible_time_period": "2020-2022",
            "exclusions": [],
        }

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = type("R", (), {"content": json.dumps({"verdict": "likely", "confidence": 70, "is_chain": False, "chain_reason": None, "reasoning": "ok"})})()

        with patch("verification.agent.check_business_website", new_callable=AsyncMock) as mock_web, \
             patch("verification.agent.search_platform_presence", new_callable=AsyncMock) as mock_plat, \
             patch("verification.agent.search_general_context", new_callable=AsyncMock) as mock_gen, \
             patch("verification.agent.check_review_presence", new_callable=AsyncMock) as mock_rev:
            mock_web.return_value = SubAgentFinding(source="business_website", finding="ok")
            mock_plat.return_value = SubAgentFinding(source="platform_search", finding="ok")
            mock_gen.return_value = SubAgentFinding(source="general_search", finding="ok")
            mock_rev.return_value = SubAgentFinding(source="review_search", finding="ok")

            result = await verify_candidate(business, settlement, llm_client=mock_llm)

        assert result.verdict == "likely"
        assert result.confidence == 70


class TestVerifyCandidates:
    @pytest.mark.asyncio
    async def test_verify_candidates_returns_results(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = type("R", (), {"content": json.dumps({"verdict": "unlikely", "confidence": 50, "is_chain": False, "chain_reason": None, "reasoning": ""})})()

        candidates = [({"name": "A", "city": "Wooster"}, {"settlement_name": "S"})]

        with patch("verification.agent.check_business_website", new_callable=AsyncMock) as mock_web, \
             patch("verification.agent.search_platform_presence", new_callable=AsyncMock) as mock_plat, \
             patch("verification.agent.search_general_context", new_callable=AsyncMock) as mock_gen, \
             patch("verification.agent.check_review_presence", new_callable=AsyncMock) as mock_rev:
            mock_web.return_value = SubAgentFinding(source="business_website", finding="ok")
            mock_plat.return_value = SubAgentFinding(source="platform_search", finding="ok")
            mock_gen.return_value = SubAgentFinding(source="general_search", finding="ok")
            mock_rev.return_value = SubAgentFinding(source="review_search", finding="ok")

            results = await verify_candidates(candidates, concurrency=1, llm_client=mock_llm)

        assert len(results) == 1
        assert results[0].verdict == "unlikely"
