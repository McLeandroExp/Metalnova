# Arquitectura — MetalNova Smart Factory BI

> Estado: incrementos 001, 002, 003, 004 y 005 cerrados. El histórico sintético, la ingesta
> continua y las 20 vistas KPI ya están disponibles en PostgreSQL; Power BI corresponde al
> incremento 006.

## Diagrama de componentes

```text
┌──────────────────────── Windows 11 (8 GB) ─────────────────────────┐
│                                                                     │
│  Docker Desktop (WSL2, ~3,7 GB)                                     │
│  ┌───────────────────────────┐   ┌──────────────────────────────┐   │
│  │ ingestor (Python)         │   │ db (PostgreSQL)              │   │
│  │  generate_history.py      │──▶│  esquema + hechos            │   │
│  │  load_history.py          │   │  + 20 vistas KPI             │   │
│  │  validate_data.py         │   │  volumen metalinova_pgdata   │   │
│  │  simulate_events.py       │   │  127.0.0.1:5432              │   │
│  │  ingest.py                │   │                              │   │
│  └───────────────────────────┘   └───────────────┬──────────────┘   │
│                                                  │                  │
│  ┌───────────────┐              ┌────────────────┴──────────────┐   │
│  │ data/ (vol.)  │              │ pgadmin (cliente web)         │   │
│  └───────────────┘              │  127.0.0.1:5050               │   │
│                                 └───────────────────────────────┘   │
│                                                  │                  │
│                                                  ▼                  │
│                                    Power BI Desktop (Import/DirectQuery)
│                                      4 páginas · 9 KPIs              │
└─────────────────────────────────────────────────────────────────────┘
```

## Flujo de datos

1. `sql/apply_all.sql` crea el esquema, el catálogo de referencia y las vistas base + KPI
   (idempotente).
2. `generate_history.py` produce 180 días de eventos sintéticos en `data/raw/` y el manifiesto en
   `data/processed/manifest.json` (streaming, semilla explícita).
3. `load_history.py` carga por lotes en PostgreSQL con `COPY` + `ON CONFLICT DO NOTHING`
   (idempotente por `run_id`; exige `--reset` para reemplazar otra ejecución).
4. `verify_history.py` y `sql/validation/02_historico.sql` comprueban volumen, cobertura,
   coherencia de fechas, huérfanos y reglas de parada.
5. `simulate_events.py` (incremento 004) emite eventos por transición y los inserta de forma
   idempotente a través de `ingest.py` (`ON CONFLICT` sobre la clave estable, transacciones por
   lote y reintentos con *backoff*). `--scenario stop M-001` provoca una parada observable en los
   KPI.
6. `validate_data.py` (incremento 005) recalcula los KPI desde los hechos crudos, comprueba
   aditividad y casos borde, y compara contra las vistas con tolerancia `1e-9`.
7. Power BI Desktop (incremento 006) consume las vistas KPI como contrato estable.

## Capa de ingesta continua (incremento 004)

| Elemento | Detalle |
|---|---|
| Componentes | `simulate_events.py` (bucle y decisiones) + `ingest.py` (escritura y métricas) |
| Grano | evento por transición de estado; parada por episodio |
| Idempotencia | `(source_system, source_event_id)` y `(id_maquina, inicio_at)` con `ON CONFLICT DO NOTHING` |
| Reloj | slot alineado a `--interval`; `--at` para pruebas reproducibles |
| `run_id` | `sim-<timestamp>-<sufijo>` (separado del histórico `hist-*`) |
| Latencia | `ingested_at − generated_at`; objetivo < 10 min |
| Escenario | `--scenario stop M-001` (20 min, causa `F-MEC`) |
| Logs | `logs/simulate_events.log` + un JSON por ejecución |
| Reintentos | 3 por defecto con *backoff* exponencial; código de salida 2 si se agotan |

El simulador no rellena huecos si estuvo detenido: retoma el slot actual. Las paradas que genera
quedan marcadas con `causa_detalle = 'Ingesta 004: …'`, de modo que se distinguen del histórico
sin añadir columnas al esquema del 002.

## Modelo de datos

| Grupo | Objetos |
|---|---|
| Dimensiones | `dim_planta`, `dim_linea`, `dim_maquina`, `dim_familia`, `dim_producto`, `dim_turno`, `dim_causa`, `dim_tecnico`, `dim_tiempo`, `dim_orden` |
| Hechos | `fact_produccion`, `fact_parada`, `fact_mantenimiento`, `fact_calidad`, `fact_evento`, `fact_evento_rechazado` |
| Vistas base | `v_produccion_detalle`, `v_parada_detalle`, `v_mantenimiento_detalle`, `v_calidad_detalle` |
| Vistas KPI (005) | `v_kpi_parametros`, `v_kpi_produccion`, `v_kpi_calidad`, `v_kpi_parada`, `v_kpi_mantenimiento`, 5 `v_kpi_oee_*`, 4 `v_kpi_mantenimiento_*`, 2 `v_kpi_calidad_*`, `v_kpi_confiabilidad_apoyo_maquina_dia`, 2 `v_loss_tree*`, `v_alerta_maquina_critica` |

Jerarquías: `dim_planta → dim_linea → dim_maquina` y `dim_familia → dim_producto`.

## Capa KPI (incremento 005)

Las vistas son el contrato único para SQL, Python y DAX. Se agrupan en:

| Grupo | Vistas | Grano |
|---|---|---|
| Base de hechos | `v_kpi_produccion`, `v_kpi_calidad`, `v_kpi_parada`, `v_kpi_mantenimiento` | fila de hecho |
| OEE | `v_kpi_oee_planta_dia`, `_linea_dia`, `_maquina_dia`, `_maquina_turno`, `_producto_dia` | fecha × dimensión |
| Mantenimiento | `v_kpi_mantenimiento_maquina_turno`, `_maquina_dia`, `_maquina_mes`, `_planta_dia` | fecha/mes × máquina/planta |
| Confiabilidad | `v_kpi_confiabilidad_apoyo_maquina_dia` | fecha × máquina |
| Calidad/energía | `v_kpi_calidad_maquina_dia`, `v_kpi_calidad_producto_dia` | fecha × máquina/producto |
| Loss Tree | `v_loss_tree`, `v_loss_tree_maquina_mes` | fila de producción / mes × máquina |
| Alerta | `v_alerta_maquina_critica` | fecha × máquina × turno |

Regla: los porcentajes se agregan con `SUM(numerador) / SUM(denominador)`, nunca promediando
porcentajes. Las razones indefinidas devuelven `NULL` (D-014). Los umbrales viven en
`v_kpi_parametros` y la evidencia de validación está en
`specs/005-kpi-y-vistas/verification.md`.

## Puertos y volúmenes

| Elemento | Valor |
|---|---|
| Puerto PostgreSQL | `127.0.0.1:5432` (solo loopback) |
| Puerto pgAdmin | `127.0.0.1:5050` (solo loopback) |
| Volumen de datos | `metalinova_pgdata` |
| Volumen de pgAdmin | `metalinova_pgadmin` |
| Carpeta montada | `./data` → contenedor |
| Scripts SQL | `./sql` → `/sql` (solo lectura) |
| Logs | `./logs` |

## Responsabilidades por servicio

| Servicio | Responsabilidad |
|---|---|
| `db` | Almacén analítico; esquema, hechos, dimensiones, vistas base y 20 vistas KPI |
| `pgadmin` | Cliente web para inspeccionar la base (verificación manual) |
| `ingestor` | Generación, carga, verificación, validación de KPI y simulación; se ejecuta por comando |
| Power BI Desktop | Visualización (fuera de Docker) |
