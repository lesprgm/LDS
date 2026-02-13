"""Unit tests for extraction schemas and document processing."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from pydantic import ValidationError

from extraction.schemas import SettlementRules
from extraction.settlement_extractor import chunk_text, load_document_text


class TestSettlementRulesSchema:
    def test_valid_full_record(self):
        rules = SettlementRules(
            settlement_name="Visa/MC Settlement",
            administrator="Epiq",
            defendant="Visa Inc.",
            case_number="1:05-md-01720",
            summary="Settlement for merchants who accepted Visa or Mastercard.",
            eligible_class_description="All merchants who accepted Visa or Mastercard between Jan 2004 and Jan 2019.",
            eligible_industries=["restaurant", "retail", "salon"],
            eligible_geography="United States",
            eligible_time_period="January 2004 - January 2019",
            eligible_actions=["Accepted Visa or Mastercard credit/debit cards"],
            exclusions=["Government entities", "Visa/MC subsidiaries"],
            proof_required=["Merchant processing statements", "Business tax records"],
            proof_difficulty="moderate",
            claim_deadline="2025-08-30",
            claim_window_status="open",
            smb_relevance="high",
            smb_relevance_reason="Most small businesses accept card payments",
            clarity_score=8,
            claim_url="https://example.com/claim",
            claim_method="online",
            estimated_payout="$500 - $50,000 depending on volume",
        )
        assert rules.settlement_name == "Visa/MC Settlement"
        assert rules.clarity_score == 8
        assert "restaurant" in rules.eligible_industries

    def test_minimal_valid_record(self):
        rules = SettlementRules(
            settlement_name="Test Settlement",
            administrator="Test Admin",
            defendant="Test Corp",
            summary="A test settlement.",
            eligible_class_description="Anyone who bought widgets.",
        )
        assert rules.proof_difficulty == "moderate"
        assert rules.claim_window_status == "open"
        assert rules.smb_relevance == "medium"

    def test_rejects_invalid_clarity_score_too_high(self):
        with pytest.raises(ValidationError):
            SettlementRules(
                settlement_name="Test",
                administrator="Admin",
                defendant="Defendant",
                summary="Summary",
                eligible_class_description="Description",
                clarity_score=11,
            )

    def test_rejects_invalid_clarity_score_too_low(self):
        with pytest.raises(ValidationError):
            SettlementRules(
                settlement_name="Test",
                administrator="Admin",
                defendant="Defendant",
                summary="Summary",
                eligible_class_description="Description",
                clarity_score=0,
            )


class TestChunkText:
    def test_short_text_single_chunk(self):
        chunks = chunk_text("Hello world", chunk_size=100)
        assert chunks == ["Hello world"]

    def test_long_text_splits(self):
        text = "A" * 10000
        chunks = chunk_text(text, chunk_size=4000, overlap=400)
        assert len(chunks) > 1
        assert all(len(c) <= 4000 for c in chunks)


class TestLoadDocumentText:
    def test_load_plain_text(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello, this is a test document.")
            f.flush()
            result = load_document_text(f.name)
        assert "Hello, this is a test document." in result
        os.unlink(f.name)

    def test_load_html(self):
        html = """<html><body><script>var x=1;</script><p>Settlement details here.</p><footer>Copyright</footer></body></html>"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html)
            f.flush()
            result = load_document_text(f.name)
        assert "Settlement details here" in result
        assert "var x" not in result
        os.unlink(f.name)
