# Arquitectura del sistema de procesamiento de PDF

**Proyecto:** Desarrollo de Software 2026 — Ingeniería en Sistemas de Información
**Alcance:** implementación de la consigna de recepción, extracción de texto y persistencia de PDF.

## 1. Objetivo y requisitos

La aplicación recibe archivos PDF, valida su formato y tamaño, extrae el texto, calcula un checksum SHA-256 y almacena el contenido textual en MongoDB. Permite crear, listar, consultar, modificar y eliminar documentos mediante una API REST. Rechaza archivos duplicados y no guarda temporalmente el PDF original en el sistema de archivos durante el procesamiento.

Los requisitos académicos incluyen Python, FastAPI, uv, TDD y gestión con GitHub Project. Los criterios de evaluación también contemplan rendimiento, código limpio, principios SOLID/DRY/KISS/YAGNI, arquitectura empresarial y aspectos de 12 Factor App.

## 2. Arquitectura general

Se utiliza una arquitectura de **microservicios** con comunicación HTTP y separación interna por responsabilidades. Docker Compose coordina cinco contenedores:

| Componente | Función |
|---|---|
| **Traefik** | Punto de entrada HTTP, enrutamiento y límites de tráfico. |
| **PDF Request Service** | API pública, validación del PDF, checksum y orquestación del flujo. |
| **PDF Extraction Service** | Extracción de texto con `pypdf`, sin persistir el PDF. |
| **PDF Storage Service** | Casos de uso CRUD, modelo documental y persistencia. |
| **MongoDB** | Base de datos no relacional; mantiene los documentos mediante un volumen de Docker. |

**Recorrido de una carga:** Cliente → Traefik → Request → Extraction → Request → Storage → MongoDB.
**Recorrido de una consulta:** Cliente → Traefik → Request → Storage → MongoDB.

Request se comunica con Extraction y Storage mediante HTTP en la red interna de Docker. Solo Traefik publica el puerto de entrada `127.0.0.1:8000` en el entorno local. Los endpoints públicos se documentan en `/docs` mediante Swagger UI. No hay una interfaz web de usuario propia implementada; corresponde confirmar si la cátedra la requiere.

## 3. Organización interna por capas

Los servicios usan módulos organizados por responsabilidades:

- **API:** rutas HTTP, códigos de respuesta, validación de peticiones y esquemas.
- **Aplicación:** coordinación de casos de uso (`RequestService`, `ExtractionService`, `DocumentService`).
- **Dominio:** reglas y modelos, por ejemplo la validación del PDF y `Document`.
- **Infraestructura:** clientes HTTP, extractor basado en `pypdf`, repositorio MongoDB, configuración y logging.

Esta estructura aproxima una arquitectura de aplicaciones empresariales en capas; no implica que todas las decisiones de una arquitectura hexagonal o Clean Architecture estén implementadas de forma exhaustiva.

## 4. Flujo de procesamiento del PDF

1. El cliente envía `POST /api/v1/documents` con cuerpo `application/pdf` y encabezado `X-Filename`.
2. Traefik aplica restricciones de frecuencia y simultaneidad a la solicitud.
3. Request valida el tipo de contenido, la extensión, la firma del archivo y el límite de tamaño (10 MiB por defecto).
4. El archivo se procesa en memoria; Request calcula su checksum SHA-256.
5. Request envía los bytes a Extraction mediante `POST /internal/v1/extract`.
6. Extraction usa `pypdf` para extraer texto y devuelve el resultado.
7. Request envía a Storage los metadatos, checksum y texto extraído en formato JSON.
8. Storage aplica la lógica de persistencia y crea el registro en MongoDB.
9. MongoDB mantiene un índice único sobre `checksum`, para impedir documentos duplicados incluso ante inserciones concurrentes.
10. Request devuelve la respuesta al cliente, incluyendo `X-Request-ID`.

El documento PDF original no se almacena en MongoDB; se guarda el **texto extraído** y sus metadatos.

## 5. Decisiones de diseño y patrones

- **Separación de responsabilidades (SRP):** Request coordina, Extraction extrae y Storage administra documentos; cada servicio mantiene una responsabilidad principal.
- **Abstracciones e inversión de dependencias (DIP):** la lógica de aplicación depende de contratos como `TextExtractor`, `DocumentRepository` y los protocolos de clientes de Request, facilitando pruebas con dobles.
- **Repositorio:** `MongoDocumentRepository` encapsula las operaciones de MongoDB y evita acoplar los casos de uso al driver.
- **Inyección de dependencias:** FastAPI provee clientes y servicios en los endpoints, permitiendo sustituir componentes en las pruebas.
- **DRY:** las validaciones y operaciones persistentes se concentran en componentes reutilizables en lugar de duplicarse en cada ruta.
- **KISS:** la API utiliza HTTP REST y una orquestación directa, sin una capa adicional de mensajería.
- **YAGNI:** no se incorporó Kafka ni una infraestructura de eventos porque el flujo actual funciona mediante llamadas síncronas HTTP.

