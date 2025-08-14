"""Prometheus metrics for observability"""

from typing import Dict, Any
from fastapi import APIRouter, Response
from prometheus_client import (
    Counter, Histogram, Gauge, Summary,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, multiprocess, start_http_server
)
import os
import time

# Create registry for metrics
if os.getenv("prometheus_multiproc_dir"):
    # Multiprocess mode for production
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
else:
    # Single process mode for development
    registry = CollectorRegistry()

# Define metrics
llm_inference_seconds = Histogram(
    "llm_inference_seconds",
    "LLM inference duration in seconds",
    ["model", "agent", "operation"],
    registry=registry,
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf"))
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens processed",
    ["model", "agent", "token_type"],
    registry=registry
)

llm_cost_usd = Counter(
    "llm_cost_usd_total",
    "Total cost in USD",
    ["model", "agent"],
    registry=registry
)

active_sessions = Gauge(
    "active_sessions",
    "Number of active writing sessions",
    registry=registry
)

cache_hits = Counter(
    "cache_hits_total",
    "Cache hit count",
    ["cache_type"],
    registry=registry
)

cache_misses = Counter(
    "cache_misses_total",
    "Cache miss count",
    ["cache_type"],
    registry=registry
)

api_requests = Counter(
    "api_requests_total",
    "API request count",
    ["method", "endpoint", "status"],
    registry=registry
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration",
    ["method", "endpoint"],
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf"))
)

websocket_connections = Gauge(
    "websocket_connections",
    "Active WebSocket connections",
    registry=registry
)

model_errors = Counter(
    "model_errors_total",
    "Model API errors",
    ["model", "error_type"],
    registry=registry
)

budget_exceeded = Counter(
    "budget_exceeded_total",
    "Budget exceeded events",
    ["project_id"],
    registry=registry
)


class MetricsTracker:
    """Helper class for tracking metrics"""
    
    @staticmethod
    def track_inference(model: str, agent: str, operation: str):
        """Context manager for tracking inference time"""
        class Timer:
            def __enter__(self):
                self.start = time.perf_counter()
                return self
            
            def __exit__(self, *args):
                duration = time.perf_counter() - self.start
                llm_inference_seconds.labels(
                    model=model,
                    agent=agent,
                    operation=operation
                ).observe(duration)
        
        return Timer()
    
    @staticmethod
    def track_tokens(
        model: str,
        agent: str,
        prompt_tokens: int,
        completion_tokens: int
    ):
        """Track token usage"""
        llm_tokens_total.labels(
            model=model,
            agent=agent,
            token_type="prompt"
        ).inc(prompt_tokens)
        
        llm_tokens_total.labels(
            model=model,
            agent=agent,
            token_type="completion"
        ).inc(completion_tokens)
    
    @staticmethod
    def track_cost(model: str, agent: str, cost_usd: float):
        """Track cost in USD"""
        llm_cost_usd.labels(model=model, agent=agent).inc(cost_usd)
    
    @staticmethod
    def track_cache(hit: bool, cache_type: str = "response"):
        """Track cache hit/miss"""
        if hit:
            cache_hits.labels(cache_type=cache_type).inc()
        else:
            cache_misses.labels(cache_type=cache_type).inc()
    
    @staticmethod
    def track_api_request(method: str, endpoint: str, status_code: int):
        """Track API request"""
        api_requests.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
    
    @staticmethod
    def track_model_error(model: str, error_type: str):
        """Track model API errors"""
        model_errors.labels(model=model, error_type=error_type).inc()


# Create metrics router
metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(
        generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST
    )


@metrics_router.get("/health/metrics")
async def health_metrics() -> Dict[str, Any]:
    """Health check with basic metrics"""
    return {
        "active_sessions": active_sessions._value.get(),
        "websocket_connections": websocket_connections._value.get(),
        "status": "healthy"
    }