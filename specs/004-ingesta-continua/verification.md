# Verificación — Incremento 004

Estado: **hecho** · Fecha: 2026-10-21 · Entorno: PostgreSQL 16.4-alpine en Docker
(`metalinova_db`, healthy), histórico `hist-h55dac4e285` (180 días) + ingesta simulada
`sim-*`. Reloj de las pruebas: UTC. Todos los datos son **sintéticos**.

## Comandos ejecutados

```powershell
# Imagen con el código del 004
docker compose build ingestor

# AC-401 / AC-403: un ciclo con reloj fijo (reproducible)
docker compose --profile tools run --rm ingestor python src/simulate_events.py --once --at 2026-10-21T00:10:00Z

# AC-402: repetir exactamente el mismo ciclo
docker compose --profile tools run --rm ingestor python src/simulate_events.py --once --at 2026-10-21T00:10:00Z

# AC-402 (ON CONFLICT): repetir el escenario con el mismo reloj
docker compose --profile tools run --rm ingestor python src/simulate_events.py --scenario stop M-001 --once --at 2026-10-21T00:15:00Z

# AC-404: SIGINT real al proceso en ejecución
docker compose --profile tools run -d --name metalnova_sim_signal ingestor python src/simulate_events.py --interval 5
docker kill -s INT metalnova_sim_signal

# AC-405: puerto de base inaccesible (sin detener el servicio)
docker compose --profile tools run --rm -e POSTGRES_PORT=5999 ingestor python src/simulate_events.py --once --retry-delay 0.2 --max-attempts 3

# AC-406: escenario reproducible de parada
docker compose --profile tools run --rm ingestor python src/simulate_events.py --scenario stop M-001 --once --at 2026-10-21T00:15:00Z

# FR-402: cobertura de 52 máquinas y 3 plantas (10 h simuladas, sin insertar)
docker compose --profile tools run --rm ingestor python src/simulate_events.py --cycles 600 --at 2026-10-20T19:00:00Z --dry-run

# Regresiones
docker compose --profile tools run --rm ingestor python src/verify_history.py
docker compose --profile tools run --rm ingestor python src/validate_data.py
docker compose --profile tools run --rm ingestor python src/load_history.py
```

Evidencia: `logs/ingest_004_ac401.txt`, `_ac402.txt`, `_ac402_scenario.txt`, `_ac404.txt`,
`_ac405.txt`, `_ac405_metrics.json`, `_ac406.txt`, `_cobertura.txt`, `_verify_history.txt`,
`_validate_data.txt`, `_load_history_idem.txt`, `_evidence.txt` y
`logs/simulate_events_<run_id>.json`.

## Criterios de aceptación

| AC | Comando | Salida esperada | Salida observada | Fecha | Veredicto |
|---|---|---|---|---|---|
| AC-401 | `simulate_events.py --once --at …` + `SELECT count(*)` | recuento aumenta | `fact_evento` 405.995 → **405.997** (+2), `fact_parada` 76.827 → **76.828** (+1); run `sim-20261021T002026-f42948` | 2026-10-21 | superada |
| AC-402 | repetir el mismo ciclo y el mismo escenario | sin duplicados | mismo ciclo: `eventos=0 insertados=0`, recuentos estables. Mismo escenario: `eventos=2 insertados=0 duplicados=2`, `paradas_duplicadas=1`; recuentos estables | 2026-10-21 | superada |
| AC-403 | `SELECT avg/max(ingested_at − generated_at) WHERE run_id=…` | latencia medida por ejecución | 0,035976 s · 0,028917 s · 0,004411 s (media = máx. en cada run); registrada también en el JSON de cada ejecución | 2026-10-21 | superada |
| AC-404 | `docker kill -s INT` | salida limpia | log `interrupción recibida (Ctrl+C/SIGTERM); cerrando de forma controlada`, `motivo=interrumpido`, `EXIT_CODE=0` | 2026-10-21 | superada |
| AC-405 | `POSTGRES_PORT=5999` | error comprensible | 2 WARNING de reintento + `ERROR no se pudo conectar a PostgreSQL: … tras 3 intentos (OperationalError)`; `EXIT_CODE=2`; JSON con `exit_reason=error_conexion` | 2026-10-21 | superada |
| AC-406 | `--scenario stop M-001` + consulta KPI | un KPI cambia | M-001 pasa de **sin fila** a `downtime_no_planificado_min=20`, `fallas=1`, `MTBF=NULL`; planta P-NORTE 5 → **25 min**, fallas 0 → **1** | 2026-10-21 | superada |

