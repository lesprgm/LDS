from typing import Optional

from pydantic import BaseModel, Field


class SettlementRules(BaseModel):
    """Structured representation of a settlement's eligibility rules."""

    settlement_name: Optional[str] = Field(default="Unknown Settlement", description="Name of the settlement")
    administrator: Optional[str] = Field(default="Unknown", description="Settlement administrator")
    defendant: Optional[str] = Field(default="Unknown", description="Defendant in the case")
    case_number: Optional[str] = Field(default=None, description="Case number if available")
    summary: Optional[str] = Field(default="", description="2-3 sentence plain English summary")

    eligible_class_description: Optional[str] = Field(default="", description="Who qualifies (verbatim from document)")
    eligible_industries: Optional[list[str]] = Field(
        default_factory=list,
        description="Inferred industry categories that may qualify",
    )
    eligible_geography: Optional[str] = Field(default=None, description="Geographic restrictions if any")
    eligible_time_period: Optional[str] = Field(
        default=None,
        description="Time period for qualifying activity (e.g., 'Jan 2011 - Dec 2023')",
    )
    eligible_actions: Optional[list[str]] = Field(
        default_factory=list,
        description="Actions the business must have taken to qualify",
    )
    exclusions: Optional[list[str]] = Field(
        default_factory=list,
        description="Who is excluded from the settlement",
    )

    proof_required: Optional[list[str]] = Field(
        default_factory=list,
        description="Documents/records needed to file a claim",
    )
    proof_difficulty: Optional[str] = Field(
        default="moderate",
        description="How hard it is to gather proof: easy, moderate, or hard",
    )

    claim_deadline: Optional[str] = Field(default=None, description="Claim deadline (ISO date or description)")
    claim_window_status: Optional[str] = Field(
        default="open",
        description="Status of claim window: open, closing_soon, or closed",
    )

    smb_relevance: Optional[str] = Field(
        default="medium",
        description="Relevance to small businesses: high, medium, or low",
    )
    smb_relevance_reason: Optional[str] = Field(default="", description="Why this is/isn't relevant to SMBs")
    clarity_score: Optional[int] = Field(
        default=5,
        description="1-10 score for how clearly the rules are stated",
        ge=1,
        le=10,
    )

    claim_url: Optional[str] = Field(default=None, description="URL to file a claim")
    claim_method: Optional[str] = Field(default="online", description="How to file: online, mail, or both")
    estimated_payout: Optional[str] = Field(default=None, description="Estimated payout range or formula")
