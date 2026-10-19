# Incremento 002 — Modelo dimensional SQL

Estado: propuesto · Depende de: 001 · Habilita: 003

## Contexto

Define el esquema analítico sobre el que se cargan los datos y se construyen los KPI. Esquema
estrella con múltiples hechos y dimensiones conformadas, con jerarquías Planta→Línea→Máquina y
Familia→Producto (enmienda G1).

## Requisitos funcionales

| ID | Requisito |
|---|---|
| FR-201 | Crear las dimensiones `dim_planta`, `dim_linea`, `dim_maquina`, `dim_turno`, `dim_producto`, `dim_familia`, `dim_causa`, `dim_tiempo`, `dim_tecnico`. |
| FR-202 | Crear los hechos `fact_produccion`, `fact_parada`, `fact_mantenimiento`, `fact_calidad`. |
| FR-203 | Crear `fact_evento` (aterrizaje crudo) con clave única `(source_system, source_event_id)`. |
| FR-204 | Crear `fact_evento_rechazado` con `motivo` y payload original. |
| FR-205 | Declarar claves primarias, foráneas y restricciones de no-negatividad y de orden temporal (`fin >= inicio`). |
| FR-206 | Documentar el **grano** de cada tabla en el propio esquema (comentarios SQL) y en `docs/DATA_DICTIONARY.md`. |
| FR-207 | Scripts DDL versionados e **idempotentes** (`CREATE ... IF NOT EXISTS`, migraciones controladas). |
| FR-208 | Índices basados en los filtros y joins reales (fechas, máquina, planta, causa, turno). |
| FR-209 | `fact_calidad` incluye `es_retrabajo` para hacer calculable el FPY (G3). |
| FR-210 | `fact_evento` incluye señal `temperatura_c` y `energia_kwh` para la regla de alerta (G2). |
| FR-211 | Vistas base `v_*` que exponen los hechos con sus dimensiones para Power BI. |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-201 | El esquema se crea desde cero en una base limpia sin errores. |
| AC-202 | Re-ejecutar los scripts no duplica objetos ni destruye datos. |
| AC-203 | No existen claves huérfanas (consulta de integridad devuelve 0 filas). |
| AC-204 | Toda tabla de hechos tiene foráneas válidas a las dimensiones conformadas. |
| AC-205 | `docs/DATA_DICTIONARY.md` describe tabla, columnas, tipos, claves, grano y definición de KPI. |
| AC-206 | Las jerarquías Planta→Línea→Máquina y Familia→Producto se pueden recorrer con un `JOIN` sin duplicar filas del hecho. |

## Fuera de alcance

Carga de datos (003), medidas DAX (006), particionado avanzado.

## Dependencias

001 (base operativa).
