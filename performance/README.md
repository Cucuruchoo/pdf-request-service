
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
