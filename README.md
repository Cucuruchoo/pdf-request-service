
# PDF Request Service

Tercer microservicio del proyecto Desarrollo de Software 2026.

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
