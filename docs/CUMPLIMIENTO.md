# Matriz de cumplimiento — caso MetalNova

Requisito del caso → evidencia en el prototipo → estado. Todos los datos son
**sintéticos**.

| # | Requisito del caso | Evidencia | Estado |
|---|---|---|---|
| 1 | Fórmulas de OEE y componentes reconciliadas con datos base | `sql/views/03_kpi_oee.sql`; `sql/validation/07_kpi_formulas.sql` 12/12; `validate_data.py` 49/49 con tolerancia 1e-9; `docs/DATA_DICTIONARY.md` §KPI | Cumplido |
| 2 | Modelo con múltiples hechos y dimensiones conformadas | 6 hechos, 10 dimensiones, 27 relaciones; `docs/ARCHITECTURE.md`; `specs/002/verification.md` | Cumplido |
| 3 | Prototipo con mínimo 4 vistas, 9 KPIs y navegación máquina → detalle | 4 páginas PBIR + detalle de máquina/causa + tooltip; 24 tarjetas; `tools/generate_pbir.py`; verificación visual 2026-10-23; `docs/verification/bloque4-kpi-obligatorios.md` (10 KPI, FPY literal) | Cumplido |
| 4 | Manejo explícito de calidad y temporalidad de eventos IoT | `event_quality.py`, `fact_evento_rechazado`, `v_calidad_senal_iot`, `validate_iot.py` 11/11, `04_iot.sql` 5/5 | Cumplido |
| 5 | Plan de mejora priorizado y cuantificado | `docs/PLAN_MEJORA.md` (5 acciones, impacto observado vs hipotético, supuestos y limitaciones) | Cumplido |
| 6 | ≥ 200.000 eventos en ≥ 90 días | 401.830 eventos; 180 días (2026-04-22 → 2026-10-18) | Cumplido |
| 7 | Latencia < 10 min para eventos de máquina | Latencia de pipeline 0,7–55 ms; frescura DirectQuery 0,35 s (D-019); medición en 007 | Cumplido |
| 8 | Modelo dimensional: Fact_Produccion, Fact_Parada, Fact_Mantenimiento, Fact_Calidad | Esquema `sql/schema/02_hechos.sql`; `specs/002` | Cumplido |
| 9 | Dimensiones conformadas de Máquina, Planta, Turno, Producto, Causa, Tiempo y Técnico | `dim_*` + `v_dim_maquina`/`v_dim_producto`; 002/006 | Cumplido |
| 10 | Jerarquías Planta → Línea → Máquina y Familia → Producto con drill-down sin duplicar medidas | Jerarquías TMDL `Ubicación` y `Producto`; medidas únicas en `measures.dax` | Cumplido |
| 11 | Transformaciones: tiempo planificado, runtime, ciclo ideal, good count, total count, downtime plan/no plan | `fact_produccion`, `v_kpi_produccion`, `v_loss_tree` | Cumplido |
| 12 | Normalizar unidades y distinguir microparadas de fallas | Regla G6: `<5 min` y sin CMMS = microparada; `v_kpi_parada`, `docs/DATA_DICTIONARY.md` | Cumplido |
| 13 | Tratamiento de duplicados, desordenados, faltantes, timestamps fuera de rango y solapes; fuente de verdad | `event_quality.py`, cuarentena, `payload.calidad`, `v_calidad_senal_iot`, `v_parada_consolidada` (D-023), `sql/validation/05_parada_consolidada.sql` y `06_..._prueba.sql` | Cumplido |
| 14 | Vistas Executive, OEE & Loss Tree, Maintenance Reliability, Quality/Energy | Páginas 01–04 verificadas en Desktop el 2026-10-23 | Cumplido |
| 15 | Filtros por planta, línea, máquina, producto y turno | 6 slicers sincronizados por página (`sync_*`); sincronización probada por el usuario | Cumplido |
| 16 | Drill-through a historial de una máquina | `Detalle máquina` con `pageBinding` Drillthrough y filtro por `maquina_codigo`; probado el 2026-10-23 | Cumplido |
| 17 | Tooltips con última intervención, MTBF y MTTR | Página `Tooltip máquina` con `pageBinding` Tooltip; hover probado el 2026-10-23 | Cumplido |
| 18 | Serie temporal con límites/umbrales | Línea de OEE con referencia 85 %; tendencias mensuales | Cumplido |
| 19 | Pareto de downtime | Página 02, barras por `dim_causa[categoria]` ordenadas | Cumplido |
| 20 | Matriz máquina-turno con formato condicional | Página 02, `pivotTable` con escala rojo-ámbar-verde sobre OEE; verificada el 2026-10-23 | Cumplido |
| 21 | Navegación desde pérdida de OEE hacia causa | Página `Detalle causa` con `pageBinding` Drillthrough por `dim_causa[categoria]` desde el Pareto; probada el 2026-10-23 | Cumplido |
| 22 | Regla de excepción de máquina crítica accionable | `v_alerta_maquina_critica`; regla multicriterio con OEE, MTBF, temperatura y downtime; `docs/DATA_DICTIONARY.md` §8 | Cumplido |
| 23 | Loss Tree por activo/turno/producto | `v_loss_tree`; página 02 (matriz máquina-turno, pérdida por producto y por planta); `docs/verification/bloque5-analisis-descubrimiento.md` | Cumplido |
| 24 | Confiabilidad: máquinas con alto downtime y fallas cortas frecuentes | `v_kpi_confiabilidad_apoyo_maquina_dia`; medidas de fallas cortas/100 h y microparadas/100 h; página 03; `docs/verification/bloque5-analisis-descubrimiento.md` | Cumplido |
| 25 | Calidad relacionada con producto, turno y condiciones, sin afirmar causalidad | Scrap por turno/producto, dispersión energía-scrap; cambios de producto y temperatura en `docs/verification/bloque5-analisis-descubrimiento.md`; `PLAN_MEJORA.md` lo declara descriptivo | Cumplido |
| 26 | Ranking de intervenciones por impacto económico y criticidad | `docs/PLAN_MEJORA.md` §5; validación en `docs/verification/bloque5-analisis-descubrimiento.md` | Cumplido |
| 27 | Demostración sin internet y con datos sintéticos | Docker local + Power BI Desktop; aviso en cada página | Cumplido |

