from typing import Optional

from pydantic import BaseModel, Field


class SubAgentFinding(BaseModel):
    """One research finding from a sub-agent tool."""

    source: str = Field(description="Where this finding came from")
    url: Optional[str] = Field(default=None, description="URL of the evidence source")
    finding: str = Field(description="What was found, in plain English")
    supports_eligibility: Optional[bool] = Field(
        default=None,
        description="True = supports eligibility, False = contradicts, None = neutral/unclear",
    )
    is_error: bool = Field(default=False, description="True when the tool encountered an error")
    error_detail: Optional[str] = Field(default=None, description="Raw error string for debugging")


class VerificationResult(BaseModel):
    """Final verdict from the verification agent for a business × settlement candidate."""

    verdict: str = Field(description="One of: verified, likely, unlikely, excluded")
    confidence: int = Field(default=50, description="0-100 confidence in the verdict")
    is_chain: bool = Field(default=False, description="Whether the business appears to be a chain")
    chain_reason: Optional[str] = Field(default=None, description="Why this was flagged as a chain")
    evidence: list[SubAgentFinding] = Field(default_factory=list, description="All research findings")
    reasoning: str = Field(default="", description="LLM's plain-English reasoning")
    checks_performed: list[str] = Field(default_factory=list, description="Checks performed")
