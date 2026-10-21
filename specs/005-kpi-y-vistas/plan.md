# Plan — Incremento 005

## Organización

```text
sql/views/02_kpi_base.sql         # disponibilidad, rendimiento, calidad
sql/views/03_kpi_oee.sql          # OEE y componentes consolidados
sql/views/04_kpi_mantenimiento.sql# MTBF, MTTR, downtime
sql/views/05_kpi_calidad_energia.sql
sql/views/06_kpi_confiabilidad.sql# microparadas, fallas cortas
sql/views/07_loss_tree.sql
sql/views/08_alerta_maquina_critica.sql
python/src/validate_data.py       # validación independiente (contra las vistas)
```

## Convenciones

- Prefijo `v_` para vistas analíticas; sufijo de grano (`_planta`, `_maquina_turno`).
- Fórmulas con nombres explícitos: `disponibilidad`, `rendimiento`, `calidad`, `oee`.
- División segura: `NULLIF(denominador, 0)`; una razón indefinida devuelve `NULL`
  (D-014), nunca `NaN` ni un cero que oculte la falta de base.
- OEE siempre ponderado por denominador, nunca promedio de porcentajes.
- Umbrales centralizados en `v_kpi_parametros` (microparada 5 min, falla corta 30 min,
  MTBF 20 h, OEE 0,55, downtime 120 min, temperatura 85 °C/15 min/2 lecturas).

## Validación independiente

`validate_data.py` recalcula cada KPI desde los hechos crudos y compara con la vista; imprime
tabla de diferencias y devuelve código distinto de cero si se excede la tolerancia.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Definiciones divergentes SQL vs DAX | Vista única como contrato; DAX solo agrega |
| Multiplicación por joins | Validación de recuentos antes/después |
| Microparada mal clasificada | Umbral `microparada_min=5` centralizado en la vista |
