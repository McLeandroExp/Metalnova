# Incremento 003 — Generador histórico (180 días)

Estado: propuesto · Depende de: 002 · Habilita: 004, 005

## Contexto

Genera el conjunto de datos sintéticos que alimenta el histórico del prototipo: 180 días, 3
plantas, 6 líneas, 52 máquinas, con un mínimo de 200 000 eventos de origen (objetivo de diseño
~300 000). Reproducible mediante semilla.

## Requisitos funcionales

| ID | Requisito |
|---|---|
| FR-301 | El generador es reproducible: misma semilla ⇒ mismos datos. |
| FR-302 | Parámetros configurables: días, semilla, intensidad, nº de plantas/máquinas, escenario (base o degradado). |
| FR-303 | Cubre 180 días con estacionalidad por turno y patrón de degradación (OEE decreciente en el tiempo). |
| FR-304 | Emite eventos **por transición**, no snapshots periódicos (Constitución §2). |
| FR-305 | Genera ≥ 200 000 eventos de origen; registra el recuento alcanzado por tabla. |
| FR-306 | Exporta a CSV o Parquet en `data/raw/` (y `data/processed/` si aplica). |
| FR-307 | Registra semilla, parámetros y versión en un manifiesto (`data/processed/manifest.json`). |
| FR-308 | Carga los archivos en PostgreSQL por lotes. |
| FR-309 | Escenario base y escenario degradado seleccionables por parámetro. |
| FR-310 | Incluye microparadas, fallas, cambios de producto, mantenimientos e inspecciones coherentes. |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-301 | Recuentos por tabla reportados y ≥ 200 000 eventos totales. |
| AC-302 | Cobertura temporal exacta de 180 días. |
| AC-303 | Ningún evento de fin anterior a su inicio. |
| AC-304 | Sin cantidades negativas injustificadas. |
| AC-305 | Regenerar con la misma semilla produce recuentos idénticos. |
| AC-306 | Carga en lotes sin exceder la memoria disponible; duración y tamaño de archivo documentados. |
| AC-307 | Claves válidas: 0 huérfanos tras la carga. |

## Fuera de alcance

Simulación en tiempo real (004), definición de vistas KPI (005).

## Dependencias

002 (esquema creado).
