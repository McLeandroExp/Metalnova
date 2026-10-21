-- ============================================================================
-- 07_loss_tree.sql — Árbol de pérdidas (Loss Tree) del OEE.
-- Descompone las pérdidas en minutos equivalentes:
--   Disponibilidad = tiempo planificado - tiempo operativo.
--   Rendimiento    = tiempo operativo - tiempo ideal de las unidades producidas.
--   Calidad        = unidades rechazadas × ciclo ideal.
-- La participación se calcula sobre el total de pérdidas de la fila/grupo.
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

CREATE OR REPLACE VIEW v_loss_tree AS
WITH base AS (
    SELECT
        id_produccion,
        id_orden,
        fecha,
        anio_mes,
        id_planta,
        planta_codigo,
        id_linea,
        linea_codigo,
        id_maquina,
        maquina_codigo,
        maquina_tipo,
        maquina_criticidad,
        id_turno,
        turno_codigo,
        id_producto,
        producto_codigo,
        id_familia,
        familia_codigo,
        tiempo_planificado_min,
        tiempo_operativo_min,
        total_count,
        good_count,
        scrap_count,
        ciclo_ideal_segundos,
        minutos_ideales,
        oee,
        downtime_no_planificado_min AS minutos_perdidos_disponibilidad,
        GREATEST(tiempo_operativo_min - minutos_ideales, 0) AS minutos_perdidos_rendimiento,
        (scrap_count * ciclo_ideal_segundos / 60.0) AS minutos_perdidos_calidad,
        unidades_potenciales,
        GREATEST(unidades_potenciales - total_count, 0) AS unidades_no_producidas,
        scrap_count AS unidades_scrap
    FROM v_kpi_produccion
), suma AS (
    SELECT
        base.*,
        (minutos_perdidos_disponibilidad
            + minutos_perdidos_rendimiento
            + minutos_perdidos_calidad) AS minutos_perdidos_total
    FROM base
)
SELECT
    suma.*,
    (minutos_perdidos_disponibilidad::numeric
        / NULLIF(minutos_perdidos_total, 0)) AS participacion_disponibilidad,
    (minutos_perdidos_rendimiento::numeric
        / NULLIF(minutos_perdidos_total, 0)) AS participacion_rendimiento,
    (minutos_perdidos_calidad::numeric
        / NULLIF(minutos_perdidos_total, 0)) AS participacion_calidad
FROM suma;

-- ---------------------------------------------------------------------------
-- v_loss_tree_maquina_mes — grano: mes × planta × línea × máquina.
-- Agregado para el Pareto de pérdidas y el drill-down por activo.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_loss_tree_maquina_mes AS
WITH base AS (
    SELECT
        anio_mes,
        id_planta,
        planta_codigo,
        id_linea,
        linea_codigo,
        id_maquina,
        maquina_codigo,
        maquina_tipo,
        maquina_criticidad,
        SUM(tiempo_planificado_min)          AS tiempo_planificado_min,
        SUM(tiempo_operativo_min)            AS tiempo_operativo_min,
        SUM(minutos_ideales)                 AS minutos_ideales,
        SUM(total_count)                     AS total_count,
        SUM(good_count)                      AS good_count,
        SUM(scrap_count)                     AS scrap_count,
        SUM(minutos_perdidos_disponibilidad) AS minutos_perdidos_disponibilidad,
        SUM(minutos_perdidos_rendimiento)    AS minutos_perdidos_rendimiento,
        SUM(minutos_perdidos_calidad)        AS minutos_perdidos_calidad,
        SUM(minutos_perdidos_total)          AS minutos_perdidos_total,
        SUM(unidades_potenciales)            AS unidades_potenciales,
        SUM(unidades_no_producidas)          AS unidades_no_producidas,
        SUM(unidades_scrap)                  AS unidades_scrap,
        COUNT(*)                             AS filas_produccion,
        COUNT(DISTINCT fecha)                AS dias_con_datos
    FROM v_loss_tree
    GROUP BY anio_mes, id_planta, planta_codigo, id_linea, linea_codigo,
             id_maquina, maquina_codigo, maquina_tipo, maquina_criticidad
), calc AS (
    SELECT
        base.*,
        (tiempo_operativo_min::numeric
            / NULLIF(tiempo_planificado_min, 0)) AS disponibilidad,
        (minutos_ideales / NULLIF(tiempo_operativo_min, 0)) AS rendimiento,
        (good_count::numeric / NULLIF(total_count, 0)) AS calidad,
        (minutos_perdidos_disponibilidad::numeric
            / NULLIF(minutos_perdidos_total, 0)) AS participacion_disponibilidad,
        (minutos_perdidos_rendimiento::numeric
            / NULLIF(minutos_perdidos_total, 0)) AS participacion_rendimiento,
        (minutos_perdidos_calidad::numeric
            / NULLIF(minutos_perdidos_total, 0)) AS participacion_calidad
    FROM base
)
SELECT
    calc.*,
    (disponibilidad * rendimiento * calidad) AS oee
FROM calc;
