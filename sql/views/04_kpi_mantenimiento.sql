-- ============================================================================
-- 04_kpi_mantenimiento.sql — MTBF, MTTR, downtime y confiabilidad operativa.
-- Fuentes de verdad (Constitución §7.2):
--   tiempo operativo / producción -> fact_produccion (MES)
--   fallas y paradas              -> fact_parada (transiciones IoT)
--   reparaciones                  -> fact_mantenimiento (CMMS cerrado)
--
-- Regla G6 (Constitución §7.3): falla = parada no planificada que no es
-- microparada; microparada = duración < microparada_min y sin orden CMMS.
--
-- Los joins se hacen sobre agregados por (máquina, turno, día) para no
-- multiplicar filas ni duraciones.
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- v_kpi_mantenimiento_maquina_turno — grano: fecha × máquina × turno.
-- Incluye claves con producción, parada o mantenimiento, de modo que un
-- evento de parada sin producción también aparezca (útil para la ingesta 004).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_mantenimiento_maquina_turno AS
WITH claves AS (
    SELECT id_maquina, id_turno, id_tiempo FROM fact_produccion
    UNION
    SELECT id_maquina, id_turno, id_tiempo FROM fact_parada
    UNION
    SELECT id_maquina, id_turno, id_tiempo FROM fact_mantenimiento
), prod AS (
    SELECT
        id_maquina,
        id_turno,
        id_tiempo,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(tiempo_calendario_min)        AS tiempo_calendario_min,
        SUM(downtime_planificado_min)     AS downtime_planificado_min
    FROM fact_produccion
    GROUP BY id_maquina, id_turno, id_tiempo
), par AS (
    SELECT
        p.id_maquina,
        p.id_turno,
        p.id_tiempo,
        COUNT(*) FILTER (WHERE NOT p.es_planificada) AS paradas_no_planificadas,
        COALESCE(SUM(p.duracion_min)
            FILTER (WHERE NOT p.es_planificada), 0) AS minutos_no_planificados,
        COUNT(*) FILTER (
            WHERE NOT p.es_planificada
              AND NOT (p.duracion_min < prm.microparada_min
                       AND p.id_mantenimiento IS NULL)
        ) AS fallas,
        COALESCE(SUM(p.duracion_min) FILTER (
            WHERE NOT p.es_planificada
              AND NOT (p.duracion_min < prm.microparada_min
                       AND p.id_mantenimiento IS NULL)
        ), 0) AS minutos_fallas,
        COUNT(*) FILTER (
            WHERE NOT p.es_planificada
              AND p.duracion_min < prm.microparada_min
              AND p.id_mantenimiento IS NULL
        ) AS microparadas,
        COALESCE(SUM(p.duracion_min) FILTER (
            WHERE NOT p.es_planificada
              AND p.duracion_min < prm.microparada_min
              AND p.id_mantenimiento IS NULL
        ), 0) AS minutos_microparadas,
        COUNT(*) FILTER (
            WHERE NOT p.es_planificada
              AND NOT (p.duracion_min < prm.microparada_min
                       AND p.id_mantenimiento IS NULL)
              AND p.duracion_min < prm.falla_corta_min
        ) AS fallas_cortas,
        COALESCE(SUM(p.duracion_min) FILTER (
            WHERE NOT p.es_planificada
              AND NOT (p.duracion_min < prm.microparada_min
                       AND p.id_mantenimiento IS NULL)
              AND p.duracion_min < prm.falla_corta_min
        ), 0) AS minutos_fallas_cortas
    FROM fact_parada p
    CROSS JOIN v_kpi_parametros prm
    GROUP BY p.id_maquina, p.id_turno, p.id_tiempo
), mant AS (
    SELECT
        id_maquina,
        id_turno,
        id_tiempo,
        COUNT(*) FILTER (WHERE tipo = 'correctivo' AND estado = 'cerrada') AS reparaciones,
        COALESCE(SUM(duracion_min)
            FILTER (WHERE tipo = 'correctivo' AND estado = 'cerrada'), 0) AS minutos_reparacion,
        COUNT(*) AS intervenciones,
        COALESCE(SUM(duracion_min), 0) AS minutos_intervencion,
        COALESCE(SUM(costo_estimado_usd), 0) AS costo_mantenimiento_usd
    FROM fact_mantenimiento
    GROUP BY id_maquina, id_turno, id_tiempo
)
SELECT
    c.id_maquina,
    m.codigo AS maquina_codigo,
    m.nombre AS maquina_nombre,
    m.tipo AS maquina_tipo,
    m.criticidad AS maquina_criticidad,
    l.id_planta,
    pl.codigo AS planta_codigo,
    l.id_linea,
    l.codigo AS linea_codigo,
    c.id_turno,
    t.codigo AS turno_codigo,
    c.id_tiempo,
    ti.fecha,
    ti.anio_mes,
    (ti.fecha + t.hora_inicio) AS turno_inicio_at,
    COALESCE(pr.tiempo_calendario_min, 0)       AS tiempo_calendario_min,
    COALESCE(pr.tiempo_planificado_min, 0)      AS tiempo_planificado_min,
    COALESCE(pr.downtime_planificado_min, 0)    AS downtime_planificado_min,
    COALESCE(pr.tiempo_operativo_min, 0)        AS tiempo_operativo_min,
    COALESCE(pr.downtime_no_planificado_min,
             pa.minutos_no_planificados, 0)     AS downtime_no_planificado_min,
    COALESCE(pr.total_count, 0)                 AS total_count,
    COALESCE(pr.good_count, 0)                  AS good_count,
    COALESCE(pa.paradas_no_planificadas, 0)     AS paradas_no_planificadas,
    COALESCE(pa.minutos_no_planificados, 0)     AS minutos_no_planificados_parada,
    COALESCE(pa.fallas, 0)                      AS fallas,
    COALESCE(pa.minutos_fallas, 0)              AS minutos_fallas,
    COALESCE(pa.microparadas, 0)                AS microparadas,
    COALESCE(pa.minutos_microparadas, 0)        AS minutos_microparadas,
    COALESCE(pa.fallas_cortas, 0)               AS fallas_cortas,
    COALESCE(pa.minutos_fallas_cortas, 0)       AS minutos_fallas_cortas,
    COALESCE(ma.reparaciones, 0)                AS reparaciones,
    COALESCE(ma.minutos_reparacion, 0)          AS minutos_reparacion,
    COALESCE(ma.intervenciones, 0)              AS intervenciones,
    COALESCE(ma.minutos_intervencion, 0)        AS minutos_intervencion,
    COALESCE(ma.costo_mantenimiento_usd, 0)     AS costo_mantenimiento_usd,
    (COALESCE(pr.tiempo_operativo_min, 0) / 60.0) AS tiempo_operativo_h,
    CASE
        WHEN COALESCE(pr.tiempo_operativo_min, 0) > 0
         AND COALESCE(pa.fallas, 0) > 0
        THEN (COALESCE(pr.tiempo_operativo_min, 0) / 60.0) / pa.fallas
    END AS mtbf_h,
    (COALESCE(ma.minutos_reparacion, 0)::numeric
        / NULLIF(ma.reparaciones, 0)) AS mttr_min,
    (COALESCE(pr.downtime_no_planificado_min,
              pa.minutos_no_planificados, 0)::numeric
        / NULLIF(pr.tiempo_planificado_min, 0)) AS downtime_no_planificado_pct,
    CASE
        WHEN COALESCE(pr.tiempo_operativo_min, 0) > 0
         AND COALESCE(pa.fallas_cortas, 0) > 0
        THEN (COALESCE(pr.tiempo_operativo_min, 0) / 60.0) / pa.fallas_cortas
    END AS mtbf_corto_h,
    (100.0 * COALESCE(pa.fallas_cortas, 0)
        / NULLIF(COALESCE(pr.tiempo_operativo_min, 0) / 60.0, 0)) AS fallas_cortas_por_100h,
    (100.0 * COALESCE(pa.microparadas, 0)
        / NULLIF(COALESCE(pr.tiempo_operativo_min, 0) / 60.0, 0)) AS microparadas_por_100h,
    (COALESCE(pa.minutos_microparadas, 0)::numeric
        / NULLIF(pa.microparadas, 0)) AS duracion_media_micro_min,
    (COALESCE(pa.minutos_fallas, 0)::numeric
        / NULLIF(pa.fallas, 0)) AS duracion_media_falla_min
