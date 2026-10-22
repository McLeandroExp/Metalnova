# SQL — Esquema, índices, vistas y validación

Scripts versionados e idempotentes. Se ejecutan **explícitamente**; no dependen del
`docker-entrypoint-initdb.d` (que solo corre con un volumen vacío).

## Aplicar todo

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/apply_all.sql
```

El directorio `sql/` está montado en el contenedor `db` como `/sql` (solo lectura).

## Validar integridad

```powershell
# Modelo (siempre)
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/01_integridad.sql

# Histórico cargado (incremento 003)
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/02_historico.sql

# Bandas del escenario calibrado (incremento 006)
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/03_calibracion.sql
```

Todas las filas deben mostrar `estado = OK` e `incidencias = 0`.

## Orden de los scripts

| Orden | Archivo | Contenido |
|---|---|---|
| 1 | `schema/01_dimensiones.sql` | 10 dimensiones con PK, FK y CHECK |
| 2 | `schema/02_hechos.sql` | 4 hechos + evento crudo + cuarentena |
| 3 | `schema/03_comentarios.sql` | Grano y reglas documentados en el esquema |
| 4 | `schema/04_catalogo_referencia.sql` | Catálogo sintético base + perfiles de calibración |
| 5 | `indexes/01_indices.sql` | Índices de filtro y join (incluye el índice parcial de lecturas IoT) |
| 6 | `views/01_vistas_base.sql` | Vistas `v_*` para Power BI |
| 7 | `views/02..08_*.sql` | Vistas KPI y alerta de máquina crítica |
| 8 | `views/09_dimensiones_bi.sql` | Dimensiones conformadas `v_dim_maquina` y `v_dim_producto` |

La columna `dim_maquina.perfil_rendimiento` se añade con `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
para bases existentes. Solo la usa el escenario `calibracion`; el catálogo asigna siete outliers
persistentes y el resto queda en `estandar`.

## Reglas

- `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` / `CREATE OR REPLACE VIEW`.
- Los catálogos usan `INSERT ... ON CONFLICT DO NOTHING`.
- No hay `DROP` ni operaciones destructivas.
- Las constraints se declaran inline para que la creación sea atómica e idempotente.
