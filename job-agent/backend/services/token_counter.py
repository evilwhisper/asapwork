"""
App-level session token counter.
Persists across requests within a single server process.
Reset via DELETE /api/settings/tokens.
"""
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class _TokenCounter:
    _lock: Lock = field(default_factory=Lock)
    total: int = 0
    prompt: int = 0
    completion: int = 0
    calls: int = 0

    def add(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        with self._lock:
            self.prompt += prompt_tokens
            self.completion += completion_tokens
            self.total += prompt_tokens + completion_tokens
            self.calls += 1

    def reset(self):
        with self._lock:
            self.total = 0
            self.prompt = 0
            self.completion = 0
            self.calls = 0

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "total": self.total,
                "prompt": self.prompt,
                "completion": self.completion,
                "calls": self.calls,
            }


# Single shared instance for the process lifetime
token_counter = _TokenCounter()
