"""Evaluation Orchestrator — Run full evaluation pipeline on test cases."""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.pipeline import Eng2BizPipeline
from src.core.schemas import EvalResult, PipelineResult
from src.evaluation.judge import ModelJudge
from src.evaluation.metrics import compute_evaluation_report
from src.utils.llm_client import LLMClient
from src.utils.logger import PipelineLogger


class EvaluationRunner:
    """Orchestrate full evaluation: run pipeline → judge → aggregate metrics."""

    def __init__(
        self,
        config_path: str = "./configs/settings.yaml",
        provider: str = "anthropic",
    ):
        self.logger = PipelineLogger(level="INFO")
        self.pipeline = Eng2BizPipeline(config_path=config_path, provider=provider)
        self.llm = LLMClient(provider=provider)
        self.judge = ModelJudge(llm_client=self.llm, logger=self.logger)

    def run_evaluation(
        self,
        test_cases_path: str,
        output_path: Optional[str] = None,
        run_baseline: bool = True,
    ) -> dict:
        """Run full evaluation on test set.

        Args:
            test_cases_path: Path to test_cases_30.json
            output_path: Optional path to save results
            run_baseline: Whether to also run prompt-only baseline

        Returns:
            Complete evaluation report
        """
        # Load test cases
        with open(test_cases_path, "r", encoding="utf-8") as f:
            test_cases = json.load(f)

        self.logger.info(f"Loaded {len(test_cases)} test cases")

        # ── Run System ──
        self.logger.info("=" * 60)
        self.logger.info("Running SYSTEM evaluation")
        self.logger.info("=" * 60)

        system_results: list[PipelineResult] = []
        system_eval_results: list[EvalResult] = []

        for i, case in enumerate(test_cases):
            case_id = case.get("case_id", f"CASE-{i+1:02d}")
            input_text = case.get("input_artifact", "")
            gold_brief = case.get("gold_brief", {})
            expected = case.get("expected_behavior", "PUBLISH")

            self.logger.info(f"\n[{i+1}/{len(test_cases)}] {case_id}")

            # Run pipeline
            start = time.time()
            result = self.pipeline.run(input_text, case_id=case_id)
            system_results.append(result)

            # Prepare system output for judging
            if result.refusal:
                system_output = result.refusal.model_dump()
            elif result.brief:
                system_output = result.brief.model_dump()
            else:
                system_output = {}

            # Judge
            eval_result = self.judge.evaluate_case(
                case_id=case_id,
                system_output=system_output,
                gold_standard=gold_brief,
                input_artifact=input_text,
            )
            system_eval_results.append(eval_result)

            self.logger.info(
                f"  Score: {eval_result.overall_score:.2f} | "
                f"Latency: {result.latency_seconds:.1f}s | "
                f"Cost: ${result.estimated_cost_usd:.4f}"
            )

        # ── Run Baseline (Prompt-Only) ──
        baseline_eval_results = None
        if run_baseline:
            self.logger.info("\n" + "=" * 60)
            self.logger.info("Running BASELINE evaluation (prompt-only, no RAG)")
            self.logger.info("=" * 60)
            baseline_eval_results = self._run_baseline(test_cases)

        # ── Aggregate Results ──
        self.logger.info("\n" + "=" * 60)
        self.logger.info("Computing evaluation report")
        self.logger.info("=" * 60)

        report = compute_evaluation_report(
            results=system_eval_results,
            baseline_results=baseline_eval_results,
        )

        # Add per-case details
        report["per_case"] = []
        for i, (case, eval_r, pipe_r) in enumerate(
            zip(test_cases, system_eval_results, system_results)
        ):
            report["per_case"].append({
                "case_id": case.get("case_id"),
                "artifact_type": case.get("artifact_type"),
                "commodity": case.get("commodity"),
                "expected": case.get("expected_behavior"),
                "actual": "REFUSAL" if pipe_r.refusal else "PUBLISH",
                "overall_score": eval_r.overall_score,
                "scores": {k: v.model_dump() for k, v in eval_r.scores.items()},
                "latency_s": pipe_r.latency_seconds,
                "cost_usd": pipe_r.estimated_cost_usd,
                "critical_failures": eval_r.critical_failures,
            })

        # Print summary
        self._print_summary(report)

        # Save results
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"\nResults saved to {output_path}")

        return report

    def _run_baseline(self, test_cases: list[dict]) -> list[EvalResult]:
        """Run prompt-only baseline (no RAG, no agentic loop)."""
        baseline_results = []

        for i, case in enumerate(test_cases):
            case_id = case.get("case_id", f"CASE-{i+1:02d}")
            input_text = case.get("input_artifact", "")
            gold_brief = case.get("gold_brief", {})

            self.logger.info(f"  Baseline [{i+1}/{len(test_cases)}] {case_id}")

            # Simple zero-shot prompt
            response = self.llm.chat(
                prompt=(
                    f"You are a supply chain expert. Analyze this engineering change "
                    f"and provide a commercial impact assessment:\n\n{input_text}\n\n"
                    f"Provide: translation, cost impact, schedule impact, risk, "
                    f"and recommended actions as JSON."
                ),
                model="claude-sonnet-4-20250514",
                temperature=0.3,
                max_tokens=2048,
                response_format="json",
            )

            system_output = response.get("parsed", {}) or {}

            eval_result = self.judge.evaluate_case(
                case_id=case_id,
                system_output=system_output,
                gold_standard=gold_brief,
                input_artifact=input_text,
            )
            baseline_results.append(eval_result)

        return baseline_results

    def _print_summary(self, report: dict):
        """Print a formatted evaluation summary."""
        sys_scores = report.get("system_scores", {})

        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)
        print(f"Total cases: {report.get('total_cases', 0)}")
        print(f"Published: {report.get('published_cases', 0)}")
        print(f"Refusals: {report.get('refusal_cases', 0)}")
        print()

        print("Dimension Scores (System):")
        print("-" * 50)
        for dim in ["translation_accuracy", "completeness", "citation_faithfulness",
                     "action_usefulness", "refusal_correctness"]:
            s = sys_scores.get(dim, {})
            print(f"  {dim:25s}  mean={s.get('mean', 0):.2f}  std={s.get('std', 0):.2f}")

        overall = sys_scores.get("overall", {})
        print(f"\n  {'OVERALL':25s}  mean={overall.get('mean', 0):.2f}  std={overall.get('std', 0):.2f}")
        print(f"  Win rate vs Gold: {sys_scores.get('win_rate', 0):.1%}")

        if "baseline_scores" in report:
            base_overall = report["baseline_scores"].get("overall", {})
            print(f"\n  Baseline OVERALL: mean={base_overall.get('mean', 0):.2f}")

        if "bootstrap_test" in report:
            bt = report["bootstrap_test"]
            print(f"\n  Bootstrap test: diff={bt['mean_diff']:.3f} "
                  f"CI=[{bt['ci_lower']:.3f}, {bt['ci_upper']:.3f}] "
                  f"p={bt['p_value']:.4f} "
                  f"{'*SIGNIFICANT*' if bt['significant'] else 'not significant'}")

        if "cohens_kappa" in report and report["cohens_kappa"] is not None:
            print(f"\n  Cohen's κ (judge-human): {report['cohens_kappa']:.3f}")

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="ECO-Impact Interpreter Evaluation")
    parser.add_argument(
        "--test-set", "-t",
        type=str,
        default="./data/test_cases/test_cases_30.json",
        help="Path to test cases JSON",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./evaluation_results.json",
        help="Output path for results",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="Skip baseline evaluation",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="anthropic",
        help="LLM provider",
    )

    args = parser.parse_args()

    runner = EvaluationRunner(provider=args.provider)
    runner.run_evaluation(
        test_cases_path=args.test_set,
        output_path=args.output,
        run_baseline=not args.no_baseline,
    )


if __name__ == "__main__":
    main()
