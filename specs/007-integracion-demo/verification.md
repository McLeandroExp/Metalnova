# Verificación — Incremento 007

Estado: **en curso** · Última actualización: 2026-10-22 · Entorno: PostgreSQL 16.4-alpine en
Docker, Power BI Desktop 2.159.883.0.

| AC | Comando/observación | Salida esperada | Salida observada | Fecha | Veredicto |
|---|---|---|---|---|---|
| AC-701 | `docker compose down` → `up -d` y repetir el runbook | datos intactos y proceso repetible | `db` healthy; 401.832 eventos, 28.080 producciones, 76.042 paradas; el escenario `stop M-001` volvió a insertar 20 min y 1 falla | 2026-10-22 | superada |
| AC-702 | revisar dependencias externas | sin internet | Docker local + Power BI Desktop; sin nube ni API | 2026-10-22 | superada (declarada) |
| AC-703 | medir latencia `sim-*` | < 10 min | 0,7–55 ms de pipeline; frescura DirectQuery 0,35 s (D-019) | 2026-10-22 | superada |
| AC-704 | `pg_dump -Fc` + `pg_restore` en base temporal | recuentos coinciden | 401.832 / 28.080 / 76.042 / 28.080 idénticos; base temporal eliminada | 2026-10-22 | superada |
| AC-705 | revisar demo y páginas | datos sintéticos declarados | aviso en cada página y en README/runbook | 2026-10-22 | superada |
| AC-706 | revisar `docs/PLAN_MEJORA.md` | 3–5 acciones con impacto y supuestos | 5 acciones con impacto observado/hipotético, supuesto, confianza y limitación | 2026-10-22 | superada |
| AC-707 | checklist Constitución §13 | todo cumplido o declarado | ver tabla siguiente; queda la verificación visual del informe | 2026-10-22 | en curso |

## Condiciones de finalización (Constitución §13)

| # | Condición | Estado | Evidencia |
|---|---|---|---|
| 1 | Infraestructura arranca y conserva datos | Cumplida | `down`/`up -d`; volumen intacto |
| 2 | 180 días y volumen mínimo | Cumplida | 401.830 eventos; 2026-04-22 → 2026-10-18 |
| 3 | Ingesta simulada sin duplicados | Cumplida | 004/006; `ON CONFLICT`; 0 duplicados |
| 4 | KPI validados de forma independiente | Cumplida | `validate_data.py` 49/49 |
| 5 | 4 páginas, 9 KPIs y navegación máquina→detalle | Generada, pendiente de verificación visual | `generate_pbir.py`; `validate_report.py` 0 errores |
| 6 | DirectQuery/Import elegido con mediciones y latencia | Cumplida | D-019; 35,46 s apertura, 0,35 s frescura |
| 7 | Demo repetible y plan de mejora con evidencia | Cumplida (runbook + plan) | `DEMO_RUNBOOK.md`, `PLAN_MEJORA.md` |
| 8 | README y documentación para terceros | Cumplida | README, ARCHITECTURE, DATA_DICTIONARY, TEST_PLAN |

## Backup y restauración

```powershell
docker compose exec -T db pg_dump -U metalinova -d metalinova -Fc -f /tmp/restore.dump
docker cp metalnova_db:/tmp/restore.dump backups/metalnova_restore_test_20261022.dump
docker compose exec -T db createdb -U metalinova metalinova_restore_test
docker compose exec -T db pg_restore -U metalinova -d metalinova_restore_test `
  --no-owner --no-privileges /tmp/restore.dump
```

Recuentos observados en la base restaurada: eventos 401.832, producciones 28.080, paradas
76.042 y calidad 28.080. La base `metalinova_restore_test` se eliminó después de la prueba.

## Latencia observada

| Métrica | Valor |
|---|---|
| Eventos `sim-*` | 51 |
| Latencia mínima | 0,7 ms |
| Latencia media | 28 ms |
| Latencia máxima | 55 ms |
| Desfase máximo `ingested_at − event_time` | 10 min 0,7 s (evento de prueba tardío) |
| Frescura DirectQuery | 0,35 s (D-019) |

La latencia de pipeline se mide solo con `run_id LIKE 'sim-%'`; los eventos históricos tienen
`generated_at` de la generación y `ingested_at` de la carga, por lo que su diferencia no es
latencia de ingesta.

## Matriz de cumplimiento

La matriz completa está en `docs/CUMPLIMIENTO.md`. Resumen: 20 requisitos con evidencia
verificada y 7 generados pendientes de verificación visual (páginas, filtros, drill-through,
tooltip y matriz con formato condicional).

## Pendientes

1. Abrir `powerbi/final/MetalNova.pbip`, refrescar y validar visualmente las 4 páginas.
2. Medir de nuevo la apertura del informe final; si supera 60 s, reevaluar D-019.
3. Registrar capturas y valores; cerrar T-614, T-615 y T-710.