Estos son ejemplos concretos de principios aplicados; no se afirma una conformidad absoluta con todos los principios SOLID.

## 6. Persistencia y consistencia

MongoDB guarda el identificador, nombre del PDF, texto extraído, checksum SHA-256, tamaño y fechas de creación/actualización. Storage admite operaciones POST, GET, PATCH y DELETE. Un índice único de checksum se crea al iniciar el servicio; ante duplicados se devuelve HTTP `409 Conflict`.

La base de datos utiliza el volumen persistente `mongo_data` de Docker Compose. No se debe ejecutar `docker compose down -v` al realizar una reconstrucción habitual, porque eso eliminaría los datos del volumen.

## 7. Seguridad, recursos y observabilidad

- **Validaciones:** extensión `.pdf`, firma `%PDF-`, `Content-Type` y tamaño máximo configurable.
- **Traefik:** `rateLimit` configurado con promedio de 15 solicitudes/s y ráfaga de 20; `inFlightReq` limita a cuatro los POST simultáneos al mismo host.
- **Protección interna:** `PdfUploadLimiter` limita a cuatro cargas en curso **por proceso** de Request; devuelve HTTP `429` ante saturación y libera espacios incluso ante errores.
- **Trazabilidad:** Request genera o conserva un `X-Request-ID` válido y lo propaga a Extraction y Storage. Los tres servicios emiten registros JSON con identificador, operación, código HTTP y duración.
- **Tiempos de espera:** Request configura timeout para las llamadas HTTP internas (30 segundos por defecto).

**Limitaciones:** Traefik está configurado como gateway hacia una instancia de Request, pero no se validó balanceo real entre réplicas. La limitación de tráfico reduce el abuso, pero **no equivale a autenticación, WAF ni protección integral contra DDoS**. El sistema está preparado para pruebas locales; antes de publicarlo en Internet deben evaluarse autenticación, autorización, TLS y el acceso al socket de Docker.

## 8. 12 Factor App: criterios aplicados

| Criterio | Evidencia en el proyecto |
|---|---|
| Código base | Repositorios Git separados para Request, Extraction y Storage. |
| Dependencias | Declaradas con `pyproject.toml` y gestionadas mediante `uv`. |
| Configuración | Variables de entorno para URLs, MongoDB, límites y logging. |
| Servicios externos | MongoDB y microservicios conectados por direcciones configurables. |
| Procesos y puertos | Contenedores Docker con servidores HTTP y gateway de entrada. |
| Logs | Salida estándar con registros estructurados disponibles mediante `docker compose logs`. |

Esta tabla documenta los puntos observables; no pretende certificar el cumplimiento íntegro de los doce factores.

## 9. Pruebas y evidencias

- **Pruebas unitarias y de API:** ejecutadas con `uv run pytest -q` en los tres repositorios, con dobles de prueba donde corresponde.
- **Calidad de código:** revisión con `uv run ruff check app tests`.
- **TDD:** se registraron ciclos de pruebas fallidas (RED) y aprobadas (GREEN) durante la implementación de trazabilidad. La evidencia histórica de commits y capturas debe adjuntarse si la cátedra lo solicita.
- **Integración:** se verificó una carga PDF con el mismo `X-Request-ID` en Request, Extraction y Storage.
- **Rendimiento:** k6 probó GET con 2, 5 y 10 usuarios virtuales; las ejecuciones no tuvieron errores HTTP, aunque algunas superaron el objetivo provisional de P95 de 500 ms.
- **Protección:** una prueba GET obtuvo 2211 respuestas `429` de 2341 solicitudes; otra prueba de 20 cargas POST obtuvo cuatro `201` y dieciséis `429` con los mecanismos de Traefik activos.

Las mediciones corresponden al entorno local y no demuestran la capacidad máxima del sistema.

## 10. Ejecución y entrega

Los repositorios `pdf-request-service`, `pdf-extraction-service` y `pdf-storage-service` deben encontrarse como carpetas hermanas. Desde `pdf-request-service` se inicia el conjunto con:

`docker compose up --build -d`

La comprobación de contenedores se realiza con `docker compose ps`. La API pública está disponible en `http://127.0.0.1:8000/docs` y el endpoint de salud en `http://127.0.0.1:8000/health`.

**Pendientes de validación académica:** tablero GitHub Project, formato requerido para la evidencia de TDD, necesidad de un frontend propio y criterios finales de entrega indicados por la cátedra.