## AC-401 · Aparición de eventos nuevos

Ciclo `2026-10-21T00:10:00Z`, semilla 42. La máquina 2 (M-002) inicia una microparada de 3 min.
Se insertaron 2 eventos y 1 parada:

```text
source_system | source_event_id           | tipo_evento      | id_maquina | event_time            | estado
iot           | sim-down-002-1792541400   | transicion_estado| 2          | 2026-10-21 00:10:00Z  | DOWN
iot           | sim-parada-002-1792541400 | parada           | 2          | 2026-10-21 00:10:00Z  | DOWN
```

La parada quedó en `fact_parada` como `microparada` de 3 min, turno C, `id_tiempo=20261020`
(fecha de inicio del turno que cruza medianoche) y causa `MICRO`.

## AC-402 · No duplicación al reiniciar

Hay dos caminos, ambos verificados:

1. **Mismo ciclo:** al repetir `--at 2026-10-21T00:10:00Z`, el simulador detecta que la parada
   sigue abierta y no genera eventos (`eventos=0`). Los recuentos no cambian.
2. **Mismo escenario (ON CONFLICT):** al repetir `--scenario stop M-001 --at 2026-10-21T00:15:00Z`,
   el lote se vuelve a generar con los mismos `source_event_id`, pero la base responde
   `insertados=0`, `duplicados=2` y `parada_insertada=no (ya existía)`. El `ON CONFLICT` cubre
   `(source_system, source_event_id)` en eventos y `(id_maquina, inicio_at)` en paradas.

Recuentos tras todas las pruebas: `fact_evento=406.001`, `fact_parada=76.830` (3 paradas
simuladas: M-002 00:10, M-001 00:15 y M-011 00:23), sin filas repetidas.

## AC-403 · Latencia por ejecución

| run_id | Eventos | Primer `generated_at` | Primer `ingested_at` | Latencia media (s) | Latencia máx. (s) |
|---|---|---:|---|---:|---:|
| `sim-20261021T002026-f42948` | 2 | 00:20:26.832997Z | 00:20:26.868973Z | 0,035976 | 0,035976 |
| `sim-20261021T002330-83c5c0` | 2 | 00:23:30.300406Z | 00:23:30.329323Z | 0,028917 | 0,028917 |
| `sim-20261021T002408-e602e5` | 2 | 00:24:08.520372Z | 00:24:08.524783Z | 0,004411 | 0,004411 |

Se usa `ingested_at − generated_at` (latencia de pipeline), según la Constitución §6 y
`docs/DATA_DICTIONARY.md`. El objetivo de < 10 min se cumple con margen: la peor medición fue
**36 ms**. `ingested_at − event_time` se conserva como desfase de evento y puede ser mayor porque
`event_time` es el inicio del slot simulado.

## AC-404 · Salida limpia con Ctrl+C

```text
2026-10-21T00:23:30Z INFO ciclo=1 ... eventos=2 paradas=1 insertados=2 ...
2026-10-21T00:23:38Z INFO interrupción recibida (Ctrl+C/SIGTERM); cerrando de forma controlada
2026-10-21T00:23:38Z INFO fin run_id=sim-20261021T002330-83c5c0 ... motivo=interrumpido
EXIT_CODE=0 STATUS=exited
```

El manejador de `SIGINT`/`SIGTERM` escribe el JSON de métricas y cierra la conexión antes de
salir con código 0.

## AC-405 · Errores comprensibles y reintentos limitados

