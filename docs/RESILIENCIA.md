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


## Evidencia de validación local — 10/11/2026

Se verificó la solución con los tres repositorios en ramas de corrección,
ejecutados en Docker Compose para Windows. Las pruebas corresponden al entorno
local del equipo, no a un despliegue productivo.

| Comprobación | Evidencia |
|---|---|
| Usuario de aplicación | `docker compose exec request id` y equivalentes en Extraction y Storage: UID/GID 10001, sin root |
| Salud de contenedores | `docker compose ps`: MongoDB, Extraction, Storage y Request en estado `healthy`; Traefik en ejecución |
| Pruebas de Request | `uv run pytest -q`: 22 pruebas aprobadas |
| Calidad estática | `uv run ruff check app tests`: sin errores |
| Falla inducida | `docker compose stop storage` |
| Primera consulta a Storage caído | GET público → HTTP 502 en 10,701166 s |
| Segunda consulta a Storage caído | GET público → HTTP 502 en 10,525964 s |
| Rechazo rápido observado | GET público → HTTP 503 en 0,036177 s |
| Recuperación | `docker compose start storage`; healthcheck de Storage en `healthy`; GET público → HTTP 200 |

**Interpretación y alcance:** el HTTP 503 rápido es compatible con un circuito
abierto, pero el cuerpo de esa respuesta no quedó capturado. La salida pegada
incluye tres resultados de solicitudes durante la caída, no cuatro; por tanto
no se concluye una secuencia exacta de tres HTTP 502 seguida de un HTTP 503.
El HTTP 200 posterior demuestra restablecimiento de la comunicación, pero no
mide por sí solo la transición interna de `HALF-OPEN` a `CLOSED`. La prueba
unitaria `test_breaker_opens_and_recovers_with_probe` valida esa transición.

## Limitaciones y posibles mejoras

- El Circuit Breaker mantiene un estado **por proceso**. Varias réplicas
  requerirían una estrategia adicional si se quisiera coordinación global.
- `depends_on: condition: service_healthy` controla el orden inicial de
  arranque, pero no garantiza disponibilidad permanente.
- Los endpoints `/health` verifican la respuesta de cada proceso.
  Se puede añadir un `/ready` separado para evaluar dependencias.
- Las escrituras no se reintentan automáticamente porque no está implementada
  una clave de idempotencia de operación.
- No hay un workflow de GitHub Actions que ejecute automáticamente pytest
  y Ruff por cada PR; la evidencia anterior corresponde a ejecuciones locales.

## Guion reproducible de prueba de resiliencia (PowerShell)

```powershell
# Ejecutar desde pdf-request-service (todos los contenedores levantados)
docker compose ps
curl.exe -i http://127.0.0.1:8000/health

# En un entorno de pruebas, detener solo Storage
docker compose stop storage
1..4 | ForEach-Object {
    curl.exe -s -o NUL -w "HTTP %{http_code} - %{time_total}s`n" http://127.0.0.1:8000/api/v1/documents
}

# Restaurar Storage aunque la prueba no haya dado el resultado esperado
docker compose start storage
docker compose ps

# Confirmar que Storage vuelve a estar healthy antes de verificar recuperación
curl.exe -i http://127.0.0.1:8000/api/v1/documents
```

Si el puerto 8000 está ocupado por otro proyecto (por ejemplo, Bodegas del
Atuel), detener ese proyecto o asignar un puerto externo diferente a Traefik,
sin cambiar los puertos HTTP internos de los microservicios. El nombre
esperado de la API se valida en `/openapi.json`: `PDF Request Service`.
