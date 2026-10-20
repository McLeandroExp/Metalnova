# Arquitectura — MetalNova Smart Factory BI

> Estado: incrementos 001–003 cerrados. El histórico sintético ya está disponible en PostgreSQL;
> las vistas KPI y Power BI corresponden a los incrementos 005 y 006.

## Diagrama de componentes

```text
┌──────────────────────── Windows 11 (8 GB) ─────────────────────────┐
│                                                                     │
│  Docker Desktop (WSL2, ~3,7 GB)                                     │
│  ┌───────────────────────────┐   ┌──────────────────────────────┐   │
│  │ ingestor (Python)         │   │ db (PostgreSQL)              │   │
│  │  generate_history.py      │──▶│  esquema + hechos + vistas   │   │
│  │  load_history.py          │   │  volumen metalinova_pgdata   │   │
│  │  simulate_events.py       │   │  127.0.0.1:5432              │   │
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

1. `sql/apply_all.sql` crea el esquema y el catálogo de referencia (idempotente).
2. `generate_history.py` produce 180 días de eventos sintéticos en `data/raw/` y el manifiesto en
   `data/processed/manifest.json` (streaming, semilla explícita).
3. `load_history.py` carga por lotes en PostgreSQL con `COPY` + `ON CONFLICT DO NOTHING`
   (idempotente por `run_id`; exige `--reset` para reemplazar otra ejecución).
4. `verify_history.py` y `sql/validation/02_historico.sql` comprueban volumen, cobertura,
   coherencia de fechas, huérfanos y reglas de parada.
5. `simulate_events.py` (incremento 004) generará eventos nuevos y los insertará
   idempotentemente.
6. Las vistas `v_*` (incremento 005) expondrán KPIs con contrato estable.
7. Power BI Desktop (incremento 006) consume las vistas.

## Modelo de datos

| Grupo | Objetos |
|---|---|
| Dimensiones | `dim_planta`, `dim_linea`, `dim_maquina`, `dim_familia`, `dim_producto`, `dim_turno`, `dim_causa`, `dim_tecnico`, `dim_tiempo`, `dim_orden` |
| Hechos | `fact_produccion`, `fact_parada`, `fact_mantenimiento`, `fact_calidad`, `fact_evento`, `fact_evento_rechazado` |
| Vistas base | `v_produccion_detalle`, `v_parada_detalle`, `v_mantenimiento_detalle`, `v_calidad_detalle` |

Jerarquías: `dim_planta → dim_linea → dim_maquina` y `dim_familia → dim_producto`.

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
| `db` | Almacén analítico; esquema, hechos, dimensiones y vistas |
| `pgadmin` | Cliente web para inspeccionar la base (verificación manual) |
| `ingestor` | Generación, carga y simulación; se ejecuta por comando, no en bucle |
| Power BI Desktop | Visualización (fuera de Docker) |
