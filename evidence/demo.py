from __future__ import annotations

import argparse

from extraction.schemas import SettlementRules
from verification.schemas import SubAgentFinding, VerificationResult

from .generator import generate_dual_packs


def build_demo_inputs() -> tuple[dict, SettlementRules, VerificationResult]:
    """Create static inputs so the demo runs with no API calls."""
    business = {
        "name": "Acme Bakery",
        "city": "Wooster, OH",
        "category": "bakery",
        "website": "https://example.com/acme-bakery",
    }

    settlement = SettlementRules(
        settlement_name="Payment Card Merchant Settlement (Sample)",
        administrator="Example Admin Services",
        defendant="Example Payments Inc.",
        summary=(
            "Sample settlement for merchants who accepted specific card products "
            "during a defined period."
        ),
        eligible_class_description=(
            "U.S. small businesses that accepted the defendant's payment cards "
            "between January 2018 and December 2023."
        ),
        eligible_actions=[
            "Accepted eligible card payments",
            "Processed transactions through a standard merchant account",
        ],
        proof_required=[
            "Merchant processor statements",
            "Basic business registration documents",
        ],
        claim_deadline="2026-05-18",
        claim_window_status="open",
        claim_method="online",
        claim_url="https://example.com/claim-form",
        smb_relevance="high",
        clarity_score=8,
    )

    verification = VerificationResult(
        verdict="likely",
        confidence=78,
        is_chain=False,
        reasoning=(
            "Business profile and website signals indicate independent operation "
            "with likely card acceptance during the covered period."
        ),
        checks_performed=[
            "business_website",
            "platform_search",
            "general_search",
            "review_search",
        ],
        evidence=[
            SubAgentFinding(
                source="business_website",
                url="https://example.com/acme-bakery",
                finding="Site includes online order and in-store payment references.",
                supports_eligibility=True,
            ),
            SubAgentFinding(
                source="general_search",
                finding="Business appears in local listings as independent bakery.",
                supports_eligibility=True,
            ),
        ],
    )
    return business, settlement, verification


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate sanitized demo evidence packs.")
    parser.add_argument(
        "--out",
        default="output/evidence_demo",
        help="Directory where demo HTML packs are written.",
    )
    args = parser.parse_args()

    business, settlement, verification = build_demo_inputs()
    outputs = generate_dual_packs(
        business,
        settlement,
        verification,
        out_dir=args.out,
        screenshot_paths=[
            "screenshots/acme_homepage.png",
            "screenshots/acme_checkout.png",
        ],
    )

    print("Generated demo evidence packs:")
    for key, path in outputs.items():
        print(f"- {key}: {path}")


if __name__ == "__main__":
    main()
