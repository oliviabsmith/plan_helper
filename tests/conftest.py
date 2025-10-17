import os
import sys
import types

# Ensure the project root is on the import path for tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Provide lightweight shims for optional third-party packages during tests.
if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _DummyError(Exception):
        pass

    class _DummyResponses:
        def create(self, **kwargs):  # pragma: no cover - tests inject custom behaviour
            raise RuntimeError("openai stub cannot create responses")

    class OpenAI:  # pragma: no cover - only used when real SDK is unavailable
        def __init__(self, *args, **kwargs):
            self.responses = _DummyResponses()

    openai_stub.OpenAI = OpenAI
    openai_stub.APIStatusError = _DummyError
    openai_stub.APIConnectionError = _DummyError
    openai_stub.RateLimitError = _DummyError
    sys.modules["openai"] = openai_stub
