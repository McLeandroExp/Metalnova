# Tareas — Incremento 007

| ID | Tarea | Requisito | Estado |
|---|---|---|---|
| T-701 | Prueba de arranque en frío y tras reinicio | FR-701 | hecha |
| T-702 | Ingesta continua + escenario reproducible | FR-702 | hecha |
| T-703 | Medición de latencia end-to-end | FR-703 | hecha |
| T-704 | Backup y restauración probados | FR-704 | hecha |
| T-705 | `docs/DEMO_RUNBOOK.md` | FR-705 | hecha |
| T-706 | `docs/TEST_PLAN.md` completo | FR-706 | hecha |
| T-707 | `docs/PLAN_MEJORA.md` cuantificado | FR-707,708 | hecha |
| T-708 | `README.md` final | FR-709 | hecha |
| T-709 | Matriz de cumplimiento del caso | FR-710 | hecha |
| T-710 | Commit `docs: integración, demo y plan de mejora` | — | pendiente |

Notas:

- T-701: `docker compose down` / `up -d` conservó 401.832 eventos, 28.080 producciones y 76.042
  paradas; `db` healthy. Sin `down -v`.
- T-702: `--scenario stop M-001 --once` insertó 3 paradas (la del escenario y 2 del ciclo) y 6
  eventos; M-001 turno B quedó con 20 min de downtime y 1 falla.
- T-703: latencia de pipeline de los eventos `sim-*` 0,7–55 ms; frescura DirectQuery 0,35 s
  (D-019). No se midió de nuevo la apertura del informe final (requiere GUI).
- T-704: `pg_dump -Fc` actual (9,2 MB) y `pg_restore` en `metalinova_restore_test`; recuentos
  idénticos (401.832 / 28.080 / 76.042 / 28.080). Base temporal eliminada.
- T-705…T-709: runbook, test plan, plan de mejora, README y matriz de cumplimiento actualizados.