FROM claves c
JOIN dim_maquina m  ON m.id_maquina = c.id_maquina
JOIN dim_linea   l  ON l.id_linea   = m.id_linea
JOIN dim_planta  pl ON pl.id_planta = l.id_planta
JOIN dim_turno   t  ON t.id_turno   = c.id_turno
JOIN dim_tiempo  ti ON ti.id_tiempo = c.id_tiempo
LEFT JOIN prod pr ON pr.id_maquina = c.id_maquina
                 AND pr.id_turno   = c.id_turno
                 AND pr.id_tiempo  = c.id_tiempo
LEFT JOIN par  pa ON pa.id_maquina = c.id_maquina
                 AND pa.id_turno   = c.id_turno
                 AND pa.id_tiempo  = c.id_tiempo
LEFT JOIN mant ma ON ma.id_maquina = c.id_maquina
                 AND ma.id_turno   = c.id_turno
                 AND ma.id_tiempo  = c.id_tiempo;

-- ---------------------------------------------------------------------------
-- v_kpi_mantenimiento_maquina_dia — grano: fecha × planta × línea × máquina.
-- Agrega el turno; MTBF y MTTR se recalculan con SUM/SUM.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_mantenimiento_maquina_dia AS
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
        SUM(tiempo_calendario_min)        AS tiempo_calendario_min,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(downtime_planificado_min)     AS downtime_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(paradas_no_planificadas)      AS paradas_no_planificadas,
        SUM(minutos_no_planificados_parada) AS minutos_no_planificados_parada,
        SUM(fallas)                       AS fallas,
        SUM(minutos_fallas)               AS minutos_fallas,
        SUM(microparadas)                 AS microparadas,
        SUM(minutos_microparadas)         AS minutos_microparadas,
        SUM(fallas_cortas)                AS fallas_cortas,
        SUM(minutos_fallas_cortas)        AS minutos_fallas_cortas,
        SUM(reparaciones)                 AS reparaciones,
        SUM(minutos_reparacion)           AS minutos_reparacion,
        SUM(intervenciones)               AS intervenciones,
        SUM(minutos_intervencion)         AS minutos_intervencion,
        SUM(costo_mantenimiento_usd)      AS costo_mantenimiento_usd,
        COUNT(*)                          AS turnos_maquina
    FROM v_kpi_mantenimiento_maquina_turno
    GROUP BY fecha, anio_mes, id_planta, planta_codigo, id_linea, linea_codigo,
             id_maquina, maquina_codigo, maquina_nombre, maquina_tipo,
             maquina_criticidad
)
SELECT
    base.*,
    (tiempo_operativo_min / 60.0) AS tiempo_operativo_h,
    CASE WHEN tiempo_operativo_min > 0 AND fallas > 0
         THEN (tiempo_operativo_min / 60.0) / fallas END AS mtbf_h,
    (minutos_reparacion::numeric / NULLIF(reparaciones, 0)) AS mttr_min,
    (downtime_no_planificado_min::numeric
        / NULLIF(tiempo_planificado_min, 0)) AS downtime_no_planificado_pct,
    CASE WHEN tiempo_operativo_min > 0 AND fallas_cortas > 0
         THEN (tiempo_operativo_min / 60.0) / fallas_cortas END AS mtbf_corto_h,
    (100.0 * fallas_cortas
        / NULLIF(tiempo_operativo_min / 60.0, 0)) AS fallas_cortas_por_100h,
    (100.0 * microparadas
        / NULLIF(tiempo_operativo_min / 60.0, 0)) AS microparadas_por_100h,
    (minutos_microparadas::numeric / NULLIF(microparadas, 0)) AS duracion_media_micro_min,
    (minutos_fallas::numeric / NULLIF(fallas, 0)) AS duracion_media_falla_min
