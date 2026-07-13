"""
Prometheus metrics.

Exposes request counts/latency and AI token usage at ``/metrics`` when
``prometheus-client`` is installed and ``METRICS_ENABLED`` is on. Degrades
gracefully to a no-op when the dependency is absent, so metrics are strictly
optional.
"""

from __future__ import annotations

try:
    from prometheus_client import (  # type: ignore[import-untyped]
        CONTENT_TYPE_LATEST,
        Counter,
        Histogram,
        generate_latest,
    )

    _AVAILABLE = True
except ImportError:  # pragma: no cover
    _AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain"

if _AVAILABLE:
    REQUESTS = Counter(
        "mediclear_requests_total",
        "Total API requests",
        ["method", "path", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "mediclear_request_duration_seconds",
        "Request latency in seconds",
        ["method", "path"],
    )
    ANALYSES = Counter(
        "mediclear_analyses_total", "Total document analyses", ["provider", "cached"]
    )
    TOKENS = Counter(
        "mediclear_tokens_total", "AI tokens consumed", ["provider", "direction"]
    )


def is_available() -> bool:
    return _AVAILABLE


def record_request(method: str, path: str, status: int, duration: float) -> None:
    if not _AVAILABLE:
        return
    REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(duration)


def record_analysis(provider: str, cached: bool, input_tokens: int, output_tokens: int) -> None:
    if not _AVAILABLE:
        return
    ANALYSES.labels(provider=provider, cached=str(cached).lower()).inc()
    if input_tokens:
        TOKENS.labels(provider=provider, direction="input").inc(input_tokens)
    if output_tokens:
        TOKENS.labels(provider=provider, direction="output").inc(output_tokens)


def render() -> tuple[bytes, str]:
    if not _AVAILABLE:
        return b"", CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST
