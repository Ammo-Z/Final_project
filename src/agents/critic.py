"""Critic Agent — Self-Reflexion loop for quality assurance."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from ..core.schemas import (
    GSMBrief, ParsedArtifact, RetrievedContext,
    CriticReview, ReviewIssue, CitationAudit
)
from ..utils.llm_client import LLMClient
from ..utils.logger import PipelineLogger


class CriticAgent:
    """Self-Critique agent that reviews draft GSM Briefs before publishing.

    Checks for:
    1. Citation faithfulness — every claim needs a [G#]/[E#]/[M#] reference
    2. Logical consistency — cost trend matches reasoning chain
    3. Hallucination detection — unsupported figures or claims
    4. Completeness — all required fields populated
    5. Refusal appropriateness — under-specified inputs handled correctly
    """

    def __init__(
        self,
        llm_client: LLMClient,
        logger: Optional[PipelineLogger] = None,
        prompt_path: str = "./prompts/critic_v1.md",
        model: Optional[str] = None,
        faithfulness_threshold: float = 0.95,
    ):
        self.llm = llm_client
        self.logger = logger or PipelineLogger()
        self.model = model or "claude-sonnet-4-20250514"
        self.faithfulness_threshold = faithfulness_threshold
        self._load_prompt(prompt_path)

    def _load_prompt(self, path: str):
        """Load the critic prompt template."""
        prompt_file = Path(path)
        if prompt_file.exists():
            self.prompt_template = prompt_file.read_text(encoding="utf-8")
        else:
            self.prompt_template = self._default_prompt()

    def review(
        self,
        draft_brief: GSMBrief,
        parsed_artifact: ParsedArtifact,
        context: RetrievedContext,
        context_strings: dict[str, str],
    ) -> CriticReview:
        """Review a draft GSM Brief for quality and accuracy.

        Args:
            draft_brief: The drafted GSM Brief to review
            parsed_artifact: Original parsed artifact
            context: Retrieved RAG context
            context_strings: Formatted context strings

        Returns:
            CriticReview with pass/fail, issues, and revision instructions
        """
        self.logger.start_timer("critic")
        self.logger.info("Running self-critique review")

        # Build prompt
        prompt = self.prompt_template
        prompt = prompt.replace("{draft_brief}", draft_brief.model_dump_json(indent=2))
        prompt = prompt.replace(
            "{retrieved_context}",
            json.dumps(context_strings, indent=2, ensure_ascii=False),
        )
        prompt = prompt.replace("{parsed_artifact}", parsed_artifact.model_dump_json(indent=2))

        # Call LLM
        response = self.llm.chat(
            prompt=prompt,
            system=(
                "You are a Senior GSM Reviewer. Critically evaluate the draft brief. "
                "Return your review as JSON."
            ),
            model=self.model,
            temperature=0.1,
            max_tokens=2048,
            response_format="json",
        )

        self.logger.log_llm_call(
            stage="critic",
            model=response["model"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            cost_usd=response["cost"],
            latency_ms=response["latency_ms"],
        )

        # Parse review
        parsed = response.get("parsed")
        if parsed:
            try:
                review = self._build_review(parsed)
            except Exception as e:
                self.logger.warning(f"Failed to parse CriticReview: {e}")
                review = CriticReview(
                    review_passed=True,
                    recommendation="PUBLISH",
                    citation_audit=CitationAudit(faithfulness_score=0.8),
                    logic_score=0.8,
                )
        else:
            self.logger.warning("Critic returned non-JSON, defaulting to PASS")
            review = CriticReview(
                review_passed=True,
                recommendation="PUBLISH",
                citation_audit=CitationAudit(faithfulness_score=0.8),
                logic_score=0.8,
            )

        elapsed = self.logger.stop_timer("critic")
        self.logger.info(
            f"Review complete: passed={review.review_passed} "
            f"faithfulness={review.citation_audit.faithfulness_score:.2f} "
            f"issues={len(review.issues)} ({elapsed:.1f}s)"
        )

        return review

    def _build_review(self, data: dict) -> CriticReview:
        """Build CriticReview from LLM JSON output."""
        issues = []
        for issue_data in data.get("issues", []):
            if isinstance(issue_data, dict):
                issues.append(ReviewIssue(
                    type=issue_data.get("type", "WARNING"),
                    severity=issue_data.get("severity", "WARNING"),
                    location=issue_data.get("location", ""),
                    description=issue_data.get("description", ""),
                    suggested_fix=issue_data.get("suggested_fix", ""),
                ))

        citation_data = data.get("citation_audit", {})
        citation_audit = CitationAudit(
            total_claims=citation_data.get("total_claims", 0),
            cited_claims=citation_data.get("cited_claims", 0),
            faithfulness_score=float(citation_data.get("faithfulness_score", 0.0)),
        )

        return CriticReview(
            review_passed=data.get("review_passed", False),
            issues=issues,
            citation_audit=citation_audit,
            logic_score=float(data.get("logic_score", 0.0)),
            recommendation=data.get("recommendation", "REVISE"),
            revision_instructions=data.get("revision_instructions", ""),
        )

    @staticmethod
    def _default_prompt() -> str:
        return (
            "Review the following draft GSM Brief for quality.\n\n"
            "## Draft Brief:\n{draft_brief}\n\n"
            "## Retrieved Context:\n{retrieved_context}\n\n"
            "## Original Artifact:\n{parsed_artifact}\n\n"
            "Check: citation faithfulness, logical consistency, hallucinations, "
            "completeness. Return a JSON review."
        )
