-- ============================================================================
-- 06_kpi_confiabilidad.sql — Indicadores de apoyo (Constitución §6):
-- conteo y duración de microparadas, y frecuencia de fallas cortas.
-- Se construyen sobre v_kpi_mantenimiento_maquina_turno para no duplicar la
-- regla G6 ni los joins.
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

CREATE OR REPLACE VIEW v_kpi_confiabilidad_apoyo_maquina_dia AS
WITH base AS (
    SELECT
        fecha,
        anio_mes,
        id_planta,
        planta_codigo,
        id_linea,
        linea_codigo,
        id_maquina,
        maquina_codigo,
        maquina_nombre,
        maquina_tipo,
        maquina_criticidad,
        SUM(tiempo_operativo_min)     AS tiempo_operativo_min,
        SUM(microparadas)             AS microparadas,
        SUM(minutos_microparadas)     AS minutos_microparadas,
        SUM(fallas)                   AS fallas,
        SUM(minutos_fallas)           AS minutos_fallas,
        SUM(fallas_cortas)            AS fallas_cortas,
        SUM(minutos_fallas_cortas)    AS minutos_fallas_cortas,
        COUNT(*)                      AS turnos_maquina
    FROM v_kpi_mantenimiento_maquina_turno
    GROUP BY fecha, anio_mes, id_planta, planta_codigo, id_linea, linea_codigo,
             id_maquina, maquina_codigo, maquina_nombre, maquina_tipo,
             maquina_criticidad
)
SELECT
    base.*,
    (tiempo_operativo_min / 60.0) AS tiempo_operativo_h,
    CASE WHEN tiempo_operativo_min > 0 AND fallas_cortas > 0
         THEN (tiempo_operativo_min / 60.0) / fallas_cortas END AS mtbf_corto_h,
    (100.0 * fallas_cortas
        / NULLIF(tiempo_operativo_min / 60.0, 0)) AS fallas_cortas_por_100h,
    (100.0 * microparadas
        / NULLIF(tiempo_operativo_min / 60.0, 0)) AS microparadas_por_100h,
    (minutos_microparadas::numeric / NULLIF(microparadas, 0)) AS duracion_media_micro_min,
    (minutos_fallas_cortas::numeric
        / NULLIF(fallas_cortas, 0)) AS duracion_media_falla_corta_min
FROM base;
