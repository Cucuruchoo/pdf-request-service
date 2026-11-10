# Salud de contenedores y resiliencia HTTP

## Salud y orden de arranque

Los tres servicios FastAPI exponen `GET /health`. Docker Compose ejecuta sondas HTTP
internas; MongoDB utiliza `mongosh ping`. Las dependencias configuradas con
`condition: service_healthy` esperan la salud inicial del servicio. Esto **no**
garantiza que la dependencia permanezca disponible después del arranque.
Los endpoints `/health` comprueban liveness, no la conectividad end-to-end a MongoDB.

## Retry

Request aplica dos reintentos (configurables) con backoff exponencial a
`GET` de Storage y `POST` de Extraction (sin efectos persistentes).
Solo ante errores de transporte o respuestas `5xx`. No reintenta `4xx`.
Las escrituras `POST` a Storage, `PATCH` y `DELETE` no se repiten: una
respuesta perdida no significa que la operación no se haya ejecutado.

## Circuit breaker

Circuitos independientes para Extraction y Storage, compartidos por proceso
Request. Después de tres operaciones con errores de transporte o `5xx` se
abre el circuito durante 15 segundos y las nuevas llamadas reciben `503`.
Luego se admite una única prueba de recuperación (half-open). `4xx` no abre
el circuito. No hay estado compartido entre réplicas.

Variables de entorno:
- `CIRCUIT_FAILURE_THRESHOLD=3`
- `CIRCUIT_RECOVERY_SECONDS=15`
- `UPSTREAM_RETRY_ATTEMPTS=2`
- `UPSTREAM_RETRY_BASE_DELAY_SECONDS=0.1`

## Comprobación local

```bash
docker compose up --build -d
docker compose ps
curl -i http://127.0.0.1:8000/health
docker compose exec request id
uv run pytest -q
```

El UID debe ser distinto de 0. Los contenedores con sondas deben indicar
`healthy`. No usar `docker compose down -v` salvo que se pretenda
eliminar los datos persistentes.
