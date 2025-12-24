import os
import logging
from datadog import initialize as dd_initialize, statsd

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
try:
    # import optional instrumentation
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
except Exception:
    FastAPIInstrumentor = None

logger = logging.getLogger("telemetry")


def init_telemetry(app=None):
    """Initialize OpenTelemetry tracer and Datadog DogStatsD client.

    If `app` is provided, instrument the FastAPI app.
    """
    # Configure tracer provider with service name
    service_name = os.getenv("DD_SERVICE", "llm-blackbox")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument FastAPI app if provided and instrumentation available
    if app is not None and FastAPIInstrumentor is not None:
        try:
            # Skip automatic FastAPI instrumentation if ddtrace middleware present
            FastAPIInstrumentor().instrument_app(app, tracer_provider=provider)
            logger.info("FastAPI instrumented with OpenTelemetry")
        except Exception as e:
            logger.warning("Skipping FastAPI instrumentation (middleware conflict): %s", e)

    # Initialize DogStatsD (send to local agent)
    try:
        dd_host = os.getenv("DD_AGENT_HOST", "localhost")
        dd_port = int(os.getenv("DD_AGENT_PORT", 8125))
        dd_initialize(statsd_host=dd_host, statsd_port=dd_port)
        logger.info("Datadog DogStatsD initialized: %s:%s", dd_host, dd_port)
    except Exception as e:
        logger.warning("Failed to initialize DogStatsD: %s", e)


def record_llm_metrics(prompt_tokens: int, completion_tokens: int, total_tokens: int, latency_ms: float, cost: float, model: str = "unknown"):
    """Emit Datadog metrics for LLM usage via DogStatsD."""
    try:
        tags = [f"model:{model}"]
        statsd.gauge("llm.tokens.prompt", prompt_tokens, tags=tags)
        statsd.gauge("llm.tokens.completion", completion_tokens, tags=tags)
        statsd.gauge("llm.tokens.total", total_tokens, tags=tags)
        statsd.gauge("llm.latency.ms", latency_ms, tags=tags)
        statsd.gauge("llm.cost.estimated", cost, tags=tags)
    except Exception as e:
        logger.debug("Failed to emit llm metrics: %s", e)


def current_trace_id_hex():
    """Return current trace id as hex string, or empty string if none."""
    try:
        span = trace.get_current_span()
        ctx = span.get_span_context()
        trace_id = ctx.trace_id
        if trace_id:
            return format(trace_id, '032x')
    except Exception:
        return ""
    return ""
