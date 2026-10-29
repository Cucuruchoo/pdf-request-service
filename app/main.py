
import re
import time
from uuid import uuid4

from fastapi import FastAPI, Request

from app.api.routes import router
from app.infrastructure.request_logging import (
    configure_logger,
    request_id_context,
)
from app.infrastructure.settings import get_settings

# Configuración de logging
logger = configure_logger(get_settings().log_level)

# Aplicación FastAPI
app = FastAPI(
    title="PDF Request Service",
    version="0.1.0",
)

app.include_router(router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Buscar un identificador recibido del cliente
    incoming_id = request.headers.get(
        "X-Request-ID",
        "",
    )

    # Conservar identificadores válidos
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", incoming_id):
        request_id = incoming_id
    else:
        # Generar un identificador nuevo
        request_id = uuid4().hex

    token = request_id_context.set(request_id)
    start_time = time.perf_counter()
    status_code = 500

    try:
        # Procesar la solicitud HTTP
        response = await call_next(request)

        status_code = response.status_code

        # Devolver el identificador al cliente
        response.headers["X-Request-ID"] = request_id

        return response

    except Exception:
        logger.exception("http_unhandled_error")
        raise

    finally:
        # Calcular duración de la solicitud
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2,
        )

        # Registrar la operación
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

        request_id_context.reset(token)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "pdf-request-service",
    }
