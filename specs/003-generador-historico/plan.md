# Plan — Incremento 003

## Componentes

```text
python/src/generate_history.py   # genera CSV/Parquet + manifiesto
python/src/load_history.py       # carga por lotes a PostgreSQL
python/src/common/               # catálogos, modelo de máquina, utilidades RNG
```

## Modelo de simulación

- Máquinas con tiempo de ciclo ideal por producto; estados `RUNNING`, `IDLE`, `DOWN`, `MAINT`.
- Eventos por **transición de estado** (arranque, parada, fin de reparación).
- Fallas con distribución por máquina (Machine-specific failure rate).
- Producto por orden; cambio de producto genera microparada y ajuste de ciclo.
- Energía proporcional al runtime con deriva por degradación.
- Temperatura correlacionada con runtime y carga.

## Reproducibilidad

- `random.Random(semilla)` y `numpy.default_rng(semilla)` sembrados explícitamente.
- Manifiesto JSON con semilla, parámetros, versión y recuentos por tabla.

## Carga

- `COPY`/`execute_values` por lotes (p. ej. 5 000–10 000 filas).
- No cargar todo el histórico en memoria.
- Idempotente: `ON CONFLICT DO NOTHING` sobre claves estables.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Volumen excesivo por snapshots | Emisión por transición; validar recuento antes de cargar |
| Carga lenta | Lotes + `COPY`; medir duración |
| Correlaciones irreales | Revisar distribuciones con consultas de validación |
