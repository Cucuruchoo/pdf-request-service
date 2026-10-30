
# PDF Request Service

Microservicio de entrada pública de la implementación final del proyecto Desarrollo de Software 2026.

## Integrantes

- Santiago Viñolo
- Renata Michaux

## Evolución del proyecto

El proyecto se desarrolló en **una única etapa académica**. Comenzó con una [implementación monolítica organizada por capas](https://github.com/Cucuruchoo/pdf-extractext) y evolucionó hacia tres microservicios: [Request](https://github.com/Cucuruchoo/pdf-request-service), [Extraction](https://github.com/Cucuruchoo/pdf-extraction-service) y [Storage](https://github.com/Cucuruchoo/pdf-storage-service).

La gestión del trabajo se conserva en dos tableros complementarios:

- [GitHub Project — Implementación original](https://github.com/users/Cucuruchoo/projects/2).
- [GitHub Project — Implementación final con microservicios](https://github.com/users/Cucuruchoo/projects/1).

Para conocer el flujo entre servicios, las decisiones de diseño y las limitaciones, consultá la [documentación de arquitectura](docs/ARQUITECTURA.md).

## Descripción

API REST desarrollada con Python y FastAPI que coordina la recepción, validación, extracción y almacenamiento de documentos PDF.

## Tecnologías

- Python 3.12
- FastAPI
- uv
- Docker y Docker Compose
- MongoDB
- pytest

## Microservicios

- pdf-request-service: API pública y validación.
- pdf-extraction-service: extracción de texto.
- pdf-storage-service: persistencia y CRUD.
- MongoDB: base de datos NoSQL.

## Instalación

Los tres repositorios deben estar en la misma carpeta:

Proyecto/
  pdf-request-service/
  pdf-extraction-service/
  pdf-storage-service/

Desde pdf-request-service ejecutar:

```bash
docker compose up --build -d
```

Comprobar los contenedores:

```bash
docker compose ps
```

## Documentación de la API

http://127.0.0.1:8000/docs

## Endpoints

- POST /api/v1/documents
- GET /api/v1/documents
- GET /api/v1/documents/{document_id}
- PATCH /api/v1/documents/{document_id}
- DELETE /api/v1/documents/{document_id}
- GET /health

Para cargar un PDF mediante POST, enviar el archivo como cuerpo application/pdf e indicar su nombre en el encabezado X-Filename.

## Pruebas

```bash
uv sync
uv run pytest -q
```

## Funcionalidades

- Validación del formato y tamaño del PDF.
- Extracción de texto.
- Generación de checksum SHA-256.
- Detección de documentos duplicados.
- Almacenamiento en MongoDB.
- Operaciones CRUD sobre documentos.

## Protección contra sobrecarga

La API implementa dos niveles de protección:

### 1. Protección mediante Traefik

Traefik funciona como API Gateway e incorpora:

- Rate limiting de 15 solicitudes por segundo.
- Burst de 20 solicitudes.
- Límite de 4 solicitudes POST simultáneas.
- Respuesta HTTP 429 cuando se exceden los límites.

### 2. Control interno de concurrencia

Request Service incorpora un controlador basado
en asyncio para limitar el procesamiento de PDFs.

- Máximo configurable mediante
  MAX_CONCURRENT_PDF_UPLOADS.
- Valor predeterminado: 4 PDFs simultáneos.
- El límite es compartido por las solicitudes
  de una misma instancia del servicio.
- Las solicitudes adicionales reciben HTTP 429.
- Los espacios se liberan al finalizar o fallar.
- Las operaciones GET, PATCH y DELETE
  no utilizan este límite.

### Pruebas automatizadas

Se verifica:

- El rechazo cuando se alcanza el límite.
- La liberación de recursos después de errores.
- El control de la cantidad máxima de operaciones.

### Limitaciones

El límite interno funciona por proceso de Request.
En una arquitectura con múltiples instancias,
cada una mantiene su propio contador.
