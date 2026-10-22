# Tareas — Incremento 006

| ID | Tarea | Requisito | Estado |
|---|---|---|---|
| T-601 | Conectar Power BI Desktop a PostgreSQL local | FR-601 | hecha |
| T-602 | Página de prueba DirectQuery y mediciones | FR-601 | hecha |
| T-603 | Decidir DirectQuery vs Import y documentar | FR-601, AC-606 | hecha |
| T-604 | Generar modelo semántico TMDL con jerarquías | FR-614 | hecha |
| T-605 | Medidas DAX de los KPI | FR-614, AC-602 | hecha |
| T-606 | Página Executive Plant Performance | FR-602 | en curso |
| T-607 | Página OEE & Loss Tree (Pareto + matriz máquina-turno) | FR-603,610,611 | pendiente |
| T-608 | Página Maintenance Reliability | FR-604 | pendiente |
| T-609 | Página Quality & Energy | FR-605 | pendiente |
| T-610 | Filtros consistentes y drill-through | FR-606,607 | pendiente |
| T-611 | Tooltips (última intervención, MTBF, MTTR) | FR-608 | pendiente |
| T-612 | Serie temporal con umbrales | FR-609 | pendiente |
| T-613 | Navegación pérdida OEE→causa y alerta crítica | FR-612,613 | pendiente |
| T-614 | Verificar 4 páginas y 9 KPIs; guardar `.pbix`/`.pbip` | AC-601,605,607 | pendiente |
| T-616 | Optimizar `v_alerta_maquina_critica` (índice o materialización) | FR-601, AC-606 | hecha |
| T-617 | Calibrar el histórico: factores por planta, perfiles y outliers | FR-615, AC-608 | hecha |
| T-615 | Commit `feat: informe power bi` | — | pendiente |

Notas de estado:

- T-604/T-605: el TMDL se generó y validó (12 tablas, 20 relaciones, 45 medidas). El usuario
  confirmó el 2026-10-22 que las 10 tarjetas de validación muestran valor, incluida
  `OEE último mes` (65,51 % por DAX). El modelo y las medidas quedan cerrados.
- T-616: `CROSS JOIN LATERAL` + índice parcial `ix_fact_evento_lectura_maquina_time`; consulta
  filtrada 464/335/369 ms y `validate_data.py` 49/49. Evidencia en `verification.md`.
- T-606…T-609: la guía paso a paso está en `powerbi/final/BUILD_GUIDE.md`; T-606 está en curso.
- T-617: corrida `hist-h3a58b2b659`, OEE 78,02 → 66,00 %, dispersión 8,5 → 7,3 pp; validación
  49/49 y reproducibilidad SHA-256 idéntica. Evidencia en `verification.md`.
