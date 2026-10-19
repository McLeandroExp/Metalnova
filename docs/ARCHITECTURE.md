# Arquitectura — MetalNova Smart Factory BI

> Estado: borrador inicial (incremento 001). Se completa a medida que avanzan los incrementos.

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

1. `generate_history.py` produce 180 días de eventos sintéticos en `data/`.
2. `load_history.py` carga por lotes en PostgreSQL (idempotente).
3. `simulate_events.py` genera eventos nuevos cada minuto y los inserta idempotentemente.
4. Las vistas `v_*` exponen KPIs con contrato estable.
5. Power BI Desktop consume las vistas.

## Puertos y volúmenes

| Elemento | Valor |
|---|---|
| Puerto PostgreSQL | `127.0.0.1:5432` (solo loopback) |
| Puerto pgAdmin | `127.0.0.1:5050` (solo loopback) |
| Volumen de datos | `metalinova_pgdata` |
| Volumen de pgAdmin | `metalinova_pgadmin` |
| Carpeta montada | `./data` → contenedor |
| Logs | `./logs` |

## Responsabilidades por servicio

| Servicio | Responsabilidad |
|---|---|
| `db` | Almacén analítico; esquema, hechos, dimensiones y vistas |
| `pgadmin` | Cliente web para inspeccionar la base (verificación manual) |
| `ingestor` | Generación, carga y simulación; se ejecuta por comando, no en bucle |
| Power BI Desktop | Visualización (fuera de Docker) |
