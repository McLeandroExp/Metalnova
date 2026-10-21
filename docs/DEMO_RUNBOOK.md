# Runbook de demostración — MetalNova Smart Factory BI

> Estado: borrador inicial. Se completa en el incremento 007.

## Guion (5–10 minutos)

1. Explicar el problema de MetalNova y aclarar que **los datos son sintéticos**.
2. Mostrar el esquema: archivos históricos → Python → PostgreSQL → Power BI.
3. Panel ejecutivo: 3 plantas y 52 máquinas.
4. OEE & Loss Tree: identificar una pérdida relevante.
5. Maintenance Reliability: relacionar paradas con una causa o equipo.
6. Quality & Energy: mostrar una tendencia de scrap o energía.
7. Iniciar la ingesta simulada y provocar un evento identificable (`--scenario stop M-001`).
8. Mostrar el registro en PostgreSQL y cuándo se refleja en Power BI según el modo validado.
9. Presentar 3–5 acciones priorizadas con impacto, supuesto, responsable y KPI de seguimiento.
10. Explicar limitaciones del prototipo y qué requeriría una implantación real.

## Orden de arranque

```text
1. Arrancar Docker Desktop (si no está activo)
2. docker compose up -d
3. Verificar: docker compose ps  →  db healthy
4. (si hace falta) generar y cargar histórico:
   generate_history.py --seed 42  →  load_history.py  →  verify_history.py
5. Iniciar simulación:
   docker compose --profile tools run --rm ingestor python src/simulate_events.py
6. Abrir powerbi/MetalNova.pbix y refrescar según el modo validado
```

## Escenario reproducible

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

Para una demostración con más actividad, usar `--intensity 2` o dejar el bucle corriendo varios
minutos. Todos los eventos son sintéticos.

## Recuperación ante errores

| Síntoma | Acción |
|---|---|
| `db` no saludable | `docker compose logs db`; verificar puerto libre |
| Power BI no ve datos nuevos | refrescar; confirmar modo de conexión |
| Datos corruptos | restaurar desde `backups/` con `pg_restore` |
