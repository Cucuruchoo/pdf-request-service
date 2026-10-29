
import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# Identificador de cada solicitud HTTP
request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default="-",
)


class JsonFormatter(logging.Formatter):
    """Convierte los registros en formato JSON."""

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "service": "pdf-request-service",
            "request_id": request_id_context.get(),
            "event": record.getMessage(),
        }

        # Datos adicionales de la solicitud
        for field in (
            "method",
            "path",
            "status_code",
            "duration_ms",
        ):
            if hasattr(record, field):
                payload[field] = getattr(record, field)

        # Registrar el tipo de error sin exponer el PDF
        if record.exc_info:
            payload["error_type"] = (
                record.exc_info[0].__name__
            )

        return json.dumps(payload, ensure_ascii=False)


def configure_logger(level: str):
    """Configura los logs para Docker."""

    logger = logging.getLogger("pdf_request")
    logger.setLevel(level.upper())
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger
