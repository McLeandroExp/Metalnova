# Incremento 005 — Vistas KPI y validación

Estado: propuesto · Depende de: 003 · Habilita: 006

## Contexto

Implementa las fórmulas de OEE y KPIs relacionados en vistas SQL estables, y las valida de forma
independiente con Python. Las vistas son el contrato que consume Power BI.

## Requisitos funcionales

| ID | Requisito |
|---|---|
| FR-501 | Vista de OEE por planta/línea/máquina/turno/producto/periodo con A×P×Q ponderado. |
| FR-502 | Vistas de Disponibilidad, Rendimiento y Calidad según Constitución §6. |
| FR-503 | Vistas de MTBF, MTTR, downtime no planificado. |
| FR-504 | Vistas de Scrap Rate, FPY, Energía por Unidad Buena. |
| FR-505 | Vistas de apoyo: conteo y duración de microparadas; frecuencia de fallas cortas. |
| FR-506 | Vista de la regla de excepción de máquina crítica (Constitución §8). |
| FR-507 | Vista del árbol de pérdidas (Loss Tree) descompuesto por activo/turno/producto. |
| FR-508 | Script de validación independiente en Python que calcula los KPI desde los hechos crudos y los compara con las vistas. |
| FR-509 | Tratamiento explícito de casos borde (sin producción, sin fallas, división por cero, periodo incompleto). |
| FR-510 | Definiciones publicadas en `docs/DATA_DICTIONARY.md`. |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-501 | Los KPI de SQL y de Python coinciden dentro de la tolerancia documentada (p. ej. 0,1 %). |
| AC-502 | Ningún KPI devuelve `NULL`/`NaN` no intencionado; los casos borde devuelven 0 o valor definido. |
| AC-503 | Los filtros por planta, línea, máquina, turno, producto y fecha no alteran la definición del KPI. |
| AC-504 | Los joins hecho→dimensión no multiplican conteos (recuento estable). |
| AC-505 | Cada fórmula del código es trazable a su definición en `docs/DATA_DICTIONARY.md`. |

## Fuera de alcance

Visualización (006). El Loss Tree se calcula aquí; se dibuja en 006.

## Dependencias

003 (datos cargados).
