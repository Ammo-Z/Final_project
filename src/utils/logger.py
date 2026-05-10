"""Structured logging for ECO-Impact Interpreter pipeline."""

from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class PipelineLogger:
    """Logger that tracks latency, token usage, and pipeline events."""

    def __init__(self, log_dir: str = "./logs", level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger("eco_interpreter")
        self.logger.setLevel(getattr(logging, level.upper()))

        # Console handler
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(message)s",
                datefmt="%H:%M:%S",
            )
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        # Run log (JSONL)
        self._run_log: list[dict] = []
        self._timers: dict[str, float] = {}

    def info(self, msg: str, **kwargs):
        self.logger.info(msg)
        self._log_event("INFO", msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg)
        self._log_event("WARNING", msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self.logger.error(msg)
        self._log_event("ERROR", msg, **kwargs)

    def start_timer(self, label: str):
        """Start a named timer."""
        self._timers[label] = time.time()
        self.logger.debug(f"Timer started: {label}")

    def stop_timer(self, label: str) -> float:
        """Stop a named timer and return elapsed seconds."""
        if label not in self._timers:
            return 0.0
        elapsed = time.time() - self._timers.pop(label)
        self.logger.info(f"Timer {label}: {elapsed:.2f}s")
        self._log_event("TIMER", label, elapsed_seconds=elapsed)
        return elapsed

    def log_llm_call(
        self,
        stage: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
    ):
        """Log an LLM API call with usage metrics."""
        self.logger.info(
            f"LLM [{stage}] model={model} "
            f"tokens={input_tokens}+{output_tokens} "
            f"cost=${cost_usd:.5f} "
            f"latency={latency_ms:.0f}ms"
        )
        self._log_event(
            "LLM_CALL",
            stage,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

    def log_pipeline_result(self, case_id: str, is_published: bool, confidence: float, total_latency: float):
        """Log final pipeline result."""
        status = "PUBLISHED" if is_published else "REFUSAL"
        self.logger.info(
            f"Pipeline [{case_id}] status={status} "
            f"confidence={confidence:.2f} "
            f"total_latency={total_latency:.2f}s"
        )
        self._log_event(
            "PIPELINE_RESULT",
            case_id,
            status=status,
            confidence=confidence,
            total_latency=total_latency,
        )

    def _log_event(self, level: str, message: str, **kwargs):
        """Append structured event to run log."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            **kwargs,
        }
        self._run_log.append(event)

    def save_run_log(self, filename: Optional[str] = None):
        """Save the run log as JSONL."""
        if filename is None:
            filename = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        path = self.log_dir / filename
        with open(path, "w") as f:
            for event in self._run_log:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.logger.info(f"Run log saved to {path}")
        return str(path)

    def get_run_summary(self) -> dict:
        """Summarize the current run's metrics."""
        llm_calls = [e for e in self._run_log if e["level"] == "LLM_CALL"]
        return {
            "total_events": len(self._run_log),
            "llm_calls": len(llm_calls),
            "total_input_tokens": sum(e.get("input_tokens", 0) for e in llm_calls),
            "total_output_tokens": sum(e.get("output_tokens", 0) for e in llm_calls),
            "total_cost_usd": sum(e.get("cost_usd", 0) for e in llm_calls),
            "total_latency_ms": sum(e.get("latency_ms", 0) for e in llm_calls),
        }