Con el puerto de PostgreSQL apuntando a `5999`:

```text
WARNING error de base en conexión (OperationalError) intento 1/3; reintento en 0.2 s
WARNING error de base en conexión (OperationalError) intento 2/3; reintento en 0.4 s
ERROR no se pudo conectar a PostgreSQL: no se pudo completar conexión tras 3 intentos (OperationalError)
EXIT_CODE=2
```

`logs/ingest_004_ac405_metrics.json` registra `run_id`, `exit_reason=error_conexion` y el tipo de
error. Los mensajes no incluyen usuario, contraseña ni cadena de conexión. El *backoff* es
exponencial (0,2 s → 0,4 s) y el número de intentos es configurable.

## AC-406 · El escenario altera un KPI observable

Antes del escenario no existía fila para M-001 en el turno C del 2026-10-20. Después:

| Consulta | Antes | Después |
|---|---|---|
| `v_kpi_mantenimiento_maquina_turno` M-001 · 2026-10-20 · C | sin fila | `tiempo_operativo_min=0`, `downtime_no_planificado_min=20`, `fallas=1`, `paradas_no_planificadas=1`, `mtbf_h=NULL` |
| `v_kpi_mantenimiento_planta_dia` P-NORTE · 2026-10-20 | `downtime=5`, `fallas=0` | `downtime=25`, `fallas=1` |

El escenario inserta una parada de 20 min con causa fija `F-MEC` (no planificada, no microparada)
en la máquina designada y en el turno que contiene el instante `--at`. El KPI cambia porque la
parada se persiste en `fact_parada`; no basta con un evento en `fact_evento`. Si el turno elegido
ya tuviera producción histórica, la vista de downtime prioriza `fact_produccion` y el simulador
emite una advertencia explícita.

## FR-402 · Cobertura de plantas y máquinas

Simulación acelerada de 600 ciclos (10 h) con `--dry-run`:

```text
fin run_id=sim-20261021T002522-a9cb5a ciclos=600 eventos=729 insertados=0 duplicados=0
paradas=363 insertadas=0 latencia_media_ms=0.0 latencia_max_ms=0.0 errores=0
cobertura_maquinas=52/52 cobertura_plantas=3 motivo=completado
```

Las 52 máquinas y las 3 plantas generaron transiciones. El volumen es coherente con la regla de
**eventos por transición** (no snapshots): ~1,2 paradas por minuto en la simulación acelerada, sin
muestrear 52 filas por minuto.

## Regresiones

| Prueba | Comando | Resultado | Fecha | Veredicto |
|---|---|---|---|---|
| Histórico intacto | `verify_history.py` | 17/17 OK; `run_id` histórico único; 6 eventos `sim-*` ignorados por el chequeo histórico | 2026-10-21 | superada |
| KPI siguen validando | `validate_data.py` | 49/49 comprobaciones OK | 2026-10-21 | superada |
| Recarga histórica idempotente | `load_history.py` | 0 filas insertadas en las 6 tablas; no bloquea por los `run_id` `sim-*` | 2026-10-21 | superada |

## Observaciones y límites

- Los `run_id` de la ingesta llevan prefijo `sim-` para separarlos del histórico `hist-*`.
  `load_history.py` y `verify_history.py` se ajustaron para no tratar esos `run_id` como una
  ejecución histórica distinta.
- Las paradas simuladas se identifican por `fact_parada.causa_detalle` con el prefijo
  `Ingesta 004:`. No se añadió una columna `run_id` a `fact_parada` para no alterar el esquema del
  002.
- El simulador no rellena huecos si estuvo detenido: al arrancar retoma el slot actual. Esto es
  intencional (ingesta en vivo, no *backfill*); el histórico cubre el pasado.
- Con `--interval` pequeño la probabilidad por ciclo también baja; para una demo con muchos
  eventos usar `--intensity` > 1 y documentar que es un escenario de prueba.
- Todos los eventos y paradas son **sintéticos** y no representan telemetría real.
