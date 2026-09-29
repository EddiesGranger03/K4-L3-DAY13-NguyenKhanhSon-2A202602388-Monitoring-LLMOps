from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

# Langfuse reads its credentials when the client is initialized. Load the local
# development environment before importing the SDK so `get_client()` cannot be
# cached with missing credentials.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - requirements are not installed yet
    pass

try:
    from langfuse import get_client, observe, propagate_attributes

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

        def flush(self) -> None:
            return None

        def shutdown(self) -> None:
            return None

    def get_client():
        return _DummyClient()

    @contextmanager
    def propagate_attributes(**kwargs: Any):
        yield


def get_langfuse_client():
    return get_client()


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


def shutdown_tracing() -> None:
    """Flush queued observations and stop the SDK during app shutdown."""
    if tracing_enabled():
        get_langfuse_client().shutdown()
