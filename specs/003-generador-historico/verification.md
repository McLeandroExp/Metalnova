# Verificación — Incremento 003

| AC | Comando | Salida esperada | Salida observada | Fecha | Veredicto |
|---|---|---|---|---|---|
| AC-301 | `SELECT count(*)` por tabla | total ≥ 200 000 | — | — | pendiente |
| AC-302 | min/max de fechas | intervalo = 180 días | — | — | pendiente |
| AC-303 | `WHERE fin < inicio` | 0 filas | — | — | pendiente |
| AC-304 | `WHERE cantidad < 0` | 0 filas | — | — | pendiente |
| AC-305 | regenerar con misma semilla | recuentos idénticos | — | — | pendiente |
| AC-306 | medir carga | duración y tamaño documentados | — | — | pendiente |
| AC-307 | consulta de huérfanos | 0 filas | — | — | pendiente |

## Recuento por tabla

| Tabla/archivo | Filas | Tamaño | Tiempo de carga |
|---|---|---|---|
| — | — | — | — |
