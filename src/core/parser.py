"""Structural Parser — Extract technical entities from raw engineering artifacts."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import PipelineLogger
from .schemas import ParsedArtifact


class ECOParser:
    """Parse raw engineering text into structured entities using LLM."""

    def __init__(
        self,
        llm_client: LLMClient,
        logger: Optional[PipelineLogger] = None,
        prompt_path: str = "./prompts/parser_v1.md",
        model: Optional[str] = None,
    ):
        self.llm = llm_client
        self.logger = logger or PipelineLogger()
        self.model = model or "claude-sonnet-4-20250514"
        self._load_prompt(prompt_path)

    def _load_prompt(self, path: str):
        """Load the parser prompt template."""
        prompt_file = Path(path)
        if prompt_file.exists():
            self.prompt_template = prompt_file.read_text(encoding="utf-8")
        else:
            # Fallback inline prompt
            self.prompt_template = (
                "You are a manufacturing engineering parser. Extract structured "
                "technical entities from the following engineering artifact text. "
                "Return a JSON object with fields: artifact_id, artifact_type, "
                "commodity, supplier_id, part_number, entities (materials, tolerances, "
                "processes, specifications, cost_signals, schedule_signals, risk_indicators), "
                "raw_text, parse_confidence, ambiguities.\n\n"
                "Input Artifact:\n{input_text}"
            )

    def parse(self, input_text: str) -> ParsedArtifact:
        """Parse raw engineering text into structured artifact.

        Args:
            input_text: Raw ECO/PCN/DFM/FA text

        Returns:
            ParsedArtifact with extracted entities and confidence score
        """
        self.logger.start_timer("parser")
        self.logger.info(f"Parsing artifact ({len(input_text)} chars)")

        # Build prompt
        prompt = self.prompt_template.replace("{input_text}", input_text)

        # Call LLM
        response = self.llm.chat(
            prompt=prompt,
            system="You are a manufacturing engineering parser. Return ONLY valid JSON.",
            model=self.model,
            temperature=0.1,
            max_tokens=2048,
            response_format="json",
        )

        # Log usage
        self.logger.log_llm_call(
            stage="parser",
            model=response["model"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            cost_usd=response["cost"],
            latency_ms=response["latency_ms"],
        )

        # Parse response
        parsed_data = response.get("parsed")
        if parsed_data is None:
            self.logger.warning("Parser returned non-JSON response, using fallback")
            parsed = ParsedArtifact(
                raw_text=input_text,
                parse_confidence=0.3,
                ambiguities=["Failed to parse LLM response as JSON"],
            )
        else:
            try:
                parsed = self._build_artifact(parsed_data, input_text)
            except Exception as e:
                self.logger.error(f"Error building ParsedArtifact: {e}")
                parsed = ParsedArtifact(
                    raw_text=input_text,
                    parse_confidence=0.3,
                    ambiguities=[f"Parse error: {str(e)}"],
                )

        elapsed = self.logger.stop_timer("parser")
        self.logger.info(
            f"Parse complete: type={parsed.artifact_type.value} "
            f"commodity={parsed.commodity.value} "
            f"confidence={parsed.parse_confidence:.2f} "
            f"({elapsed:.1f}s)"
        )

        return parsed

    def _build_artifact(self, data: dict, raw_text: str) -> ParsedArtifact:
        """Build ParsedArtifact from LLM JSON output."""
        # Handle entities sub-object
        entities_data = data.get("entities", {})

        return ParsedArtifact(
            artifact_id=data.get("artifact_id"),
            artifact_type=data.get("artifact_type", "OTHER"),
            commodity=data.get("commodity", "OTHER"),
            supplier_id=data.get("supplier_id"),
            part_number=data.get("part_number"),
            entities=entities_data,
            raw_text=raw_text,
            parse_confidence=float(data.get("parse_confidence", 0.5)),
            ambiguities=data.get("ambiguities", []),
        )
