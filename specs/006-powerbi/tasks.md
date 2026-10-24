# Tareas — Incremento 006

| ID | Tarea | Requisito | Estado |
|---|---|---|---|
| T-601 | Conectar Power BI Desktop a PostgreSQL local | FR-601 | hecha |
| T-602 | Página de prueba DirectQuery y mediciones | FR-601 | hecha |
| T-603 | Decidir DirectQuery vs Import y documentar | FR-601, AC-606 | hecha |
| T-604 | Generar modelo semántico TMDL con jerarquías | FR-614 | hecha |
| T-605 | Medidas DAX de los KPI | FR-614, AC-602 | hecha |
| T-606 | Página Executive Plant Performance | FR-602 | hecha |
| T-607 | Página OEE & Loss Tree (Pareto + matriz máquina-turno) | FR-603,610,611 | hecha |
| T-608 | Página Maintenance Reliability | FR-604 | hecha |
| T-609 | Página Quality & Energy | FR-605 | hecha |
| T-610 | Filtros consistentes y drill-through | FR-606,607 | hecha |
| T-611 | Tooltips (última intervención, MTBF, MTTR) | FR-608 | hecha |
| T-612 | Serie temporal con umbrales | FR-609 | hecha |
| T-613 | Navegación pérdida OEE→causa y alerta crítica | FR-612,613 | hecha |
| T-614 | Verificar 4 páginas y 9 KPIs; guardar `.pbix`/`.pbip` | AC-601,605,607 | hecha |
| T-618 | Calidad IoT: cuarentena, tardío/reordenado y cobertura | G5 | hecha |
| T-616 | Optimizar `v_alerta_maquina_critica` (índice o materialización) | FR-601, AC-606 | hecha |
| T-617 | Calibrar el histórico: factores por planta, perfiles y outliers | FR-615, AC-608 | hecha |
| T-615 | Commit `feat: informe power bi` | — | hecha (`ce39ae9`) |

Notas de estado:

- T-604/T-605: el TMDL se generó y validó (12 tablas, 20 relaciones, 45 medidas). El usuario
  confirmó el 2026-10-22 que las 10 tarjetas de validación muestran valor, incluida
  `OEE último mes` (65,51 % por DAX). El modelo y las medidas quedan cerrados.
- T-616: `CROSS JOIN LATERAL` + índice parcial `ix_fact_evento_lectura_maquina_time`; consulta
  filtrada 464/335/369 ms y `validate_data.py` 49/49. Evidencia en `verification.md`.
- T-606…T-613: las páginas se generaron con `tools/generate_pbir.py` (7 páginas, 94 visuales) y
  `tools/validate_report.py` no encontró referencias rotas. El usuario verificó en Desktop las 4
  páginas, los slicers sincronizados, el drill-through (máquina y causa) y el tooltip el
  2026-10-23. El drill-through requirió `pageBinding` tipo `Drillthrough`, corregido ese día.
- T-614: cierre visual confirmado por el usuario; la tabla de alertas quedó sin fila de totales
  (`objects.total[0].properties.totals = false`) y `OEE Alerta` muestra valores.
- T-618: `validate_iot.py` 11/11 y `04_iot.sql` 5/5; `--scenario invalid M-001` deja 2 rechazos y
  un evento tardío/reordenado. Evidencia en `verification.md`.
- T-617: corrida `hist-h3a58b2b659`, OEE 78,02 → 66,00 %, dispersión 8,5 → 7,3 pp; validación
  49/49 y reproducibilidad SHA-256 idéntica. Evidencia en `verification.md`.
