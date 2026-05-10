"""Integration tests for the Eng2Biz pipeline."""

import json
import pytest
from unittest.mock import MagicMock, patch
from src.core.schemas import PipelineResult, GSMBrief, RefusalResponse


class TestPipelineResult:
    """Test PipelineResult data model."""

    def test_pipeline_result_creation(self):
        result = PipelineResult(
            case_id="CASE-01",
            input_text="test ECO",
            is_published=True,
            latency_seconds=5.2,
            total_tokens=3000,
            estimated_cost_usd=0.025,
        )
        assert result.case_id == "CASE-01"
        assert result.is_published is True
        assert result.latency_seconds == 5.2

    def test_pipeline_result_with_brief(self):
        brief = GSMBrief(
            overall_confidence=0.89,
            chain_of_thought="Step 1: Physical impact...",
        )
        result = PipelineResult(
            case_id="CASE-01",
            input_text="test",
            brief=brief,
            is_published=True,
        )
        assert result.brief is not None
        assert result.brief.overall_confidence == 0.89

    def test_pipeline_result_with_refusal(self):
        refusal = RefusalResponse(
            reason="Insufficient information",
            missing_info=["Supplier ID", "Part number"],
        )
        result = PipelineResult(
            case_id="FAIL-01",
            input_text="vague message",
            refusal=refusal,
            is_published=False,
        )
        assert result.refusal is not None
        assert result.is_published is False
        assert len(result.refusal.missing_info) == 2

    def test_pipeline_result_serialization(self):
        result = PipelineResult(
            case_id="CASE-01",
            input_text="test",
            is_published=True,
        )
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["case_id"] == "CASE-01"


class TestGSMBrief:
    """Test GSMBrief data model."""

    def test_brief_defaults(self):
        brief = GSMBrief()
        assert brief.overall_confidence == 0.0
        assert brief.cost_impact.trend.value == "NEUTRAL"
        assert len(brief.recommended_actions) == 0

    def test_brief_with_actions(self):
        from src.core.schemas import RecommendedAction
        brief = GSMBrief(
            overall_confidence=0.85,
            recommended_actions=[
                RecommendedAction(
                    action="Reject NRE claim",
                    owner="Sr. GSM",
                    confidence=0.92,
                    requires_approval_from=None,
                ),
                RecommendedAction(
                    action="Kick off requal",
                    owner="GSM",
                    confidence=0.88,
                ),
            ],
        )
        assert len(brief.recommended_actions) == 2
        assert brief.recommended_actions[0].owner == "Sr. GSM"


class TestRefusalResponse:
    """Test RefusalResponse data model."""

    def test_refusal_creation(self):
        refusal = RefusalResponse(
            reason="Ambiguous supplier",
            missing_info=["Supplier MSA number"],
            required_clarifications=["Please provide supplier ID"],
        )
        assert refusal.is_refusal is True
        assert "Ambiguous" in refusal.reason
