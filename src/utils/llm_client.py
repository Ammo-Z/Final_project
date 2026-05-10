"""Unified LLM client supporting Anthropic and OpenAI APIs."""

from __future__ import annotations
import json
import os
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Wrapper around Anthropic/OpenAI APIs with logging and cost tracking."""

    # Approximate pricing per 1M tokens (input/output)
    PRICING = {
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
        "claude-opus-4-6": {"input": 15.0, "output": 75.0},
        "gpt-4o": {"input": 2.50, "output": 10.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    }

    def __init__(self, provider: str = "anthropic"):
        self.provider = provider
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.call_count = 0

        if provider == "anthropic":
            try:
                import anthropic
                self.client = anthropic.Anthropic(
                    api_key=os.getenv("ANTHROPIC_API_KEY")
                )
            except ImportError:
                raise ImportError("pip install anthropic")
        elif provider == "openai":
            try:
                import openai
                self.client = openai.OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY")
                )
            except ImportError:
                raise ImportError("pip install openai")
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def chat(
        self,
        prompt: str,
        system: str = "",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[str] = None,
    ) -> dict:
        """Send a chat request and return parsed response with metadata.

        Args:
            prompt: User message content
            system: System message/instructions
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
            response_format: If "json", attempt to parse JSON from response

        Returns:
            dict with keys: content, input_tokens, output_tokens, cost, latency_ms
        """
        if model is None:
            model = "claude-sonnet-4-20250514" if self.provider == "anthropic" else "gpt-4o"

        start = time.time()

        if self.provider == "anthropic":
            result = self._call_anthropic(prompt, system, model, temperature, max_tokens)
        else:
            result = self._call_openai(prompt, system, model, temperature, max_tokens)

        latency_ms = (time.time() - start) * 1000

        # Track usage
        input_tokens = result.get("input_tokens", 0)
        output_tokens = result.get("output_tokens", 0)
        cost = self._estimate_cost(model, input_tokens, output_tokens)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        self.call_count += 1

        response = {
            "content": result["content"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "latency_ms": latency_ms,
            "model": model,
        }

        # Parse JSON if requested
        if response_format == "json":
            response["parsed"] = self._extract_json(result["content"])

        return response

    def _call_anthropic(self, prompt, system, model, temperature, max_tokens):
        """Call Anthropic API."""
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return {
            "content": response.content[0].text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

    def _call_openai(self, prompt, system, model, temperature, max_tokens):
        """Call OpenAI API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            "content": response.choices[0].message.content,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD."""
        pricing = self.PRICING.get(model, {"input": 3.0, "output": 15.0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """Extract JSON from LLM response text."""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from code block
        for marker in ["```json", "```"]:
            if marker in text:
                start = text.index(marker) + len(marker)
                end = text.index("```", start)
                try:
                    return json.loads(text[start:end].strip())
                except (json.JSONDecodeError, ValueError):
                    pass

        # Try finding JSON object boundaries
        brace_start = text.find("{")
        if brace_start != -1:
            depth = 0
            for i in range(brace_start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[brace_start : i + 1])
                        except json.JSONDecodeError:
                            pass
                        break
        return None

    def get_usage_summary(self) -> dict:
        """Return cumulative usage statistics."""
        return {
            "total_calls": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 6),
        }
