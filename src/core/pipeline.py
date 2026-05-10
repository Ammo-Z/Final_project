"""End-to-end Eng2Biz Pipeline — Orchestrates parse → retrieve → draft → critique → finalize."""

from __future__ import annotations
import argparse
import json
import time
import sys
from pathlib import Path
from typing import Optional

import yaml

from .schemas import (
    PipelineResult, GSMBrief, RefusalResponse,
    ParsedArtifact, RetrievedContext
)
from .parser import ECOParser
from ..rag.retriever import MultiIndexRetriever
from ..agents.drafter import DraftingAgent
from ..agents.critic import CriticAgent
from ..utils.llm_client import LLMClient
from ..utils.logger import PipelineLogger


class Eng2BizPipeline:
    """Main pipeline orchestrating the 5-stage agentic workflow.

    Stages:
        1. Parse — Extract entities from raw engineering text
        2. Retrieve — Query triple-index RAG knowledge base
        3. Draft — CoT reasoning to produce GSM Brief
        4. Critique — Self-reflexion quality check
        5. Finalize — Publish or revise based on critic feedback
    """

    def __init__(
        self,
        config_path: str = "./configs/settings.yaml",
        provider: str = "anthropic",
    ):
        # Load config
        self.config = self._load_config(config_path)

        # Initialize components
        self.logger = PipelineLogger(level=self.config.get("app", {}).get("log_level", "INFO"))
        self.llm = LLMClient(provider=provider)

        llm_config = self.config.get("llm", {})
        rag_config = self.config.get("rag", {})
        pipeline_config = self.config.get("pipeline", {})

        self.parser = ECOParser(
            llm_client=self.llm,
            logger=self.logger,
            model=llm_config.get("drafting", {}).get("model"),
        )

        self.retriever = MultiIndexRetriever(
            persist_dir=rag_config.get("persist_directory", "./chroma_db"),
            embedding_model=rag_config.get("embedding_model", "all-MiniLM-L6-v2"),
            glossary_top_k=rag_config.get("indices", {}).get("glossary", {}).get("top_k", 3),
            eco_corpus_top_k=rag_config.get("indices", {}).get("eco_corpus", {}).get("top_k", 3),
            msa_top_k=rag_config.get("indices", {}).get("msa", {}).get("top_k", 2),
            logger=self.logger,
        )

        self.drafter = DraftingAgent(
            llm_client=self.llm,
            logger=self.logger,
            model=llm_config.get("drafting", {}).get("model"),
            confidence_threshold=pipeline_config.get("confidence_threshold", 0.5),
        )

        self.critic = CriticAgent(
            llm_client=self.llm,
            logger=self.logger,
            model=llm_config.get("critic", {}).get("model"),
        )

        self.max_retries = pipeline_config.get("max_retries", 2)
        self.enable_critique = pipeline_config.get("enable_self_critique", True)

    def run(self, input_text: str, case_id: Optional[str] = None) -> PipelineResult:
        """Execute the full Eng2Biz pipeline on a single input.

        Args:
            input_text: Raw engineering artifact text
            case_id: Optional identifier for tracking

        Returns:
            PipelineResult with all intermediate and final outputs
        """
        start_time = time.time()
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Pipeline START: {case_id or 'ad-hoc'}")
        self.logger.info(f"{'='*60}")

        result = PipelineResult(case_id=case_id, input_text=input_text)

        # ── Stage 1: Parse ──
        self.logger.info("Stage 1/5: Parsing engineering artifact")
        parsed = self.parser.parse(input_text)
        result.parsed_artifact = parsed

        # ── Stage 2: Retrieve ──
        self.logger.info("Stage 2/5: Retrieving RAG context")
        context = self.retriever.retrieve(parsed)
        result.retrieved_context = context
        context_strings = self.retriever.format_context_for_prompt(context)

        # ── Stage 3: Draft ──
        self.logger.info("Stage 3/5: Drafting GSM Brief (CoT)")
        draft_output = self.drafter.draft(parsed, context, context_strings)

        if isinstance(draft_output, RefusalResponse):
            result.refusal = draft_output
            result.is_published = False
            result.latency_seconds = time.time() - start_time
            self.logger.log_pipeline_result(
                case_id or "ad-hoc", False, 0.0, result.latency_seconds
            )
            return result

        brief = draft_output
        result.brief = brief

        # ── Stage 4: Critique ──
        if self.enable_critique:
            self.logger.info("Stage 4/5: Self-critique review")
            review = self.critic.review(brief, parsed, context, context_strings)
            result.critic_review = review

            # Handle revision loop
            if not review.review_passed and self.max_retries > 0:
                self.logger.info("Critic flagged issues — attempting revision")
                for attempt in range(self.max_retries):
                    self.logger.info(f"Revision attempt {attempt + 1}/{self.max_retries}")
                    # Re-draft with critic feedback
                    revision_prompt = (
                        f"REVISION REQUIRED. The critic found these issues:\n"
                        f"{review.revision_instructions}\n\n"
                        f"Please fix the following issues and regenerate the brief."
                    )
                    draft_output = self.drafter.draft(parsed, context, context_strings)
                    if isinstance(draft_output, GSMBrief):
                        brief = draft_output
                        result.brief = brief
                        review = self.critic.review(brief, parsed, context, context_strings)
                        result.critic_review = review
                        if review.review_passed:
                            break
        else:
            self.logger.info("Stage 4/5: Self-critique SKIPPED (disabled)")

        # ── Stage 5: Finalize ──
        self.logger.info("Stage 5/5: Finalizing output")
        is_published = (
            result.critic_review is None
            or result.critic_review.review_passed
            or result.critic_review.recommendation.value == "PUBLISH"
        )
        result.is_published = is_published

        # Track metrics
        result.latency_seconds = time.time() - start_time
        usage = self.llm.get_usage_summary()
        result.total_tokens = usage["total_input_tokens"] + usage["total_output_tokens"]
        result.estimated_cost_usd = usage["total_cost_usd"]

        self.logger.log_pipeline_result(
            case_id or "ad-hoc",
            is_published,
            brief.overall_confidence if brief else 0.0,
            result.latency_seconds,
        )

        self.logger.info(f"Pipeline END: {result.latency_seconds:.1f}s, ${result.estimated_cost_usd:.4f}")
        return result

    def run_batch(self, test_cases: list[dict]) -> list[PipelineResult]:
        """Run pipeline on multiple test cases.

        Args:
            test_cases: List of dicts with 'case_id' and 'input_artifact' keys

        Returns:
            List of PipelineResults
        """
        results = []
        for i, case in enumerate(test_cases):
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Batch {i+1}/{len(test_cases)}: {case.get('case_id', f'case-{i+1}')}")
            result = self.run(
                input_text=case.get("input_artifact", ""),
                case_id=case.get("case_id"),
            )
            results.append(result)
        return results

    @staticmethod
    def _load_config(path: str) -> dict:
        """Load YAML configuration."""
        config_file = Path(path)
        if config_file.exists():
            with open(config_file, "r") as f:
                return yaml.safe_load(f)
        return {}


def main():
    """CLI entry point for the pipeline."""
    parser = argparse.ArgumentParser(description="ECO-Impact Interpreter Pipeline")
    parser.add_argument(
        "--input", "-i",
        type=str,
        help="Raw engineering artifact text to process",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Path to a text file containing the artifact",
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        help="Path to JSON file with test cases for batch processing",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="./configs/settings.yaml",
        help="Path to configuration file",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="anthropic",
        choices=["anthropic", "openai"],
        help="LLM provider",
    )

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = Eng2BizPipeline(config_path=args.config, provider=args.provider)

    if args.batch:
        # Batch mode
        with open(args.batch, "r") as f:
            test_cases = json.load(f)
        results = pipeline.run_batch(test_cases)
        output = [r.model_dump() for r in results]
    elif args.file:
        # File input mode
        with open(args.file, "r") as f:
            input_text = f.read()
        result = pipeline.run(input_text)
        output = result.model_dump()
    elif args.input:
        # Direct input mode
        result = pipeline.run(args.input)
        output = result.model_dump()
    else:
        parser.print_help()
        sys.exit(1)

    # Output results
    output_json = json.dumps(output, indent=2, ensure_ascii=False, default=str)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Results saved to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
