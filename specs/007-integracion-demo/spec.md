# Incremento 007 — Integración, demo y plan de mejora

Estado: propuesto · Depende de: 006 · Habilita: —

## Contexto

Cierra el proyecto: prueba integral end-to-end, backup/restore, runbook de demostración y plan de
mejora cuantificado. Verifica las condiciones de finalización de la Constitución §13.

## Requisitos funcionales

| ID | Requisito |
|---|---|
| FR-701 | Probar arranque desde cero y tras reinicio sin pérdida de datos. |
| FR-702 | Ejecutar ingesta continua y comprobar que un evento nuevo llega al informe. |
| FR-703 | Medir y documentar la latencia real end-to-end. |
| FR-704 | Validar backup (`pg_dump`) y restauración (`pg_restore`). |
| FR-705 | `docs/DEMO_RUNBOOK.md` con orden de arranque, escenarios y recuperación ante errores. |
| FR-706 | `docs/TEST_PLAN.md` con casos, comandos, resultados y fechas. |
| FR-707 | Plan de mejora priorizado y cuantificado: problema, planta/máquina/turno, evidencia, acción, prioridad, responsable, KPI de seguimiento, impacto, método de cálculo, coste/supuesto, confianza y limitaciones. |
| FR-708 | Distinguir impacto observado en datos sintéticos, impacto hipotético y cifras del caso no recalculadas. |
| FR-709 | `README.md` final usable por terceros. |
| FR-710 | Matriz de cumplimiento requisito del caso → evidencia. |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-701 | El proceso completo se repite siguiendo pasos documentados. |
| AC-702 | El flujo normal no depende de internet. |
| AC-703 | Existe evidencia de latencia (tabla de mediciones). |
| AC-704 | Existen instrucciones de recuperación de la base y se probaron. |
| AC-705 | La presentación explica claramente que los datos son sintéticos. |
| AC-706 | El plan de mejora incluye 3–5 acciones priorizadas con impacto y supuestos. |
| AC-707 | Todas las condiciones de finalización de la Constitución §13 se cumplen o se declaran. |

## Dependencias

006 (informe construido).
