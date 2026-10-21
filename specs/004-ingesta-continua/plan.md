# Plan — Incremento 004

## Componentes

```text
python/src/simulate_events.py   # bucle de simulación
python/src/ingest.py            # inserción idempotente y métricas
```

## Diseño

- Bucle con `intervalo_segundos` configurable (env `SIM_INTERVAL_SECONDS`, por defecto 60).
- Cada ciclo se alinea a una rejilla temporal (`slot`) y decide transiciones por máquina con
  `SHA-256(semilla, máquina, slot)`. No se depende del estado en memoria: las paradas abiertas se
  consultan en `fact_parada`, de modo que un reinicio retoma el estado real.
- `run_id` (`sim-<timestamp>-<sufijo>`) por arranque; registrado junto a cada evento.
- Inserciones por lote con `ON CONFLICT (source_system, source_event_id) DO NOTHING` para eventos y
  `ON CONFLICT (id_maquina, inicio_at) DO NOTHING` para paradas.
- Métricas por ciclo: nº eventos, duración, latencia media → log estructurado en
  `logs/simulate_events.log` y JSON por ejecución.
- Cierre limpio con `signal`/`KeyboardInterrupt`; reintentos limitados con *backoff*.
- Las paradas generadas se persisten en `fact_parada` (no solo como evento) para que alteren los
  KPI de mantenimiento.

## Latencia (definición)

Para el objetivo de 10 minutos se usa `ingested_at − generated_at` (pipeline controlado). La
métrica `ingested_at − event_time` se registra aparte porque puede ser negativa (reloj simulado).
Definición fijada en la Constitución §6 y en `docs/DATA_DICTIONARY.md`.

## Escenario reproducible

Máquina designada (p. ej. `M-001`) entra en parada de 20 min con causa fija a petición
(`--scenario stop M-001`), de forma que la demo no dependa de eventos aleatorios. La parada se
inserta en `fact_parada` y sus eventos IoT; repetir el comando con el mismo reloj no duplica
registros (AC-406).

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Duplicados al reiniciar | Clave única + `ON CONFLICT`; prueba AC-402 |
| Conexión abierta indefinidamente | Reconexión con reintentos limitados y *backoff* |
| Fuga de secretos en logs | Logs sin credenciales; `.env` fuera de Git |
