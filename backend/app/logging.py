"""GCP-compatible structured logging configuration for sopher.ai"""

import json
import logging
import os
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variables for request-scoped data
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar("span_id", default=None)
http_request_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar("http_request", default=None)


def severity_from_level(levelno: int) -> str:
    """Map Python logging level to GCP severity."""
    if levelno >= logging.CRITICAL:
        return "CRITICAL"
    elif levelno >= logging.ERROR:
        return "ERROR"
    elif levelno >= logging.WARNING:
        return "WARNING"
    elif levelno >= logging.INFO:
        return "INFO"
    else:
        return "DEBUG"


class GCPJSONFormatter(logging.Formatter):
    """JSON formatter that outputs GCP-compatible structured logs."""

    def __init__(self, service_name: str = "sopher-api", service_version: Optional[str] = None):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
        self.gcp_project = os.getenv("GCP_PROJECT")

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as GCP-compatible JSON."""
        # Build base log entry
        log_entry: Dict[str, Any] = {
            "severity": severity_from_level(record.levelno),
            "message": record.getMessage(),
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "lineno": record.lineno,
        }

        # Add labels
        labels: Dict[str, str] = {"service": self.service_name}
        if self.service_version:
            labels["version"] = self.service_version
        log_entry["labels"] = labels

        # Add request context if available
        request_id = getattr(record, "request_id", None)
        if request_id:
            log_entry["request_id"] = request_id

        # Add HTTP request info if available
        http_request = getattr(record, "http_request", None)
        if http_request:
            log_entry["httpRequest"] = http_request

        # Add trace info if available
        trace_id = getattr(record, "trace_id", None)
        if trace_id and self.gcp_project:
            log_entry["logging.googleapis.com/trace"] = (
                f"projects/{self.gcp_project}/traces/{trace_id}"
            )

        span_id = getattr(record, "span_id", None)
        if span_id:
            log_entry["logging.googleapis.com/spanId"] = span_id

        # Add stack trace if exception info is present
        if record.exc_info:
            log_entry["stack_trace"] = "".join(traceback.format_exception(*record.exc_info))

        # Add any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "request_id",
                "trace_id",
                "span_id",
                "http_request",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


class ContextFilter(logging.Filter):
    """Filter that injects context variables into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context variables to the log record."""
        record.request_id = request_id_var.get()
        record.trace_id = trace_id_var.get()
        record.span_id = span_id_var.get()
        record.http_request = http_request_var.get()
        return True


def setup_logging() -> logging.Logger:
    """Configure structured logging for the application."""
    # Get configuration from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_json = os.getenv("LOG_JSON", "true").lower() == "true"
    service_name = os.getenv("SERVICE_NAME", "sopher-api")
    service_version = os.getenv("SERVICE_VERSION")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create stdout handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter based on configuration
    formatter: logging.Formatter
    if log_json:
        formatter = GCPJSONFormatter(service_name=service_name, service_version=service_version)
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)

    # Add context filter
    handler.addFilter(ContextFilter())

    # Add handler to root logger
    root_logger.addHandler(handler)

    # Configure uvicorn loggers to propagate to root
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True

    return root_logger


def set_request_context(
    request_id: Optional[str] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    http_request: Optional[Dict[str, Any]] = None,
) -> None:
    """Set context variables for the current request."""
    if request_id:
        request_id_var.set(request_id)
    if trace_id:
        trace_id_var.set(trace_id)
    if span_id:
        span_id_var.set(span_id)
    if http_request:
        http_request_var.set(http_request)


def clear_request_context() -> None:
    """Clear all request context variables."""
    request_id_var.set(None)
    trace_id_var.set(None)
    span_id_var.set(None)
    http_request_var.set(None)


def parse_trace_context(header_value: str) -> tuple[Optional[str], Optional[str]]:
    """Parse X-Cloud-Trace-Context header.

    Format: TRACE_ID/SPAN_ID;o=TRACE_TRUE
    Returns: (trace_id, span_id)
    """
    if not header_value:
        return None, None

    parts = header_value.split(";")[0].split("/")
    trace_id = parts[0] if parts else None
    span_id = parts[1] if len(parts) > 1 else None

    return trace_id, span_id
