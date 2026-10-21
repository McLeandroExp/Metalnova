-- ============================================================================
-- 05_kpi_calidad_energia.sql — Scrap Rate, FPY y Energía por Unidad Buena.
-- Scrap y energía provienen de fact_produccion; FPY y retrabajo, de
-- fact_calidad. Se agregan por separado para no multiplicar conteos.
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- v_kpi_calidad_maquina_dia — grano: fecha × planta × línea × máquina.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_calidad_maquina_dia AS
WITH claves AS (
    SELECT id_maquina, id_tiempo FROM fact_produccion
    UNION
    SELECT id_maquina, id_tiempo FROM fact_calidad
), prod AS (
    SELECT
        id_maquina,
        id_tiempo,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(scrap_count)                  AS scrap_count,
        SUM(energia_kwh)                  AS energia_kwh
    FROM fact_produccion
    GROUP BY id_maquina, id_tiempo
), cal AS (
    SELECT
        id_maquina,
        id_tiempo,
        COUNT(*)                          AS inspecciones,
        SUM(unidades_inspeccionadas)      AS unidades_inspeccionadas,
        SUM(unidades_buenas)              AS unidades_buenas_inspeccion,
        SUM(unidades_defectuosas)         AS unidades_defectuosas,
        SUM(unidades_retrabajo)           AS unidades_retrabajo,
        COUNT(*) FILTER (WHERE es_retrabajo) AS inspecciones_con_retrabajo
    FROM fact_calidad
    GROUP BY id_maquina, id_tiempo
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
    c.id_tiempo,
    ti.fecha,
    ti.anio_mes,
    COALESCE(pr.tiempo_planificado_min, 0)      AS tiempo_planificado_min,
    COALESCE(pr.tiempo_operativo_min, 0)        AS tiempo_operativo_min,
    COALESCE(pr.downtime_no_planificado_min, 0) AS downtime_no_planificado_min,
    COALESCE(pr.total_count, 0)                 AS total_count,
    COALESCE(pr.good_count, 0)                  AS good_count,
    COALESCE(pr.scrap_count, 0)                 AS scrap_count,
    COALESCE(pr.energia_kwh, 0)                 AS energia_kwh,
    COALESCE(cal.inspecciones, 0)               AS inspecciones,
    COALESCE(cal.unidades_inspeccionadas, 0)    AS unidades_inspeccionadas,
    COALESCE(cal.unidades_buenas_inspeccion, 0) AS unidades_buenas_inspeccion,
    COALESCE(cal.unidades_defectuosas, 0)       AS unidades_defectuosas,
    COALESCE(cal.unidades_retrabajo, 0)         AS unidades_retrabajo,
    COALESCE(cal.inspecciones_con_retrabajo, 0) AS inspecciones_con_retrabajo,
    (COALESCE(pr.scrap_count, 0)::numeric
        / NULLIF(pr.total_count, 0)) AS scrap_rate,
    (COALESCE(pr.energia_kwh, 0)
        / NULLIF(pr.good_count, 0)) AS energia_por_unidad_buena,
    (COALESCE(pr.downtime_no_planificado_min, 0)::numeric
        / NULLIF(pr.tiempo_planificado_min, 0)) AS downtime_no_planificado_pct,
    (COALESCE(cal.unidades_defectuosas, 0)::numeric
        / NULLIF(cal.unidades_inspeccionadas, 0)) AS tasa_defectos,
    (COALESCE(cal.unidades_retrabajo, 0)::numeric
        / NULLIF(cal.unidades_inspeccionadas, 0)) AS tasa_retrabajo,
    ((COALESCE(cal.unidades_inspeccionadas, 0)
        - COALESCE(cal.unidades_retrabajo, 0))::numeric
        / NULLIF(cal.unidades_inspeccionadas, 0)) AS fpy
FROM claves c
JOIN dim_maquina m  ON m.id_maquina = c.id_maquina
JOIN dim_linea   l  ON l.id_linea   = m.id_linea
JOIN dim_planta  pl ON pl.id_planta = l.id_planta
JOIN dim_tiempo  ti ON ti.id_tiempo = c.id_tiempo
LEFT JOIN prod pr ON pr.id_maquina = c.id_maquina AND pr.id_tiempo = c.id_tiempo
LEFT JOIN cal ON cal.id_maquina = c.id_maquina AND cal.id_tiempo = c.id_tiempo;

-- ---------------------------------------------------------------------------
-- v_kpi_calidad_producto_dia — grano: fecha × familia × producto.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_calidad_producto_dia AS
WITH claves AS (
    SELECT id_producto, id_tiempo FROM fact_produccion
    UNION
    SELECT id_producto, id_tiempo FROM fact_calidad
), prod AS (
    SELECT
        id_producto,
        id_tiempo,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(scrap_count)                  AS scrap_count,
        SUM(energia_kwh)                  AS energia_kwh
    FROM fact_produccion
    GROUP BY id_producto, id_tiempo
), cal AS (
    SELECT
        id_producto,
        id_tiempo,
        COUNT(*)                          AS inspecciones,
        SUM(unidades_inspeccionadas)      AS unidades_inspeccionadas,
        SUM(unidades_buenas)              AS unidades_buenas_inspeccion,
        SUM(unidades_defectuosas)         AS unidades_defectuosas,
        SUM(unidades_retrabajo)           AS unidades_retrabajo,
        COUNT(*) FILTER (WHERE es_retrabajo) AS inspecciones_con_retrabajo
    FROM fact_calidad
    GROUP BY id_producto, id_tiempo
)
SELECT
    pr_producto.id_producto,
    pr_producto.codigo AS producto_codigo,
    pr_producto.nombre AS producto_nombre,
    fa.id_familia,
    fa.codigo AS familia_codigo,
    fa.nombre AS familia_nombre,
    k.id_tiempo,
    ti.fecha,
    ti.anio_mes,
    COALESCE(pr.tiempo_planificado_min, 0)      AS tiempo_planificado_min,
    COALESCE(pr.tiempo_operativo_min, 0)        AS tiempo_operativo_min,
    COALESCE(pr.downtime_no_planificado_min, 0) AS downtime_no_planificado_min,
    COALESCE(pr.total_count, 0)                 AS total_count,
    COALESCE(pr.good_count, 0)                  AS good_count,
    COALESCE(pr.scrap_count, 0)                 AS scrap_count,
    COALESCE(pr.energia_kwh, 0)                 AS energia_kwh,
    COALESCE(cal.inspecciones, 0)               AS inspecciones,
    COALESCE(cal.unidades_inspeccionadas, 0)    AS unidades_inspeccionadas,
    COALESCE(cal.unidades_buenas_inspeccion, 0) AS unidades_buenas_inspeccion,
    COALESCE(cal.unidades_defectuosas, 0)       AS unidades_defectuosas,
    COALESCE(cal.unidades_retrabajo, 0)         AS unidades_retrabajo,
    COALESCE(cal.inspecciones_con_retrabajo, 0) AS inspecciones_con_retrabajo,
    (COALESCE(pr.scrap_count, 0)::numeric
        / NULLIF(pr.total_count, 0)) AS scrap_rate,
    (COALESCE(pr.energia_kwh, 0)
        / NULLIF(pr.good_count, 0)) AS energia_por_unidad_buena,
    (COALESCE(pr.downtime_no_planificado_min, 0)::numeric
        / NULLIF(pr.tiempo_planificado_min, 0)) AS downtime_no_planificado_pct,
    (COALESCE(cal.unidades_defectuosas, 0)::numeric
        / NULLIF(cal.unidades_inspeccionadas, 0)) AS tasa_defectos,
    (COALESCE(cal.unidades_retrabajo, 0)::numeric
        / NULLIF(cal.unidades_inspeccionadas, 0)) AS tasa_retrabajo,
    ((COALESCE(cal.unidades_inspeccionadas, 0)
        - COALESCE(cal.unidades_retrabajo, 0))::numeric
        / NULLIF(cal.unidades_inspeccionadas, 0)) AS fpy
FROM claves k
JOIN dim_producto pr_producto ON pr_producto.id_producto = k.id_producto
JOIN dim_familia  fa ON fa.id_familia = pr_producto.id_familia
JOIN dim_tiempo   ti ON ti.id_tiempo  = k.id_tiempo
LEFT JOIN prod pr ON pr.id_producto = k.id_producto AND pr.id_tiempo = k.id_tiempo
LEFT JOIN cal ON cal.id_producto = k.id_producto AND cal.id_tiempo = k.id_tiempo;
