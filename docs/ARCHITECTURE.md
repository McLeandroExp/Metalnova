# Arquitectura — MetalNova Smart Factory BI

> Estado: incrementos 001–007 cerrados. El histórico sintético, la ingesta continua, las 20
> vistas KPI, el informe Power BI verificado y la demo end-to-end están disponibles; el
> histórico base es el **calibrado** (`calibracion`).

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
│                                    Power BI Desktop (DirectQuery)
│                                      4 páginas · 9 KPIs              │
└─────────────────────────────────────────────────────────────────────┘
```

## Flujo de datos

1. `sql/apply_all.sql` crea el esquema, el catálogo de referencia y las vistas base + KPI
   (idempotente).
2. `generate_history.py` produce 180 días de eventos sintéticos en `data/raw/` y el manifiesto en
   `data/processed/manifest.json` (streaming, semilla explícita). El escenario `calibracion`
   aplica factores por planta y perfiles persistentes de máquina; `degradado` conserva la
   parametrización histórica neutra.
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
   `tools/generate_tmdl.py` genera el modelo y `tools/generate_pbir.py` las páginas;
   `tools/validate_report.py` comprueba que cada campo del informe existe en el
   modelo antes de abrirlo en Desktop.

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

### Calidad y temporalidad IoT (G5)

`event_quality.py` clasifica cada evento antes de insertarlo:

| Situación | Resultado |
|---|---|
| `event_time` en `[inicio_histórico − 1 d, ahora + 5 min]` | aceptado |
| fuera de ese rango o nulo | `fact_evento_rechazado` con `motivo` |
| llega más de 5 min después | aceptado con `payload.calidad.tardio = true` |
| `event_time` anterior al último evento de la máquina | aceptado con `payload.calidad.reordenado = true` |
| duplicado | `ON CONFLICT DO NOTHING` |

`v_calidad_senal_iot` resume la cobertura por máquina/día: lecturas recibidas vs
`senal_lecturas_turno_min`, hueco máximo y estado `ok`/`incompleta`/`sin_datos`.
La cadencia ideal de 15 min se informa aparte (`cumple_cadencia_15min`) porque el
feed sintético emite dos lecturas por turno (D-022). No se aplica *carry-forward*:
el hueco se declara, no se rellena.

## Calibración del histórico (006)

El diagnóstico de homogeneidad mostró que las tres plantas diferían solo por ruido (~0,05 pp).
Para que el informe tenga señal, el escenario `calibracion` aplica:

- Factores de rendimiento, fallas, calidad y energía por planta.
- `dim_maquina.perfil_rendimiento`, leído por el generador, con siete máquinas outlier
  persistentes (no ruido diario).
- Una curva de degradación más marcada en rendimiento y más suave en fallas/calidad/energía.

La semilla sigue siendo 42 y el `run_id` incorpora el manifiesto de calibración. El escenario
`degradado` no aplica perfiles ni factores y sigue siendo reproducible. Resultado medido:
OEE 78,02 → 66,00 % en ventanas de 30 días; dispersión entre plantas 8,5 pp al inicio y
7,3 pp al cierre; una máquina en 51,81 % y tres por debajo de 61 %. Detalle en D-020 y en
`specs/006-powerbi/verification.md`.

## Modelo de datos

| Grupo | Objetos |
|---|---|
| Dimensiones | `dim_planta`, `dim_linea`, `dim_maquina`, `dim_familia`, `dim_producto`, `dim_turno`, `dim_causa`, `dim_tecnico`, `dim_tiempo`, `dim_orden` |
| Hechos | `fact_produccion`, `fact_parada`, `fact_mantenimiento`, `fact_calidad`, `fact_evento`, `fact_evento_rechazado` |
| Vistas base | `v_produccion_detalle`, `v_parada_detalle`, `v_mantenimiento_detalle`, `v_calidad_detalle` |
| Consolidación de paradas | `v_parada_consolidada` (D-023; usada por `v_kpi_parada` y `v_kpi_mantenimiento_*`) |
| Vistas KPI (005) | `v_kpi_parametros`, `v_kpi_produccion`, `v_kpi_calidad`, `v_kpi_parada`, `v_kpi_mantenimiento`, 5 `v_kpi_oee_*`, 4 `v_kpi_mantenimiento_*`, 2 `v_kpi_calidad_*`, `v_kpi_confiabilidad_apoyo_maquina_dia`, 2 `v_loss_tree*`, `v_alerta_maquina_critica` |
| Alertas y señal IoT (006) | `v_alerta_ultimo_turno`, `v_calidad_senal_iot` |

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
| Alerta | `v_alerta_maquina_critica`, `v_alerta_ultimo_turno` | fecha × máquina × turno |
| Calidad de señal | `v_calidad_senal_iot` | fecha × máquina |
| Dimensiones BI (006) | `v_dim_maquina`, `v_dim_producto` | una fila por máquina / producto; alimentan el modelo estrella |

Regla: los porcentajes se agregan con `SUM(numerador) / SUM(denominador)`, nunca promediando
porcentajes. Las razones indefinidas devuelven `NULL` (D-014). Los umbrales viven en
`v_kpi_parametros` y la evidencia de validación está en
`specs/005-kpi-y-vistas/verification.md`.

**Consolidación de paradas (D-023):** `v_kpi_parada` y
`v_kpi_mantenimiento_maquina_turno` leen de `v_parada_consolidada`, que une
intervalos estrictamente solapados por máquina. `fact_parada` permanece como capa
cruda y el OEE/Loss Tree siguen usando `fact_produccion.downtime_no_planificado_min`;
la consolidación no altera el OEE, solo Pareto, MTBF, fallas y microparadas.

## Capa de análisis estadístico (incremento 008)

El análisis es una capa de solo lectura sobre PostgreSQL. No crea tablas, vistas ni cambios de
esquema; consume las vistas KPI y los hechos, calcula en Python y escribe artefactos:

```text
PostgreSQL ──▶ analyze_data.py ──┬──▶ docs/ANALISIS_DATOS.md
  (vistas + hechos)              ├──▶ docs/analysis/figures/F01..F18.png
                                 ├──▶ docs/analysis/manifest.json
                                 ├──▶ data/analysis/<run_id>/*.csv
                                 └──▶ logs/analyze_data_<run_id>.log
```

- **Dependencias:** pandas, numpy, scipy y matplotlib con versión fija en
  `python/requirements-analysis.txt`; se instalan en la imagen del ingestor.
- **Montaje:** `compose.yaml` monta `./docs` en `/app/docs` para que el contenedor escriba el
  informe y las figuras.
- **Niveles:** fila, máquina-día, máquina-turno, planta-día y máquina agregada (D-024).
- **Validación:** `validate_analysis.py` recalcula en SQL y compara con los CSV (`1e-9`);
  `sql/validation/08_analisis.sql` comprueba estructura y cobertura.
- **Reproducibilidad:** semilla 42, filtros declarados y SHA-256 de 42 archivos en el
  manifiesto (D-027).
- **Alcance:** descriptivo e inferencial; no causal, no predictivo y sin cambios en Power BI.

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
