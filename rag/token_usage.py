"""Track Gemini token usage via a LangChain callback.

Attach TOKEN_TRACKER to the LLM; every finished call (streaming or not) logs
its input/output/thinking tokens and adds them to running totals.
"""

import logging
import threading

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("rag.token_usage")


class TokenUsageTracker(BaseCallbackHandler):
    """Log per-call token usage and keep cumulative totals."""

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with self._lock:
            self.calls = 0
            self.input_tokens = 0
            self.output_tokens = 0   # includes thinking tokens
            self.thinking_tokens = 0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "calls": self.calls,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "thinking_tokens": self.thinking_tokens,
                "total_tokens": self.input_tokens + self.output_tokens,
            }

    def on_llm_end(self, response, **kwargs):
        usage = None
        for generations in response.generations:
            for generation in generations:
                usage = getattr(
                    getattr(generation, "message", None), "usage_metadata", None
                ) or usage

        if not usage:
            logger.warning("Gemini call finished without usage metadata.")
            return

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        thinking = (usage.get("output_token_details") or {}).get("reasoning", 0)

        with self._lock:
            self.calls += 1
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.thinking_tokens += thinking
            totals = (
                self.calls,
                self.input_tokens,
                self.output_tokens,
                self.thinking_tokens,
            )

        logger.info(
            "Gemini tokens: input=%d output=%d (thinking=%d) total=%d | "
            "cumulative: calls=%d input=%d output=%d thinking=%d",
            input_tokens,
            output_tokens,
            thinking,
            input_tokens + output_tokens,
            *totals,
        )


TOKEN_TRACKER = TokenUsageTracker()
