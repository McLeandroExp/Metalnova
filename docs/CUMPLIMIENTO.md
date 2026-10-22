# Matriz de cumplimiento — caso MetalNova

Requisito del caso → evidencia en el prototipo → estado. Todos los datos son
**sintéticos**.

| # | Requisito del caso | Evidencia | Estado |
|---|---|---|---|
| 1 | Fórmulas de OEE y componentes reconciliadas con datos base | `sql/views/03_kpi_oee.sql`; `validate_data.py` 49/49 con tolerancia 1e-9; `docs/DATA_DICTIONARY.md` §KPI | Cumplido |
| 2 | Modelo con múltiples hechos y dimensiones conformadas | 6 hechos, 10 dimensiones, 27 relaciones; `docs/ARCHITECTURE.md`; `specs/002/verification.md` | Cumplido |
| 3 | Prototipo con mínimo 4 vistas, 9 KPIs y navegación máquina → detalle | 4 páginas PBIR + detalle de máquina/causa + tooltip; 10 KPIs obligatorios; `tools/generate_pbir.py`; `powerbi/README.md` | Generado; **verificación visual pendiente** |
| 4 | Manejo explícito de calidad y temporalidad de eventos IoT | `event_quality.py`, `fact_evento_rechazado`, `v_calidad_senal_iot`, `validate_iot.py` 11/11, `04_iot.sql` 5/5 | Cumplido |
| 5 | Plan de mejora priorizado y cuantificado | `docs/PLAN_MEJORA.md` (5 acciones, impacto observado vs hipotético, supuestos y limitaciones) | Cumplido |
| 6 | ≥ 200.000 eventos en ≥ 90 días | 401.830 eventos; 180 días (2026-04-22 → 2026-10-18) | Cumplido |
| 7 | Latencia < 10 min para eventos de máquina | Latencia de pipeline 0,7–55 ms; frescura DirectQuery 0,35 s (D-019); medición en 007 | Cumplido |
| 8 | Modelo dimensional: Fact_Produccion, Fact_Parada, Fact_Mantenimiento, Fact_Calidad | Esquema `sql/schema/02_hechos.sql`; `specs/002` | Cumplido |
| 9 | Dimensiones conformadas de Máquina, Planta, Turno, Producto, Causa, Tiempo y Técnico | `dim_*` + `v_dim_maquina`/`v_dim_producto`; 002/006 | Cumplido |
| 10 | Jerarquías Planta → Línea → Máquina y Familia → Producto con drill-down sin duplicar medidas | Jerarquías TMDL `Ubicación` y `Producto`; medidas únicas en `measures.dax` | Cumplido |
| 11 | Transformaciones: tiempo planificado, runtime, ciclo ideal, good count, total count, downtime plan/no plan | `fact_produccion`, `v_kpi_produccion`, `v_loss_tree` | Cumplido |
| 12 | Normalizar unidades y distinguir microparadas de fallas | Regla G6: `<5 min` y sin CMMS = microparada; `v_kpi_parada`, `docs/DATA_DICTIONARY.md` | Cumplido |
| 13 | Tratamiento de duplicados, desordenados, faltantes y timestamps fuera de rango; fuente de verdad | `event_quality.py`, cuarentena, `payload.calidad`, `v_calidad_senal_iot`, D-022 | Cumplido |
| 14 | Vistas Executive, OEE & Loss Tree, Maintenance Reliability, Quality/Energy | Páginas 01–04 generadas | Generado; **verificación visual pendiente** |
| 15 | Filtros por planta, línea, máquina, producto y turno | 6 slicers sincronizados por página (`sync_*`) | Generado; **verificación visual pendiente** |
| 16 | Drill-through a historial de una máquina | `Detalle máquina` con filtro de página por `maquina_codigo` | Generado; **verificación visual pendiente** |
| 17 | Tooltips con última intervención, MTBF y MTTR | Página `Tooltip máquina` enlazada a la tabla de confiabilidad | Generado; **verificación visual pendiente** |
| 18 | Serie temporal con límites/umbrales | Línea de OEE con referencia 85 %; tendencias mensuales | Cumplido |
| 19 | Pareto de downtime | Página 02, barras por `dim_causa[categoria]` ordenadas | Cumplido |
| 20 | Matriz máquina-turno con formato condicional | Página 02, `pivotTable` con escala rojo-ámbar-verde sobre OEE | Generado; **verificación visual pendiente** |
| 21 | Navegación desde pérdida de OEE hacia causa | Página `Detalle causa` con filtro por `dim_causa[categoria]` desde el Pareto | Generado; **verificación visual pendiente** |
| 22 | Regla de excepción de máquina crítica accionable | `v_alerta_maquina_critica`; regla multicriterio con OEE, MTBF, temperatura y downtime; `docs/DATA_DICTIONARY.md` §8 | Cumplido |
| 23 | Loss Tree por activo/turno/producto | `v_loss_tree`; página 02 (matriz máquina-turno, pérdida por producto y por planta) | Cumplido |
| 24 | Confiabilidad: máquinas con alto downtime y fallas cortas frecuentes | `v_kpi_confiabilidad_apoyo_maquina_dia`; medidas de fallas cortas/100 h y microparadas/100 h; página 03 | Cumplido |
| 25 | Calidad relacionada con producto, turno y condiciones, sin afirmar causalidad | Scrap por turno/producto y dispersión energía-scrap; `PLAN_MEJORA.md` lo declara descriptivo | Cumplido |
| 26 | Ranking de intervenciones por impacto económico y criticidad | `docs/PLAN_MEJORA.md` §5 | Cumplido |
| 27 | Demostración sin internet y con datos sintéticos | Docker local + Power BI Desktop; aviso en cada página | Cumplido |

## Pendiente para cerrar el proyecto

1. Abrir `powerbi/final/MetalNova.pbip`, refrescar y validar visualmente las 4 páginas, los
   filtros, el drill-through y el tooltip (T-614).
2. Registrar las capturas y los valores observados en `specs/006-powerbi/verification.md`.
3. Confirmar que las 4 páginas abren por debajo de 60 s; si no, reevaluar D-019.
4. Cerrar T-615 y T-710 con el commit correspondiente.
