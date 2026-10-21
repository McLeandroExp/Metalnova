# Índice de incrementos SDD

Fuente de verdad normativa: [`CONSTITUTION.md`](./CONSTITUTION.md).

Cada incremento contiene `spec.md`, `plan.md`, `tasks.md` y `verification.md`.
Estados: `propuesto` · `en curso` · `hecho` · `bloqueado`.

| Incremento | Título | Depende de | Estado |
|---|---|---|---|
| 001 | Infraestructura PostgreSQL en Docker | — | hecho |
| 002 | Modelo dimensional SQL | 001 | hecho |
| 003 | Generador histórico (180 días) | 002 | hecho |
| 004 | Ingesta continua simulada | 003 | propuesto (diferido) |
| 005 | Vistas KPI y validación | 003 | hecho |
| 006 | Informe Power BI (4 páginas) | 004, 005 | propuesto |
| 007 | Integración, demo y plan de mejora | 006 | propuesto |

## Grafo de dependencias

```text
001 ──▶ 002 ──┬──▶ 003 ──┬──▶ 004 ──┐
              │          └──▶ 005 ──┴──▶ 006 ──▶ 007
```

## Regla de avance (gate)

No se abre un incremento si un prerequisito no está en estado `hecho` con evidencia
registrada en su `verification.md`. Si una prueba esencial falla, el incremento pasa a
`bloqueado` y se documenta el bloqueo antes de continuar.

## Registro de estado

Actualizar esta tabla al cerrar cada incremento, junto con el commit correspondiente.
