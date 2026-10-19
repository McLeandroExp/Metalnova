# Plan — Incremento 004

## Componentes

```text
python/src/simulate_events.py   # bucle de simulación
python/src/ingest.py            # inserción idempotente y métricas
```

## Diseño

- Bucle con `intervalo_segundos` configurable (env `SIM_INTERVAL_SECONDS`, por defecto 60).
- Estado en memoria de las 52 máquinas; en cada ciclo decide transiciones y las persiste.
- `run_id` (uuid) por arranque; registrado junto a cada evento.
- Inserciones por lote con `ON CONFLICT (source_system, source_event_id) DO NOTHING`.
- Métricas por ciclo: nº eventos, duración, latencia media → log estructurado.
- Cierre limpio con `signal`/`KeyboardInterrupt`.

## Latencia (definición)

Para el objetivo de 10 minutos se usa `ingested_at − generated_at` (pipeline controlado). La
métrica `ingested_at − event_time` se registra aparte porque puede ser negativa (reloj simulado).
Definición fijada en la Constitución §6 y en `docs/DATA_DICTIONARY.md`.

## Escenario reproducible

Máquina designada (p. ej. `M-001`) entra en parada de 20 min con causa fija a petición
(`--scenario stop M-001`), de forma que la demo no dependa de eventos aleatorios.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Duplicados al reiniciar | Clave única + `ON CONFLICT`; prueba AC-402 |
| Conexión abierta indefinidamente | Reconexión con reintentos limitados y *backoff* |
| Fuga de secretos en logs | Logs sin credenciales; `.env` fuera de Git |
