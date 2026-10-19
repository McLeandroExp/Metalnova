# Verificación — Incremento 002

| AC | Comando | Salida esperada | Salida observada | Fecha | Veredicto |
|---|---|---|---|---|---|
| AC-201 | ejecutar `sql/schema/*.sql` en base limpia | sin errores | — | — | pendiente |
| AC-202 | re-ejecutar todos los scripts | 0 objetos nuevos, 0 filas perdidas | — | — | pendiente |
| AC-203 | `sql/validation/01_integridad.sql` | 0 filas huérfanas | — | — | pendiente |
| AC-204 | consulta de FK inválidas | 0 filas | — | — | pendiente |
| AC-205 | revisión de `docs/DATA_DICTIONARY.md` | cubre todas las tablas | — | — | pendiente |
| AC-206 | join hecho→jerarquía y comparar recuento | recuento idéntico | — | — | pendiente |

## Notas

- Guardar el `\d+` de cada tabla como evidencia opcional.
