"""OTEL and Azure Monitor / Application Insights configuration.

Call ``configure_otel_providers()`` once at application startup.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def configure_otel_providers(
    app_insights_conn_str: str | None = None,
    service_name: str = "certprep-maf",
    enable_console_exporter: bool = False,
) -> None:
    """Wire up OpenTelemetry traces/metrics to Azure Monitor.

    Args:
        app_insights_conn_str: Application Insights connection string.
            Falls back to ``APPLICATIONINSIGHTS_CONNECTION_STRING`` env var.
        service_name: Service name tag for all telemetry.
        enable_console_exporter: If True, also prints spans to stdout
            (useful for local development).
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.semconv.resource import ResourceAttributes
    except ImportError as exc:
        logger.warning("opentelemetry SDK not installed; skipping OTEL setup. %s", exc)
        return

    conn_str = app_insights_conn_str or os.environ.get(
        "APPLICATIONINSIGHTS_CONNECTION_STRING", ""
    )

    resource = Resource.create(
        {ResourceAttributes.SERVICE_NAME: service_name}
    )
    provider = TracerProvider(resource=resource)

    # Azure Monitor exporter
    if conn_str:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            az_exporter = AzureMonitorTraceExporter(connection_string=conn_str)
            provider.add_span_processor(BatchSpanProcessor(az_exporter))
            logger.info("Azure Monitor trace exporter registered for %s.", service_name)
        except ImportError:
            logger.warning(
                "azure-monitor-opentelemetry-exporter not installed; "
                "App Insights tracing disabled."
            )

    # Optional console exporter for local debugging
    if enable_console_exporter:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # Metrics – basic counter for agent invocations
    try:
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        if conn_str:
            from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter

            metric_exporter = AzureMonitorMetricExporter(connection_string=conn_str)
            reader = PeriodicExportingMetricReader(metric_exporter)
            meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            metrics.set_meter_provider(meter_provider)
            logger.info("Azure Monitor metric exporter registered.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not configure metrics exporter: %s", exc)
