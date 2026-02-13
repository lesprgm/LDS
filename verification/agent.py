"""Verification agent — orchestrates parallel research and LLM reasoning."""

from __future__ import annotations

import logging
from typing import Optional

from framework.fanout import gather_with_limit, map_with_limit
from llm.client_factory import get_llm_client
from llm.structured_json import ainvoke_pydantic
from verification.schemas import SubAgentFinding, VerificationResult
from verification.tools import (
    check_business_website,
    check_review_presence,
    search_general_context,
    search_platform_presence,
)

logger = logging.getLogger(__name__)


REASONING_PROMPT = """You are a verification analyst for a small-business settlement matching service.

SETTLEMENT CONTEXT:
  Name: {settlement_name}
  Defendant: {defendant}
  Summary: {summary}
  Eligible class: {eligible_class}
  Eligible actions: {eligible_actions}
  Eligible industries: {eligible_industries}
  Eligible geography: {eligible_geography}
  Eligible time period: {eligible_time_period}
  Exclusions: {exclusions}

BUSINESS:
  Name: {biz_name}
  Category: {biz_category}
  Address: {biz_address}, {biz_city}, OH
  Website: {biz_website}

RESEARCH FINDINGS:
{findings_text}

TASK:
- Decide whether this business is likely eligible for this settlement.
- Return ONLY valid JSON with these keys:
  verdict: "verified"|"likely"|"unlikely"|"excluded"
  confidence: int 0-100
  is_chain: bool
  chain_reason: string|null
  reasoning: string
"""


def _with_context(result: VerificationResult, findings: list[SubAgentFinding], checks_performed: list[str]) -> VerificationResult:
    """Attach tool findings to an LLM verdict."""
    update = {"evidence": findings, "checks_performed": checks_performed}
    if hasattr(result, "model_copy"):
        # Pydantic v2
        return result.model_copy(update=update)
    # Pydantic v1
    return result.copy(update=update)


async def verify_candidate(
    business: dict,
    settlement: dict,
    llm_client=None,
) -> VerificationResult:
    """Verify a single business × settlement candidate."""
    biz_name = business.get("name", "")
    biz_city = business.get("city", "")
    biz_website = business.get("website") or ""

    settlement_name = settlement.get("settlement_name", "Unknown")
    settlement_context = {
        "settlement_name": settlement_name,
        "defendant": settlement.get("defendant", ""),
        "eligible_actions": settlement.get("eligible_actions", []),
        "platform_keywords": settlement.get("eligible_actions", []),
    }

    checks_performed: list[str] = [
        "business_website",
        "platform_search",
        "general_search",
        "review_search",
    ]

    tasks = [
        check_business_website(biz_website, settlement_context),
        search_platform_presence(biz_name, biz_city, settlement_context),
        search_general_context(biz_name, biz_city),
        check_review_presence(biz_name, biz_city),
    ]

    try:
        findings: list[SubAgentFinding] = await gather_with_limit(tasks, concurrency=4)

        findings_text = ""
        for i, finding in enumerate(findings, 1):
            findings_text += f"\n--- Finding {i} ({finding.source}) ---\n"
            if finding.url:
                findings_text += f"URL: {finding.url}\n"
            findings_text += f"{finding.finding}\n"

        prompt = REASONING_PROMPT.format(
            settlement_name=settlement_name,
            defendant=settlement.get("defendant", ""),
            summary=settlement.get("summary", ""),
            eligible_class=settlement.get("eligible_class_description", ""),
            eligible_actions=", ".join(settlement.get("eligible_actions", [])),
            eligible_industries=", ".join(settlement.get("eligible_industries", [])),
            eligible_geography=settlement.get("eligible_geography", ""),
            eligible_time_period=settlement.get("eligible_time_period", ""),
            exclusions=", ".join(settlement.get("exclusions", [])),
            biz_name=biz_name,
            biz_category=business.get("category", "Unknown"),
            biz_address=business.get("address", ""),
            biz_city=biz_city,
            biz_website=biz_website or "None",
            findings_text=findings_text,
        )

        if llm_client is None:
            llm_client = get_llm_client()

        verdict = await ainvoke_pydantic(llm_client, prompt, VerificationResult)
        return _with_context(verdict, findings=findings, checks_performed=checks_performed)

    except Exception as e:
        logger.error(f"Verification failed for {biz_name}: {e}")
        return VerificationResult(
            verdict="unlikely",
            confidence=0,
            evidence=[],
            reasoning=f"Verification failed: {e}",
            checks_performed=checks_performed,
        )


async def verify_candidates(
    candidates: list[tuple[dict, dict]],
    concurrency: int = 3,
    llm_client=None,
) -> list[VerificationResult]:
    """Verify a batch of candidates with limited concurrency."""
    if llm_client is None:
        llm_client = get_llm_client()

    async def _worker(item: tuple[dict, dict]) -> VerificationResult:
        biz, settlement = item
        return await verify_candidate(biz, settlement, llm_client=llm_client)

    return await map_with_limit(candidates, _worker, concurrency=concurrency, delay_s=0.5)