FROM base;

-- ---------------------------------------------------------------------------
-- v_kpi_mantenimiento_maquina_mes — grano: mes × planta × línea × máquina.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_mantenimiento_maquina_mes AS
WITH base AS (
    SELECT
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
        SUM(tiempo_calendario_min)        AS tiempo_calendario_min,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(downtime_planificado_min)     AS downtime_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(paradas_no_planificadas)      AS paradas_no_planificadas,
        SUM(minutos_no_planificados_parada) AS minutos_no_planificados_parada,
        SUM(fallas)                       AS fallas,
        SUM(minutos_fallas)               AS minutos_fallas,
        SUM(microparadas)                 AS microparadas,
        SUM(minutos_microparadas)         AS minutos_microparadas,
        SUM(fallas_cortas)                AS fallas_cortas,
        SUM(minutos_fallas_cortas)        AS minutos_fallas_cortas,
        SUM(reparaciones)                 AS reparaciones,
        SUM(minutos_reparacion)           AS minutos_reparacion,
        SUM(intervenciones)               AS intervenciones,
        SUM(minutos_intervencion)         AS minutos_intervencion,
        SUM(costo_mantenimiento_usd)      AS costo_mantenimiento_usd,
        SUM(turnos_maquina)               AS turnos_maquina,
        COUNT(*)                          AS dias_con_datos
    FROM v_kpi_mantenimiento_maquina_dia
    GROUP BY anio_mes, id_planta, planta_codigo, id_linea, linea_codigo,
             id_maquina, maquina_codigo, maquina_nombre, maquina_tipo,
             maquina_criticidad
)
SELECT
    base.*,
    (tiempo_operativo_min / 60.0) AS tiempo_operativo_h,
    CASE WHEN tiempo_operativo_min > 0 AND fallas > 0
         THEN (tiempo_operativo_min / 60.0) / fallas END AS mtbf_h,
    (minutos_reparacion::numeric / NULLIF(reparaciones, 0)) AS mttr_min,
    (downtime_no_planificado_min::numeric
        / NULLIF(tiempo_planificado_min, 0)) AS downtime_no_planificado_pct,
    CASE WHEN tiempo_operativo_min > 0 AND fallas_cortas > 0
         THEN (tiempo_operativo_min / 60.0) / fallas_cortas END AS mtbf_corto_h,
    (100.0 * fallas_cortas
        / NULLIF(tiempo_operativo_min / 60.0, 0)) AS fallas_cortas_por_100h,
    (100.0 * microparadas
        / NULLIF(tiempo_operativo_min / 60.0, 0)) AS microparadas_por_100h,
    (minutos_microparadas::numeric / NULLIF(microparadas, 0)) AS duracion_media_micro_min,
    (minutos_fallas::numeric / NULLIF(fallas, 0)) AS duracion_media_falla_min
