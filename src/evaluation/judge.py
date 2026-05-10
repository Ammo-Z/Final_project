"""Model-as-a-Judge — Automated evaluation using LLM scoring."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from ..core.schemas import EvalResult, DimensionScore
from ..utils.llm_client import LLMClient
from ..utils.logger import PipelineLogger


class ModelJudge:
    """Automated scoring of system outputs against Gold Standard briefs.

    Uses a high-reasoning LLM to score each case across 6 dimensions:
    1. Translation Accuracy (1-5)
    2. Completeness (1-5)
    3. Citation Faithfulness (1-5)
    4. Action Usefulness (1-5)
    5. Refusal Correctness (0-1)
    6. Latency/Cost (informational)
    """

    def __init__(
        self,
        llm_client: LLMClient,
        logger: Optional[PipelineLogger] = None,
        prompt_path: str = "./prompts/judge_v1.md",
        model: Optional[str] = None,
    ):
        self.llm = llm_client
        self.logger = logger or PipelineLogger()
        self.model = model or "claude-sonnet-4-20250514"
        self._load_prompt(prompt_path)

    def _load_prompt(self, path: str):
        """Load the judge prompt template."""
        prompt_file = Path(path)
        if prompt_file.exists():
            self.prompt_template = prompt_file.read_text(encoding="utf-8")
        else:
            self.prompt_template = (
                "Score the system output against the gold standard.\n\n"
                "System Output:\n{system_output}\n\n"
                "Gold Standard:\n{gold_standard}\n\n"
                "Original Input:\n{input_artifact}\n\n"
                "Score on: translation_accuracy (1-5), completeness (1-5), "
                "citation_faithfulness (1-5), action_usefulness (1-5), "
                "refusal_correctness (0-1). Return JSON."
            )

    def evaluate_case(
        self,
        case_id: str,
        system_output: dict,
        gold_standard: dict,
        input_artifact: str,
    ) -> EvalResult:
        """Evaluate a single case.

        Args:
            case_id: Test case identifier
            system_output: Pipeline output (brief or refusal)
            gold_standard: Expected Gold Standard output
            input_artifact: Original input text

        Returns:
            EvalResult with dimension scores and overall assessment
        """
        self.logger.info(f"Evaluating {case_id}")

        prompt = self.prompt_template
        prompt = prompt.replace("{system_output}", json.dumps(system_output, indent=2, ensure_ascii=False))
        prompt = prompt.replace("{gold_standard}", json.dumps(gold_standard, indent=2, ensure_ascii=False))
        prompt = prompt.replace("{input_artifact}", input_artifact)

        response = self.llm.chat(
            prompt=prompt,
            system="You are an expert evaluator. Score the system output objectively. Return only valid JSON.",
            model=self.model,
            temperature=0.0,
            max_tokens=2048,
            response_format="json",
        )

        self.logger.log_llm_call(
            stage="judge",
            model=response["model"],
            input_tokens=response["input_tokens"],
            output_tokens=response["output_tokens"],
            cost_usd=response["cost"],
            latency_ms=response["latency_ms"],
        )

        parsed = response.get("parsed")
        if parsed:
            return self._build_eval_result(case_id, parsed)
        else:
            self.logger.warning(f"Judge returned non-JSON for {case_id}")
            return EvalResult(case_id=case_id, overall_score=0.0)

    def _build_eval_result(self, case_id: str, data: dict) -> EvalResult:
        """Build EvalResult from judge JSON."""
        scores = {}
        scores_data = data.get("scores", {})
        for dim, score_info in scores_data.items():
            if isinstance(score_info, dict):
                scores[dim] = DimensionScore(
                    score=float(score_info.get("score", 0)),
                    justification=score_info.get("justification", ""),
                )
            elif isinstance(score_info, (int, float)):
                scores[dim] = DimensionScore(score=float(score_info))

        # Calculate overall score
        rubric_scores = [s.score for s in scores.values() if s.score > 0]
        overall = sum(rubric_scores) / len(rubric_scores) if rubric_scores else 0.0

        return EvalResult(
            case_id=case_id,
            scores=scores,
            overall_score=data.get("overall_score", overall),
            win_vs_gold=data.get("win_vs_gold", False),
            critical_failures=data.get("critical_failures", []),
            improvement_suggestions=data.get("improvement_suggestions", []),
        )
