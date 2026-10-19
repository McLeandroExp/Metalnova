# Plan — Incremento 002

## Organización de scripts

```text
sql/schema/       01_dimensiones.sql   02_hechos.sql   03_constraints.sql
sql/indexes/      01_indices.sql
sql/views/        01_vistas_base.sql
sql/validation/   01_integridad.sql
```

Los scripts se numeran y se ejecutan en orden. Cada uno es idempotente.

## Grano de los hechos

| Tabla | Grano |
|---|---|
| `fact_produccion` | orden + máquina + turno |
| `fact_parada` | episodio de parada |
| `fact_mantenimiento` | orden de trabajo |
| `fact_calidad` | inspección / lote |
| `fact_evento` | evento crudo (transición o lectura) |

## Claves y relaciones

- `dim_maquina.pk = id_maquina`; FK `id_linea`; `dim_linea.fk = id_planta`.
- `dim_producto.pk = id_producto`; FK `id_familia`.
- Hechos: FK a `dim_maquina`, `dim_producto`, `dim_turno`, `dim_causa`, `dim_tecnico`, `dim_tiempo`
  según corresponda al grano.
- `fact_evento` lleva `source_system`, `source_event_id` y `UNIQUE (source_system, source_event_id)`.
- `fact_evento_rechazado` lleva `motivo`, `payload`, `recibido_at`.

## Tipos y normalización de unidades (G9)

| Magnitud | Unidad canónica | Nota |
|---|---|---|
| Duración | minutos (entero) | conversiones documentadas |
| Tiempo de ciclo ideal | segundos | |
| Energía | kWh | |
| Temperatura | °C | |
| Conteos | unidades | enteros |

## Idempotencia

- Dimensiones: `INSERT ... ON CONFLICT (pk) DO UPDATE`.
- Hechos crudos: `ON CONFLICT (source_system, source_event_id) DO NOTHING`.
- DDL: `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`.
- Nada de `DROP` destructivo sin confirmación.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Joins que multiplican conteos | Validar con `sql/validation/01_integridad.sql` comparando totales antes/después del join |
| Crecimiento de índices | Índices solo sobre columnas de filtro/join reales |
