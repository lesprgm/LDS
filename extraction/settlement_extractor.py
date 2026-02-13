import logging
from pathlib import Path
from typing import Optional

from extraction.schemas import SettlementRules
from llm.client_factory import get_llm_client
from llm.structured_json import ainvoke_pydantic

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a legal analyst extracting settlement eligibility rules.
Given the following settlement document, extract ALL eligibility criteria
into the provided JSON schema. Be precise and literal — quote the document
where possible. If information is not stated, use null.

Focus especially on:
1. WHO qualifies (industry, geography, time period, actions taken)
2. WHO is excluded
3. WHAT proof is required
4. WHEN is the deadline
5. Is this relevant to small businesses? Why or why not?

CRITICAL for smb_relevance scoring:
- We are evaluating whether LOCAL SMALL BUSINESSES (restaurants, salons,
  auto shops, dentists, retail stores in a small Ohio town) could be
  CLAIMANTS in this settlement.
- "high" = settlement directly targets merchants/businesses as the harmed
  class (e.g., merchant fee overcharges, antitrust, data breaches
  affecting businesses, wage/labor settlements for employers).
- "medium" = settlement could plausibly include SMBs but they aren't the
  primary class (e.g., broad consumer settlements where a business might
  also have purchased the product).
- "low" = settlement is for INDIVIDUAL CONSUMERS, not businesses.
  Examples: app store users, streaming subscribers, personal loan
  borrowers, tenants, insurance policyholders, social media users,
  product recall for consumer goods.
- Most consumer platform settlements (Google Play, Netflix, Facebook,
  auto loans, health insurance, cosmetics) should be "low" because
  the eligible class is individuals, not merchants.

Document:
{document_text}

Return a valid JSON object matching this schema:
- settlement_name: str
- administrator: str
- defendant: str
- case_number: str or null
- summary: str (2-3 sentences)
- eligible_class_description: str
- eligible_industries: list[str]
- eligible_geography: str or null
- eligible_time_period: str or null
- eligible_actions: list[str]
- exclusions: list[str]
- proof_required: list[str]
- proof_difficulty: "easy" | "moderate" | "hard"
- claim_deadline: str or null
- claim_window_status: "open" | "closing_soon" | "closed"
- smb_relevance: "high" | "medium" | "low"
- smb_relevance_reason: str
- clarity_score: int (1-10)
- claim_url: str or null
- claim_method: "online" | "mail" | "both"
- estimated_payout: str or null

Respond with ONLY the JSON object, no other text.
"""


def load_document_text(file_path: str) -> str:
    """Load document text from HTML or text file."""
    path = Path(file_path)

    if path.suffix.lower() == ".html":
        from bs4 import BeautifulSoup

        content = path.read_text(errors="replace")
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    if path.suffix.lower() == ".pdf":
        logger.warning("PDF loading not fully implemented. Reading as text.")
        return path.read_text(errors="replace")

    return path.read_text(errors="replace")


def chunk_text(text: str, chunk_size: int = 15000, overlap: int = 1000) -> list[str]:
    """Split text into overlapping chunks for LLM processing."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


async def extract_settlement_rules(
    document_path: str,
    llm_client=None,
) -> Optional[SettlementRules]:
    """Extract structured settlement rules from a document using an LLM."""
    try:
        text = load_document_text(document_path)
        if not text or len(text.strip()) < 100:
            logger.warning(f"Document too short or empty: {document_path}")
            return None

        primary_text = chunk_text(text)[0]
        prompt = EXTRACTION_PROMPT.format(document_text=primary_text)

        if llm_client is None:
            try:
                llm_client = get_llm_client()
            except Exception as e:
                logger.error(f"Failed to create LLM client: {e}")
                return None

        return await ainvoke_pydantic(llm_client, prompt, SettlementRules)

    except Exception as e:
        logger.error(f"Extraction failed for {document_path}: {e}")
        return None
