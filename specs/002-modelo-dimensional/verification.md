# Verificación — Incremento 002

Fecha de las pruebas: 2026-10-19.
Entorno: PostgreSQL 16.4 en Docker, base `metalinova`.

| AC | Comando | Salida esperada | Salida observada | Veredicto |
|---|---|---|---|---|
| AC-201 | `psql -f /sql/apply_all.sql` en base limpia | sin errores | 10 `CREATE TABLE`, 6 `CREATE TABLE`, 18 `CREATE INDEX`, 4 `CREATE VIEW` | **superada** |
| AC-202 | segunda ejecución completa | sin objetos nuevos ni filas perdidas | solo `NOTICE ... already exists, skipping`; recuentos idénticos | **superada** |
| AC-203 | `psql -f /sql/validation/01_integridad.sql` | 0 incidencias | 21 chequeos, todos con `incidencias = 0` y `estado = OK` | **superada** |
| AC-204 | recuento de constraints en `pg_constraint` | FK y CHECK presentes | 16 PK · 24 FK · 16 UNIQUE · 41 CHECK | **superada** |
| AC-205 | revisión de `docs/DATA_DICTIONARY.md` | cubre todas las tablas | 10 dimensiones, 6 hechos, columnas y grano documentados | **superada** |
| AC-206 | join hecho→jerarquía y comparar recuentos | sin multiplicación | vistas base con 0 diferencias vs hechos; 52 máquinas = 18+18+16 | **superada** |

## Recuento del catálogo (estable tras dos ejecuciones)

| Tabla | Filas |
|---|---|
| `dim_planta` | 3 |
| `dim_linea` | 6 |
| `dim_maquina` | 52 |
| `dim_familia` | 3 |
| `dim_producto` | 12 |
| `dim_turno` | 3 |
| `dim_causa` | 12 |
| `dim_tecnico` | 12 |
| `dim_tiempo` | 1095 (2025-01-01 → 2027-12-31) |

## Evidencia adicional

- FK compuesta `fact_produccion_orden_producto_fk` presente: garantiza que el producto del hecho
  coincide con el de la orden.
- Jerarquía Planta→Línea→Máquina: Planta Norte 18, Planta Centro 18, Planta Sur 16 (total 52).
- Jerarquía Familia→Producto: 4 productos por familia (Frenos, Suspensión, Transmisión).
- Hechos vacíos: la carga de datos corresponde al incremento 003.

## Observaciones

- Los `NOTICE` de PostgreSQL se emiten por *stderr*; PowerShell puede mostrar `NativeCommandError`
  aunque la ejecución sea correcta. Verificar con la consulta de validación.
