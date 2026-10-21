# Verificación — Incremento 005

Estado: **hecho** · Fecha: 2026-10-20 · Entorno: PostgreSQL 16.4-alpine en Docker,
histórico sintético `hist-h55dac4e285` (180 días, 2026-04-22 → 2026-10-18).

## Comandos ejecutados

```powershell
# 1. Aplicar esquema + vistas (idempotente)
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/apply_all.sql

# 2. Validación independiente (recalcula desde los hechos y compara con las vistas)
docker compose --profile tools run --rm ingestor python src/validate_data.py

# 3. Comprobaciones SQL de contrato, parámetros y agregados
docker compose exec -T db psql -U metalinova -d metalinova -P pager=off -c "..."
```

Evidencia completa en `logs/validation_005.txt` (49 comprobaciones + resumen global) y
`logs/kpi_checks_005.txt` (contrato, parámetros, OEE mensual, alertas y Loss Tree).

## Criterios de aceptación

| AC | Comando | Salida esperada | Salida observada | Fecha | Veredicto |
|---|---|---|---|---|---|
| AC-501 | `validate_data.py` | diferencias < tolerancia | `49/49 comprobaciones OK`; diferencia máxima `4,366e-11` (límite `1e-9`) | 2026-10-20 | superada |
| AC-502 | `validate_data.py` | solo valores definidos | `0` incidencias de `NULL`/`NaN` no intencionado; 3 casos borde con `NULL` documentado | 2026-10-20 | superada |
| AC-503 | `validate_data.py` | definición estable con filtros | sumas aditivas OK en 5 vistas OEE, 4 de mantenimiento y Loss Tree; OEE global = suma ponderada de plantas | 2026-10-20 | superada |
| AC-504 | `validate_data.py` | recuento estable | `v_kpi_produccion` 28.080 = 28.080; `v_kpi_calidad` 28.080 = 28.080; `v_kpi_parada` 76.827 = 76.827; `v_kpi_mantenimiento` 4.400 = 4.400; `v_loss_tree` 28.080 = 28.080 | 2026-10-20 | superada |
| AC-505 | `information_schema.views` + diccionario | trazable | 20 vistas KPI presentes; tabla de trazabilidad en `docs/DATA_DICTIONARY.md` | 2026-10-20 | superada |

## Comparación SQL vs Python

Los valores globales se obtuvieron con la consulta SQL de `logs/kpi_checks_005.txt` y con el
resumen que `validate_data.py` recalcula desde los hechos. La tolerancia efectiva es `1e-9`
(más estricta que el 0,1 % del spec).

| KPI | Grano | Valor SQL | Valor Python | Diferencia |
|---|---|---|---|---|
| OEE | global (suma ponderada) | 0,8447 | 0,8447 | 0,0000 (dif. máx. por fila 2,22e-16) |
| Disponibilidad | global | 0,9857 | 0,9857 | 0,0000 |
| Rendimiento | global | 0,8851 | 0,8851 | 0,0000 |
| Calidad | global | 0,9683 | 0,9683 | 0,0000 |
| MTBF | global | 49,46 h | 49,46 h | 0,0000 |
| MTTR | global | 17,45 min | 17,45 min | 0,0000 |
| FPY | máquina × día | 0,9704 – 0,9980 | validado fila a fila | dif. máx. de tasa de defectos 3,47e-18 |
| Alertas | máquina × turno | 23.403 sin alerta / 4.528 alerta / 149 crítica | mismas claves y conteos | 0 |
| Loss Tree | fila de producción | 28.080 filas | 28.080 filas | 0 incidencias de participación |

### Cruce con el incremento 003

El OEE mensual calculado desde las vistas reproduce el histórico ya verificado en 003:

| Mes | Disponibilidad | Rendimiento | Calidad | OEE |
|---|---:|---:|---:|---:|
| 2026-04 | 0,9915 | 0,9300 | 0,9916 | 0,9144 |
| 2026-05 | 0,9896 | 0,9186 | 0,9860 | 0,8963 |
| 2026-06 | 0,9877 | 0,9034 | 0,9775 | 0,8722 |
| 2026-07 | 0,9860 | 0,8878 | 0,9690 | 0,8483 |
| 2026-08 | 0,9841 | 0,8707 | 0,9604 | 0,8229 |
| 2026-09 | 0,9819 | 0,8559 | 0,9520 | 0,8000 |
| 2026-10 | 0,9813 | 0,8421 | 0,9452 | **0,7811** |

El valor de octubre coincide con el OEE 0,7811 registrado en
`specs/003-generador-historico/verification.md`.

## Casos borde (AC-502)

`validate_data.py` inserta datos de prueba en una transacción y hace `ROLLBACK`; no persiste nada.

| Caso | Entrada | Salida observada | Interpretación |
|---|---|---|---|
| División por cero | fila de producción con tiempos y conteos en 0 | `(None, None, None, None, None, None, None)` | A/P/Q/OEE, scrap y energía quedan `NULL`; no se inventa un 0 |
| Parada sin producción | parada de 20 min en turno sin fila de producción | `(0, 1, None, 20, None)` | runtime 0, 1 falla, MTBF `NULL`, downtime 20 min, MTTR `NULL` |
| Alerta sin producción | misma clave en `v_alerta_maquina_critica` | `('sin_alerta', 0, None, None, 20)` | OEE/MTBF `NULL` no activan condiciones; severidad `sin_alerta` |

No se observaron `NaN` ni `NULL` no intencionados. El `NULL` es la representación documentada de
una razón indefinida (D-014), no un valor perdido.

## Observaciones

- Las 149 alertas críticas del histórico provienen de combinaciones de MTBF y temperatura:
  3.861 turnos tienen MTBF < 20 h, 965 tienen temperatura alta y 149 cumplen ≥ 2 condiciones.
  En el histórico no hay OEE < 0,55 ni downtime > 120 min, por lo que esas dos condiciones no se
  activan por sí solas.
- El Loss Tree tiene 28.080 filas y `0` incidencias de participación: en cada fila las tres
  participaciones suman 1 (o son `NULL` si no hay pérdidas).
- `apply_all.sql` se re-ejecutó con `ON_ERROR_STOP=1`: `EXIT=0` y 20 `CREATE VIEW`; las vistas son
  idempotentes (P-020).
