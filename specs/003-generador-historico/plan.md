# Plan — Incremento 003

## Componentes

```text
python/src/generate_history.py   # CLI: genera CSV + manifiesto
python/src/load_history.py       # CLI: carga por lotes a PostgreSQL
python/src/verify_history.py     # CLI: verificación post-carga
python/src/common/
    db.py           # conexión desde variables de entorno
    catalog.py      # lectura del catálogo sembrado por 002
    csvio.py        # escritura CSV atómica y streaming
    simulation.py   # motor de simulación por transición
```

## Modelo de simulación

- El catálogo estático (plantas, líneas, 52 máquinas, familias, productos, turnos, causas,
  técnicos, calendario) ya está sembrado por el incremento 002.
- Máquinas con tiempo de ciclo ideal por producto; estados `RUNNING`, `IDLE`, `DOWN`, `MAINT`.
- Eventos por **transición de estado** (arranque, parada, fin de reparación).
- Fallas con tasa específica por criticidad de máquina, turno y degradación.
- Producto por orden; el cambio de producto genera una parada **planificada** y ajusta el ciclo.
- Energía proporcional al runtime con deriva por degradación.
- Temperatura correlacionada con carga y degradación; las excursiones térmicas emiten lecturas
  cada 15 min para que la regla de alerta del 005 sea verificable.
- Descanso de turno registrado como parada planificada (causa `DESCANSO`) para que el downtime
  planificado sea trazable.

## Reproducibilidad

- `random.Random(semilla)` sembrado explícitamente. No se usa `numpy` para evitar una dependencia
  de ~100 MB en la imagen.
- Recorrido estable día → turno → máquina y `run_id` determinista a partir de la versión y los
  parámetros.
- Manifiesto JSON con semilla, parámetros, versión, `run_id`, recuentos y tamaños por tabla.

## Carga

- `COPY` CSV por lotes de 10 000 filas a una tabla temporal y `INSERT … ON CONFLICT DO NOTHING`.
- No cargar todo el histórico en memoria.
- Idempotente por `run_id`; si la base contiene otra ejecución, exige `--reset` explícito.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Volumen excesivo por snapshots | Emisión por transición; validar recuento antes de cargar |
| Carga lenta | Lotes + `COPY`; medir duración |
| Correlaciones irreales | Revisar distribuciones con consultas de validación |
