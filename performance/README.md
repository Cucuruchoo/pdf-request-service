
# Pruebas de rendimiento - PDF Request Service

## Herramienta utilizada

Grafana k6

## Objetivo

Evaluar la estabilidad y los tiempos de respuesta
del endpoint GET /api/v1/documents.

## Entorno

- Python y FastAPI
- Docker Compose
- Tres microservicios
- MongoDB
- Windows y k6

## Resultados

| Usuarios | Duración | Solicitudes | P95 | Errores |
|---|---|---|---|---|
| 2 | 15 s | 22 | 2740 ms | 0 % |
| 5 | 30 s | 136 | 266.83 ms | 0 % |
| 10 | 60 s | 485 | 426.96 ms | 0 % |
| 10 | 60 s | 492 | 543.87 ms | 0 % |
| 10 | 60 s | 481 | 477.61 ms | 0 % |

## Umbrales configurados

- Errores HTTP inferiores al 1 %
- P95 inferior a 500 ms
- Más del 99 % de checks correctos

## Conclusiones

Todas las solicitudes GET fueron exitosas.

Tres de las cinco ejecuciones registraron un P95 inferior a 500 ms. Las ejecuciones de 2 usuarios (2.740 ms) y de 10 usuarios (543,87 ms) superaron ese objetivo. Todas las solicitudes HTTP fueron exitosas.

La ejecución con 543.87 ms superó el umbral,
lo que evidencia variaciones de latencia.

Los resultados corresponden a pruebas locales.
No representan la capacidad máxima del sistema.

## Próximas pruebas

- Carga de documentos mediante POST.
- Solicitudes concurrentes de PDFs.
- Evaluación del consumo de CPU y memoria.
- Comportamiento con diferentes tamaños de PDF.

## Protección de la API con Traefik

Se incorporó Traefik como API Gateway para centralizar
el acceso HTTP y aplicar protecciones contra sobrecarga.

### Configuración implementada

- Rate limiting: 15 solicitudes por segundo.
- Burst: 20 solicitudes.
- InFlightReq: máximo de 4 POST simultáneos
  para el mismo host.
- Respuesta ante solicitudes limitadas: HTTP 429.

### Prueba de Rate Limiting (GET)

Herramienta: Grafana k6

- Usuarios virtuales: 10.
- Duración: 8 segundos.
- Solicitudes realizadas: 2341.
- Solicitudes HTTP 200: 130.
- Solicitudes HTTP 429: 2211.
- Verificaciones correctas: 100 %.

Resultado: el gateway restringió el tráfico excesivo.

### Prueba de concurrencia (POST)

Herramienta: Grafana k6

- Usuarios virtuales: 20.
- Una solicitud POST por usuario.
- PDFs válidos y diferentes.
- Solicitudes totales: 20.
- Documentos creados (HTTP 201): 4.
- Solicitudes limitadas (HTTP 429): 16.
- Respuestas inesperadas: 0.

Resultado: se observó una restricción de las cargas
simultáneas, compatible con el límite configurado.

Como Rate Limiting e InFlightReq estaban activos,
no se puede atribuir cada HTTP 429 a uno de ellos
sin realizar una prueba aislada.

### Limitaciones

- Las pruebas fueron realizadas localmente.
- El gateway limita solicitudes, pero no identifica bots.
- No sustituye autenticación ni protección anti-DDoS.
- Los límites deben ajustarse según el entorno.
- Las protecciones requieren que el tráfico pase
  por Traefik y no acceda directamente a Request.
