# Plan — Incremento 002

## Organización de scripts

```text
sql/schema/       01_dimensiones.sql   02_hechos.sql   03_comentarios.sql   04_catalogo_referencia.sql
sql/indexes/      01_indices.sql
sql/views/        01_vistas_base.sql
sql/validation/   01_integridad.sql
sql/apply_all.sql
```

Los scripts se numeran y se ejecutan en orden mediante `sql/apply_all.sql`. Cada uno es idempotente.

**Decisión de implementación:** las constraints (PK, FK, UNIQUE, CHECK) se declaran **inline** en
`CREATE TABLE IF NOT EXISTS` para que la creación sea atómica. `03_constraints.sql` del plan
original pasa a ser `03_comentarios.sql` (documentación del grano en el propio esquema). El
directorio `sql/` se monta en el contenedor `db` como `/sql` (solo lectura).

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

- Dimensiones: `INSERT ... ON CONFLICT DO NOTHING`.
- Hechos crudos: `ON CONFLICT (source_system, source_event_id) DO NOTHING`.
- DDL: `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `CREATE OR REPLACE VIEW`.
- Nada de `DROP` destructivo sin confirmación.

## Catálogo de referencia

El incremento 002 siembra el catálogo **estático**: 3 plantas, 6 líneas, 52 máquinas, 3 familias,
12 productos, 3 turnos, 12 causas, 12 técnicos y la dimensión tiempo (2025-01-01 a 2027-12-31).
Así el esquema es verificable de inmediato en pgAdmin. El incremento 003 genera los hechos
(órdenes, producción, paradas, mantenimientos, calidad) y amplía el catálogo si hiciera falta.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Joins que multiplican conteos | Validar con `sql/validation/01_integridad.sql` comparando totales antes/después del join |
| Crecimiento de índices | Índices solo sobre columnas de filtro/join reales |
