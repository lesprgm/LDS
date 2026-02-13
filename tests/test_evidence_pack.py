"""Tests for sanitized evidence-pack generation."""

from pathlib import Path

from extraction.schemas import SettlementRules
from verification.schemas import SubAgentFinding, VerificationResult

from evidence.generator import build_pack_html, generate_dual_packs, write_evidence_pack


def _sample_inputs():
    business = {
        "name": "Acme Bakery",
        "city": "Wooster, OH",
        "category": "bakery",
        "website": "https://example.com/acme-bakery",
    }
    settlement = SettlementRules(
        settlement_name="Sample Settlement",
        summary="Sample summary",
        eligible_class_description="Sample class",
        eligible_actions=["Accepted eligible card payments"],
        proof_required=["Statements"],
        claim_deadline="2026-05-18",
        claim_url="https://example.com/claim",
    )
    verification = VerificationResult(
        verdict="likely",
        confidence=77,
        reasoning="Reasoning text",
        checks_performed=["business_website", "general_search"],
        evidence=[
            SubAgentFinding(
                source="business_website",
                finding="Mentions card payments.",
                supports_eligibility=True,
            )
        ],
    )
    return business, settlement, verification


def test_client_pack_hides_internal_section():
    business, settlement, verification = _sample_inputs()
    html = build_pack_html(business, settlement, verification, pack_type="client")
    assert "Settlement Evidence Pack (Client)" in html
    assert "Acme Bakery" in html
    assert "Internal QA Signals" not in html


def test_internal_pack_contains_diagnostics():
    business, settlement, verification = _sample_inputs()
    html = build_pack_html(business, settlement, verification, pack_type="internal")
    assert "Settlement Evidence Pack (Internal)" in html
    assert "Internal QA Signals" in html
    assert "Confidence:" in html
    assert "Tool Findings" in html


def test_write_evidence_pack_creates_file(tmp_path: Path):
    business, settlement, verification = _sample_inputs()
    out = write_evidence_pack(
        business,
        settlement,
        verification,
        out_dir=tmp_path,
        pack_type="client",
        screenshot_paths=["screenshots/acme_homepage.png"],
    )
    assert out.exists()
    assert out.name == "Acme_Bakery_CLIENT.html"
    assert "screenshots/acme_homepage.png" in out.read_text(encoding="utf-8")


def test_generate_dual_packs_creates_both_variants(tmp_path: Path):
    business, settlement, verification = _sample_inputs()
    paths = generate_dual_packs(business, settlement, verification, out_dir=tmp_path)
    assert set(paths.keys()) == {"client", "internal"}
    assert paths["client"].exists()
    assert paths["internal"].exists()
