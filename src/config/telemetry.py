import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

_initialized = False


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.environ.get(name, str(default)).lower()
    return value in ("1", "true", "yes", "on")


def init_telemetry(
    service_name: str | None = None, *, instrument_django: bool = False
) -> None:
    global _initialized
    if _initialized:
        return

    if not _env_bool("OTEL_ENABLED", True):
        return

    name = service_name or os.environ.get("OTEL_SERVICE_NAME", "loadlab")
    endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"
    )
    sampler_ratio = float(os.environ.get("OTEL_TRACES_SAMPLER_ARG", "1.0"))

    resource = Resource.create(
        {
            "service.name": name,
            "deployment.environment": os.environ.get("DEPLOYMENT_ENV", "local"),
        }
    )

    tracer_provider = TracerProvider(
        resource=resource,
        sampler=ParentBasedTraceIdRatio(sampler_ratio),
    )
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, insecure=True),
        export_interval_millis=15000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    if instrument_django:
        DjangoInstrumentor().instrument(is_sqlcommenter_enabled=True)

    PsycopgInstrumentor().instrument(enable_commenter=True, commenter_options={})
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=True)

    _initialized = True


def get_trace_context() -> dict[str, str]:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx.is_valid:
        return {}
    return {
        "trace_id": format(ctx.trace_id, "032x"),
        "span_id": format(ctx.span_id, "016x"),
    }
