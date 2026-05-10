"""Unit tests for the ECO Parser module."""

import json
import pytest
from unittest.mock import MagicMock, patch
from src.core.parser import ECOParser
from src.core.schemas import ParsedArtifact, ArtifactType, Commodity


class TestECOParser:
    """Test suite for the structural parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_llm = MagicMock()
        self.parser = ECOParser(llm_client=self.mock_llm)

    def test_parse_returns_parsed_artifact(self):
        """Parser should return a ParsedArtifact object."""
        self.mock_llm.chat.return_value = {
            "content": "{}",
            "parsed": {
                "artifact_id": "ECO-24817",
                "artifact_type": "ECO",
                "commodity": "battery",
                "supplier_id": "SUP-001",
                "part_number": "BAT-001-A",
                "entities": {"materials": [], "tolerances": []},
                "raw_text": "test input",
                "parse_confidence": 0.85,
                "ambiguities": [],
            },
            "input_tokens": 100,
            "output_tokens": 200,
            "cost": 0.001,
            "latency_ms": 500,
            "model": "test",
        }

        result = self.parser.parse("ECO-24817: Change cathode binder")
        assert isinstance(result, ParsedArtifact)
        assert result.artifact_id == "ECO-24817"
        assert result.parse_confidence == 0.85

    def test_parse_low_confidence_on_vague_input(self):
        """Vague inputs should get low parse confidence."""
        self.mock_llm.chat.return_value = {
            "content": "{}",
            "parsed": {
                "artifact_type": "OTHER",
                "commodity": "OTHER",
                "parse_confidence": 0.25,
                "ambiguities": ["No artifact ID", "No supplier"],
                "raw_text": "vague text",
                "entities": {},
            },
            "input_tokens": 100,
            "output_tokens": 200,
            "cost": 0.001,
            "latency_ms": 500,
            "model": "test",
        }

        result = self.parser.parse("Something about a vendor issue")
        assert result.parse_confidence < 0.5
        assert len(result.ambiguities) > 0

    def test_parse_handles_json_failure(self):
        """Parser should handle non-JSON LLM responses gracefully."""
        self.mock_llm.chat.return_value = {
            "content": "I cannot parse this input",
            "parsed": None,
            "input_tokens": 100,
            "output_tokens": 50,
            "cost": 0.001,
            "latency_ms": 500,
            "model": "test",
        }

        result = self.parser.parse("gibberish input")
        assert isinstance(result, ParsedArtifact)
        assert result.parse_confidence == 0.3


class TestParserInputTypes:
    """Test parser with different artifact types."""

    def setup_method(self):
        self.mock_llm = MagicMock()
        self.parser = ECOParser(llm_client=self.mock_llm)

    def _mock_response(self, artifact_type, commodity, confidence):
        self.mock_llm.chat.return_value = {
            "content": "{}",
            "parsed": {
                "artifact_type": artifact_type,
                "commodity": commodity,
                "parse_confidence": confidence,
                "ambiguities": [],
                "raw_text": "test",
                "entities": {},
            },
            "input_tokens": 100,
            "output_tokens": 200,
            "cost": 0.001,
            "latency_ms": 500,
            "model": "test",
        }

    def test_eco_artifact(self):
        self._mock_response("ECO", "battery", 0.9)
        result = self.parser.parse("ECO-24817: Change PVDF binder")
        assert result.artifact_type == ArtifactType.ECO

    def test_pcn_artifact(self):
        self._mock_response("PCN", "display", 0.85)
        result = self.parser.parse("PCN-2025-0342: Display driver EOL")
        assert result.artifact_type == ArtifactType.PCN

    def test_yield_artifact(self):
        self._mock_response("YIELD", "enclosure", 0.8)
        result = self.parser.parse("Yield excursion on anodize line")
        assert result.artifact_type == ArtifactType.YIELD
