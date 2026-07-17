"""
Prometheus-compatible metrics endpoint.

Exposes ``/metrics`` with request counters, latency histograms, and
infrastructure gauges.  Uses the ``prometheus_client`` library (lightweight,
no external dependencies beyond the package itself).
"""

import time

from fastapi import APIRouter, Response

router = APIRouter(tags=["metrics"])

# ── Counters & Histograms (imported lazily so startup isn't blocked) ──

_request_counter = None
_request_duration = None
_active_requests = None
_agent_runs = None


def _ensure_metrics():
    """Lazily initialise prometheus metric objects on first /metrics hit."""
    global _request_counter, _request_duration, _active_requests, _agent_runs

    if _request_counter is not None:
        return  # already initialised

    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
    )

    _request_counter = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
    )
    _request_duration = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    )
    _active_requests = Gauge(
        "http_active_requests",
        "Number of in-flight HTTP requests",
    )
    _agent_runs = Counter(
        "agent_runs_total",
        "Total agent execution attempts",
        ["agent_type", "status"],
    )


@router.get("/metrics")
async def metrics_endpoint():
    """Return Prometheus-format metrics."""
    _ensure_metrics()

    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    body = generate_latest()
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)


# ── Helper functions used by middleware / agents ──────────────────────


def record_request(method: str, path: str, status: int, duration: float):
    """Record a completed HTTP request."""
    _ensure_metrics()
    _request_counter.labels(method=method, path=path, status=str(status)).inc()
    _request_duration.labels(method=method, path=path).observe(duration)


def inc_active_requests():
    _ensure_metrics()
    _active_requests.inc()


def dec_active_requests():
    _ensure_metrics()
    _active_requests.dec()


def record_agent_run(agent_type: str, status: str):
    """Record an agent execution (completed / failed)."""
    _ensure_metrics()
    _agent_runs.labels(agent_type=agent_type, status=status).inc()
