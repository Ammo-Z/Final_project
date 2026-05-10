"""Drafting Agent — Chain-of-Thought analysis to produce GSM Brief."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from ..core.schemas import (
    GSMBrief, ParsedArtifact, RetrievedContext, RefusalResponse
)
from ..utils.llm_client import LLMClient
from ..utils.logger import PipelineLogger


class DraftingAgent:
    """CoT Drafting Agent that produces GSM Briefs from parsed artifacts + RAG context.

    Uses Chain-of-Thought reasoning to simulate the logic of a veteran
    manufacturing expert:
    1. Physical Impact Analysis
    2. Manufacturing Process Change mapping
    3. Cost Driver Identification
    """

    def __init__(
        self,
        llm_client: LLMClient,
        logger: Optional[PipelineLogger] = None,
        prompt_path: str = "./prompts/drafting_v1.md",
        model: Optional[str] = None,
        confidence_threshold: float = 0.5,
    ):
        self.llm = llm_client
        self.logger = logger or PipelineLogger()
        self.model = model or "claude-sonnet-4-20250514"
        self.confidence_threshold = confidence_threshold
        self._load_prompt(prompt_path)

    def _load_prompt(self, path: str):
        """Load the drafting prompt template."""
        prompt_file = Path(path)
        if prompt_file.exists():
            self.prompt_template = prompt_file.read_text(encoding="utf-8")
        else:
            self.prompt_template = self._default_prompt()

    def draft(
        self,
        parsed_artifact: ParsedArtifact,
        context: RetrievedContext,
        context_strings: dict[str, str],
    ) -> GSMBrief | RefusalResponse:
        """Generate a GSM Brief or Refusal from parsed artifact and context.

        Args:
            parsed_artifact: Structured parser output
            context: Retrieved RAG chunks
            context_strings: Formatted context strings for prompt injection

        Returns:
            GSMBrief if sufficient info, RefusalResponse otherwise
        """
        self.logger.start_timer("drafter")

        # Check refusal threshold
        if parsed_artifact.parse_confidence < self.confidence_threshold:
            self.logger.info(
                f"Parse confidence {parsed_artifact.parse_confidence:.2f} "
                f"< threshold {self.confidence_threshold:.2f} — issuing REFUSAL"
            )
            refusal = self._generate_refusal(parsed_artifact)
            self.logger.stop_timer("drafter")
            return refusal

        self.logger.info("Drafting GSM Brief via Chain-of-Thought")

        # Build prompt
        prompt = self.prompt_template
        prompt = prompt.replace("{glossary_context}", context_strings.get("glossary_context", ""))
        prompt = prompt.replace("{eco_corpus_context}", context_strings.get("eco_corpus_context", ""))
        prompt = prompt.replace("{msa_context}", context_strings.get("msa_context", ""))
        prompt = prompt.replace("{parsed_artifact}", parsed_artifact.model_dump_json(indent=2))

        # Call LLM
        response = self.llm.chat(
            prompt=prompt,
            system=(
                "You are Eng2Biz, an expert manufacturing engineering advisor. "
                "Produce a structured GSM Brief as JSON. Follow Chain-of-Thought reasoning."
            ),
            model=self.model,
            temperature=0.3,
            max_tokens=4096,
            response_format="json",
        )

        self.logger.log_llm_call(
            stage="drafter",
            model=response["model"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            cost_usd=response["cost"],
            latency_ms=response["latency_ms"],
        )

        # Parse response into GSMBrief
        parsed = response.get("parsed")
        if parsed:
            try:
                brief = GSMBrief(**parsed)
            except Exception as e:
                self.logger.warning(f"Failed to parse GSMBrief: {e}, using partial data")
                brief = self._partial_brief(parsed)
        else:
            self.logger.warning("Drafter returned non-JSON, constructing from text")
            brief = GSMBrief(
                chain_of_thought=response["content"],
                overall_confidence=0.5,
            )

        elapsed = self.logger.stop_timer("drafter")
        self.logger.info(
            f"Draft complete: confidence={brief.overall_confidence:.2f} "
            f"actions={len(brief.recommended_actions)} ({elapsed:.1f}s)"
        )

        return brief

    def _generate_refusal(self, artifact: ParsedArtifact) -> RefusalResponse:
        """Generate a structured refusal response."""
        missing = []
        if not artifact.supplier_id:
            missing.append("Supplier ID or MSA number")
        if not artifact.part_number:
            missing.append("Part number or commodity")
        if not artifact.artifact_id:
            missing.append("Artifact reference (ECO#, PCN#, FA#)")
        if not artifact.entities.materials and not artifact.entities.processes:
            missing.append("Technical change description (materials, processes, tolerances)")

        clarifications = [
            f"Please provide: {item}" for item in missing
        ]
        if artifact.ambiguities:
            clarifications.extend(
                f"Clarify: {amb}" for amb in artifact.ambiguities
            )

        return RefusalResponse(
            is_refusal=True,
            reason=(
                f"Insufficient information to generate a reliable GSM Brief. "
                f"Parse confidence: {artifact.parse_confidence:.2f}"
            ),
            missing_info=missing,
            required_clarifications=clarifications,
        )

    def _partial_brief(self, data: dict) -> GSMBrief:
        """Build a partial GSMBrief from incomplete data."""
        brief = GSMBrief()
        if "translation" in data:
            if isinstance(data["translation"], dict):
                brief.translation.en = data["translation"].get("en", "")
                brief.translation.zh = data["translation"].get("zh", "")
        if "cost_impact" in data and isinstance(data["cost_impact"], dict):
            brief.cost_impact.trend = data["cost_impact"].get("trend", "NEUTRAL")
            brief.cost_impact.reasoning = data["cost_impact"].get("reasoning", "")
        if "overall_confidence" in data:
            brief.overall_confidence = float(data["overall_confidence"])
        if "chain_of_thought" in data:
            brief.chain_of_thought = data["chain_of_thought"]
        if "recommended_actions" in data and isinstance(data["recommended_actions"], list):
            from ..core.schemas import RecommendedAction
            for action_data in data["recommended_actions"]:
                if isinstance(action_data, dict):
                    brief.recommended_actions.append(
                        RecommendedAction(
                            action=action_data.get("action", ""),
                            owner=action_data.get("owner", "GSM"),
                            confidence=float(action_data.get("confidence", 0.5)),
                        )
                    )
        return brief

    @staticmethod
    def _default_prompt() -> str:
        return (
            "Given a parsed engineering artifact and retrieved knowledge context, "
            "produce a structured GSM Brief.\n\n"
            "## Retrieved Context\n"
            "### Glossary:\n{glossary_context}\n\n"
            "### ECO Precedents:\n{eco_corpus_context}\n\n"
            "### MSA Clauses:\n{msa_context}\n\n"
            "## Parsed Artifact:\n{parsed_artifact}\n\n"
            "Reason step by step (Physical Impact → Process Change → Cost Drivers) "
            "then output a complete GSM Brief as JSON."
        )