Evidencia visual: capturas de las 8 páginas en [`docs/capturas/`](capturas/README.md).

## Verificación detallada

La verificación reproducible de los Bloques 1 a 6 está en
[`docs/verification/`](verification/README.md). Incluye la respuesta formal a la
pregunta principal de Business Understanding y la matriz final de aceptación
[`bloque6-producto-criterios.md`](verification/bloque6-producto-criterios.md).

## Cierre

El prototipo quedó verificado visualmente el 2026-10-23. Evidencia en
`specs/006-powerbi/verification.md` y `specs/007-integracion-demo/verification.md`:

1. Las 4 páginas, los filtros, el drill-through (máquina y causa) y el tooltip se
   probaron en Power BI Desktop; captura de las 8 páginas con 0 fallos.
2. Los valores observados y las correcciones (OEE de alertas y fila de totales)
   están registrados en la verificación del 006.
3. La referencia de apertura es la mediana de 35,46 s de D-019 (umbral ≤ 60 s); no
   se observó regresión al abrir el informe final.
4. T-615 y T-710 cerrados con el commit `c32cbd6`.

## Análisis estadístico complementario (008)

El incremento 008 **no corresponde a un requisito explícito del caso**: se añade como evidencia
analítica sobre los mismos datos sintéticos. No cambia KPI, modelo ni informe de Power BI.
Aporta descriptivos, atípicos, correlación, comparaciones y tendencia, con validación SQL vs
Python (54/54) y controles estructurales (22/22). Informe: `docs/ANALISIS_DATOS.md`; evidencia:
`specs/008-analisis-datos/verification.md`.