FROM base;

-- ---------------------------------------------------------------------------
-- v_kpi_mantenimiento_planta_dia — grano: fecha × planta.
-- Vista ejecutiva de downtime, MTBF y MTTR.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_mantenimiento_planta_dia AS
WITH base AS (
    SELECT
        fecha,
        anio_mes,
        id_planta,
        planta_codigo,
        SUM(tiempo_calendario_min)        AS tiempo_calendario_min,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(downtime_planificado_min)     AS downtime_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(paradas_no_planificadas)      AS paradas_no_planificadas,
        SUM(minutos_no_planificados_parada) AS minutos_no_planificados_parada,
        SUM(fallas)                       AS fallas,
        SUM(minutos_fallas)               AS minutos_fallas,
        SUM(microparadas)                 AS microparadas,
        SUM(minutos_microparadas)         AS minutos_microparadas,
        SUM(fallas_cortas)                AS fallas_cortas,
        SUM(minutos_fallas_cortas)        AS minutos_fallas_cortas,
        SUM(reparaciones)                 AS reparaciones,
        SUM(minutos_reparacion)           AS minutos_reparacion,
        SUM(intervenciones)               AS intervenciones,
        SUM(minutos_intervencion)         AS minutos_intervencion,
        SUM(costo_mantenimiento_usd)      AS costo_mantenimiento_usd,
        SUM(turnos_maquina)               AS turnos_maquina,
        COUNT(DISTINCT id_maquina)
            FILTER (WHERE fallas > 0)     AS maquinas_con_fallas,
        COUNT(DISTINCT id_maquina)
            FILTER (WHERE microparadas > 0) AS maquinas_con_microparadas
    FROM v_kpi_mantenimiento_maquina_dia
    GROUP BY fecha, anio_mes, id_planta, planta_codigo
)
SELECT
    base.*,
    (tiempo_operativo_min / 60.0) AS tiempo_operativo_h,
    CASE WHEN tiempo_operativo_min > 0 AND fallas > 0
         THEN (tiempo_operativo_min / 60.0) / fallas END AS mtbf_h,
    (minutos_reparacion::numeric / NULLIF(reparaciones, 0)) AS mttr_min,
    (downtime_no_planificado_min::numeric
        / NULLIF(tiempo_planificado_min, 0)) AS downtime_no_planificado_pct,
    CASE WHEN tiempo_operativo_min > 0 AND fallas_cortas > 0
         THEN (tiempo_operativo_min / 60.0) / fallas_cortas END AS mtbf_corto_h,
    (100.0 * fallas_cortas
        / NULLIF(tiempo_operativo_min / 60.0, 0)) AS fallas_cortas_por_100h,
    (100.0 * microparadas
        / NULLIF(tiempo_operativo_min / 60.0, 0)) AS microparadas_por_100h,
    (minutos_microparadas::numeric / NULLIF(microparadas, 0)) AS duracion_media_micro_min,
    (minutos_fallas::numeric / NULLIF(fallas, 0)) AS duracion_media_falla_min
FROM base;
