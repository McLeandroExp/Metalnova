-- ============================================================================
-- 07_kpi_formulas.sql — Validación de las fórmulas de los 10 KPI obligatorios.
--
-- Comprueba que las columnas calculadas de las vistas coinciden con su fórmula
-- declarada. No recalcula desde los hechos (eso lo hace validate_data.py):
-- verifica la coherencia interna del contrato analítico.
--
-- Resultado esperado: todas las filas de "checks" con incidencias = 0.
-- ============================================================================

WITH checks AS (
    -- --- OEE y componentes (vista agregada planta-día) -------------------
    SELECT 'OEE = Disponibilidad × Rendimiento × Calidad' AS chequeo,
           count(*)::bigint AS valor,
           count(*) FILTER (
               WHERE abs(oee - round(disponibilidad * rendimiento * calidad, 6))
                     > 1e-9
           )::bigint AS incidencias
    FROM v_kpi_oee_planta_dia

    UNION ALL
    SELECT 'Disponibilidad = runtime / tiempo planificado',
           count(*)::bigint,
           count(*) FILTER (
               WHERE abs(
                   disponibilidad
                   - tiempo_operativo_min::numeric
                     / NULLIF(tiempo_planificado_min, 0)
               ) > 1e-9
           )::bigint
    FROM v_kpi_oee_planta_dia

    UNION ALL
    SELECT 'Rendimiento = minutos ideales / runtime',
           count(*)::bigint,
           count(*) FILTER (
               WHERE abs(
                   rendimiento
                   - minutos_ideales / NULLIF(tiempo_operativo_min, 0)
               ) > 1e-9
           )::bigint
    FROM v_kpi_oee_planta_dia

    UNION ALL
    SELECT 'Calidad = good count / total count',
           count(*)::bigint,
           count(*) FILTER (
               WHERE abs(
                   calidad
                   - good_count::numeric / NULLIF(total_count, 0)
               ) > 1e-9
           )::bigint
    FROM v_kpi_oee_planta_dia

    UNION ALL
    SELECT 'Scrap Rate = scrap count / total count',
           count(*)::bigint,
           count(*) FILTER (
               WHERE abs(
                   scrap_rate
                   - scrap_count::numeric / NULLIF(total_count, 0)
               ) > 1e-9
           )::bigint
    FROM v_kpi_oee_planta_dia

    UNION ALL
    SELECT 'Downtime no planificado = downtime / tiempo planificado',
           count(*)::bigint,
           count(*) FILTER (
               WHERE abs(
                   downtime_no_planificado_pct
                   - downtime_no_planificado_min::numeric
                     / NULLIF(tiempo_planificado_min, 0)
               ) > 1e-9
           )::bigint
    FROM v_kpi_oee_planta_dia

    UNION ALL
    SELECT 'Energía por Unidad Buena = kWh / good count',
           count(*)::bigint,
           count(*) FILTER (
               WHERE abs(
                   energia_por_unidad_buena
                   - energia_kwh / NULLIF(good_count, 0)
               ) > 1e-9
           )::bigint
    FROM v_kpi_oee_planta_dia

    -- --- OEE a nivel de fila de producción -------------------------------
    UNION ALL
    SELECT 'OEE por fila = A × P × Q (v_kpi_produccion)',
           count(*)::bigint,
           count(*) FILTER (
               WHERE abs(oee - disponibilidad * rendimiento * calidad) > 1e-9
           )::bigint
    FROM v_kpi_produccion

    -- --- MTBF, MTTR y downtime de mantenimiento --------------------------
    UNION ALL
    SELECT 'MTBF = horas operativas / fallas',
           count(*)::bigint,
           count(*) FILTER (
               WHERE mtbf_h IS NOT NULL
                 AND abs(
                     mtbf_h
                     - (tiempo_operativo_min / 60.0) / NULLIF(fallas, 0)
                 ) > 1e-9
           )::bigint
    FROM v_kpi_mantenimiento_maquina_turno

    UNION ALL
    SELECT 'MTTR = minutos de reparación / reparaciones',
           count(*)::bigint,
           count(*) FILTER (
               WHERE mttr_min IS NOT NULL
                 AND abs(
                     mttr_min
                     - minutos_reparacion::numeric / NULLIF(reparaciones, 0)
                 ) > 1e-9
           )::bigint
    FROM v_kpi_mantenimiento_maquina_turno

    UNION ALL
    SELECT 'Downtime % en mantenimiento = downtime / tiempo planificado',
           count(*)::bigint,
           count(*) FILTER (
               WHERE abs(
                   downtime_no_planificado_pct
                   - downtime_no_planificado_min::numeric
                     / NULLIF(tiempo_planificado_min, 0)
               ) > 1e-9
           )::bigint
    FROM v_kpi_mantenimiento_maquina_turno

    -- --- FPY (calidad) ---------------------------------------------------
    UNION ALL
    SELECT 'FPY = (inspeccionadas - retrabajo) / inspeccionadas',
           count(*)::bigint,
           count(*) FILTER (
               WHERE fpy IS NOT NULL
                 AND abs(
                     fpy
                     - (unidades_inspeccionadas - unidades_retrabajo)::numeric
                       / NULLIF(unidades_inspeccionadas, 0)
                 ) > 1e-9
           )::bigint
    FROM v_kpi_calidad_maquina_dia
)
SELECT chequeo,
       valor,
       incidencias,
       CASE WHEN incidencias = 0 THEN 'OK' ELSE 'REVISAR' END AS estado
FROM checks
ORDER BY estado DESC, chequeo;

-- Resumen global de los 10 KPI (180 días, datos sintéticos).
SELECT
    round(100.0 * sum(tiempo_operativo_min) / sum(tiempo_planificado_min), 4)
        AS disponibilidad_pct,
    round(100.0 * sum(minutos_ideales) / sum(tiempo_operativo_min), 4)
        AS rendimiento_pct,
    round(100.0 * sum(good_count) / sum(total_count), 4)
        AS calidad_pct,
    round(
        100.0 * sum(tiempo_operativo_min) / sum(tiempo_planificado_min)
        * sum(minutos_ideales) / sum(tiempo_operativo_min)
        * sum(good_count) / sum(total_count),
        4
    ) AS oee_pct,
    round(100.0 * sum(downtime_no_planificado_min) / sum(tiempo_planificado_min), 4)
        AS downtime_pct,
    round(100.0 * sum(scrap_count) / sum(total_count), 4)
        AS scrap_pct,
    round(sum(energia_kwh) / sum(good_count), 6)
        AS kwh_por_unidad_buena
FROM v_kpi_produccion;

SELECT
    round(sum(tiempo_operativo_min) / 60.0 / NULLIF(sum(fallas), 0), 4)
        AS mtbf_h,
    round(sum(minutos_reparacion)::numeric / NULLIF(sum(reparaciones), 0), 4)
        AS mttr_min
FROM v_kpi_mantenimiento_maquina_turno;

SELECT
    round(
        100.0 * (sum(unidades_inspeccionadas) - sum(unidades_retrabajo))
        / NULLIF(sum(unidades_inspeccionadas), 0),
        4
    ) AS fpy_pct
FROM v_kpi_calidad_maquina_dia;
