# Runbook de demostración — MetalNova Smart Factory BI

> Estado: borrador avanzado. Se cierra en el incremento 007. Todos los datos son **sintéticos**.

## Guion (5–10 minutos)

1. Explicar el problema de MetalNova y aclarar que **los datos son sintéticos**.
2. Mostrar el esquema: archivos históricos → Python → PostgreSQL → Power BI.
3. Panel ejecutivo: OEE global y último mes, tendencia por planta, comparación y alertas.
4. OEE & Loss Tree: Pareto de downtime, matriz máquina-turno y pérdida por producto.
5. Maintenance Reliability: MTBF, MTTR, fallas cortas, microparadas y tooltip de máquina.
6. Quality & Energy: scrap por planta/turno/producto, FPY y energía por unidad buena.
7. Drill-through a una máquina (OEE, intervenciones y paradas) y a una causa.
8. Iniciar la ingesta simulada y provocar un evento identificable (`--scenario stop M-001`).
9. Mostrar un evento inválido en cuarentena (`--scenario invalid M-001`).
10. Presentar 3–5 acciones priorizadas con impacto, supuesto, responsable y KPI de seguimiento.
11. Explicar limitaciones del prototipo y qué requeriría una implantación real.

## Orden de arranque

```text
1. Arrancar Docker Desktop (si no está activo)
2. docker compose up -d
3. Verificar: docker compose ps  →  db healthy
4. (si hace falta) generar y cargar histórico calibrado:
   generate_history.py --seed 42 --end-date 2026-10-18 --escenario calibracion
   → load_history.py  →  verify_history.py
5. Abrir powerbi/final/MetalNova.pbip y pulsar «Actualizar ahora»
6. Iniciar simulación:
   docker compose --profile tools run --rm ingestor python src/simulate_events.py
```

## Escenario reproducible de parada

Implementado en el incremento 004. La parada de 20 min no depende del azar:

```powershell
# Parada de 20 min en M-001 (causa F-MEC) en el turno actual
docker compose --profile tools run --rm ingestor python src/simulate_events.py `
  --scenario stop M-001 --once
```

Comprobación del cambio en los KPI:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -c "
SELECT fecha, turno_codigo, downtime_no_planificado_min, fallas, mtbf_h
FROM v_kpi_mantenimiento_maquina_turno
WHERE maquina_codigo = 'M-001'
ORDER BY fecha DESC, turno_codigo DESC
LIMIT 3;"
```

Antes del escenario, el turno actual de M-001 no tiene fila; después aparece con
`downtime_no_planificado_min = 20`, `fallas = 1` y `mtbf_h = NULL`. Repetir el mismo comando con el
mismo `--at` no duplica la parada (idempotencia por `(id_maquina, inicio_at)`).

## Escenario de calidad IoT

```powershell
# Evento normal, evento futuro y evento anterior al rango (los dos últimos a cuarentena)
# más un evento tardío que se marca como reordenado.
docker compose --profile tools run --rm ingestor python src/simulate_events.py `
  --scenario invalid M-001 --once
```

Comprobación:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -c "
SELECT source_event_id, motivo, recibido_at
FROM fact_evento_rechazado
ORDER BY id_rechazo DESC LIMIT 4;"
```

Resultado esperado: dos filas en cuarentena (`timestamp_futuro` y
`timestamp_anterior_al_rango`) y dos eventos aceptados; el tardío lleva
`payload.calidad.tardio = true` y `payload.calidad.reordenado = true`.

## Recuperación ante errores

| Síntoma | Acción |
|---|---|
| `db` no saludable | `docker compose logs db`; verificar puerto libre |
| Power BI no ve datos nuevos | refrescar; confirmar modo de conexión DirectQuery |
| Visual vacío tras regenerar PBIR | cerrar Desktop, `python tools/validate_report.py`, reabrir |
| Datos corruptos | restaurar desde `backups/` con `pg_restore` |
| Evento rechazado inesperado | revisar `fact_evento_rechazado.motivo`; el rango válido es `[inicio_histórico − 1 d, ahora + 5 min]` |
