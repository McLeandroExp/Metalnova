-- ============================================================================
-- 03_kpi_oee.sql — OEE y componentes (A × P × Q) por grano de análisis.
-- Todas las vistas se construyen desde v_kpi_produccion y agregan sumando
-- numeradores y denominadores. Nunca se promedian porcentajes.
--
-- Granos cubiertos (FR-501): planta, línea, máquina, máquina-turno, producto.
-- El periodo se resuelve con fecha / anio_mes en cada vista.
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- v_kpi_oee_planta_dia — grano: fecha × planta.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_oee_planta_dia AS
WITH base AS (
    SELECT
        fecha,
        anio_mes,
        id_planta,
        planta_codigo,
        planta_nombre,
        SUM(tiempo_calendario_min)        AS tiempo_calendario_min,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(downtime_planificado_min)     AS downtime_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(scrap_count)                  AS scrap_count,
        SUM(minutos_ideales)              AS minutos_ideales,
        SUM(energia_kwh)                  AS energia_kwh,
        COUNT(*)                          AS filas_produccion,
        COUNT(DISTINCT (id_maquina, id_turno)) AS turnos_maquina
    FROM v_kpi_produccion
    GROUP BY fecha, anio_mes, id_planta, planta_codigo, planta_nombre
), calc AS (
    SELECT
        base.*,
        (tiempo_operativo_min::numeric / NULLIF(tiempo_planificado_min, 0)) AS disponibilidad,
        (minutos_ideales / NULLIF(tiempo_operativo_min, 0)) AS rendimiento,
        (good_count::numeric / NULLIF(total_count, 0)) AS calidad,
        (scrap_count::numeric / NULLIF(total_count, 0)) AS scrap_rate,
        (energia_kwh / NULLIF(good_count, 0)) AS energia_por_unidad_buena,
        (downtime_no_planificado_min::numeric
            / NULLIF(tiempo_planificado_min, 0)) AS downtime_no_planificado_pct
    FROM base
)
SELECT
    calc.*,
    (disponibilidad * rendimiento * calidad) AS oee
FROM calc;

-- ---------------------------------------------------------------------------
-- v_kpi_oee_linea_dia — grano: fecha × planta × línea.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_oee_linea_dia AS
WITH base AS (
    SELECT
        fecha,
        anio_mes,
        id_planta,
        planta_codigo,
        planta_nombre,
        id_linea,
        linea_codigo,
        linea_nombre,
        SUM(tiempo_calendario_min)        AS tiempo_calendario_min,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(downtime_planificado_min)     AS downtime_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(scrap_count)                  AS scrap_count,
        SUM(minutos_ideales)              AS minutos_ideales,
        SUM(energia_kwh)                  AS energia_kwh,
        COUNT(*)                          AS filas_produccion,
        COUNT(DISTINCT (id_maquina, id_turno)) AS turnos_maquina
    FROM v_kpi_produccion
    GROUP BY fecha, anio_mes, id_planta, planta_codigo, planta_nombre,
             id_linea, linea_codigo, linea_nombre
), calc AS (
    SELECT
        base.*,
        (tiempo_operativo_min::numeric / NULLIF(tiempo_planificado_min, 0)) AS disponibilidad,
        (minutos_ideales / NULLIF(tiempo_operativo_min, 0)) AS rendimiento,
        (good_count::numeric / NULLIF(total_count, 0)) AS calidad,
        (scrap_count::numeric / NULLIF(total_count, 0)) AS scrap_rate,
        (energia_kwh / NULLIF(good_count, 0)) AS energia_por_unidad_buena,
        (downtime_no_planificado_min::numeric
            / NULLIF(tiempo_planificado_min, 0)) AS downtime_no_planificado_pct
    FROM base
)
SELECT
    calc.*,
    (disponibilidad * rendimiento * calidad) AS oee
FROM calc;

-- ---------------------------------------------------------------------------
-- v_kpi_oee_maquina_dia — grano: fecha × planta × línea × máquina.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_oee_maquina_dia AS
WITH base AS (
    SELECT
        fecha,
        anio_mes,
        id_planta,
        planta_codigo,
        planta_nombre,
        id_linea,
        linea_codigo,
        linea_nombre,
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
        SUM(scrap_count)                  AS scrap_count,
        SUM(minutos_ideales)              AS minutos_ideales,
        SUM(energia_kwh)                  AS energia_kwh,
        COUNT(*)                          AS filas_produccion,
        COUNT(DISTINCT id_turno)          AS turnos_maquina
    FROM v_kpi_produccion
    GROUP BY fecha, anio_mes, id_planta, planta_codigo, planta_nombre,
             id_linea, linea_codigo, linea_nombre, id_maquina, maquina_codigo,
             maquina_nombre, maquina_tipo, maquina_criticidad
), calc AS (
    SELECT
        base.*,
        (tiempo_operativo_min::numeric / NULLIF(tiempo_planificado_min, 0)) AS disponibilidad,
        (minutos_ideales / NULLIF(tiempo_operativo_min, 0)) AS rendimiento,
        (good_count::numeric / NULLIF(total_count, 0)) AS calidad,
        (scrap_count::numeric / NULLIF(total_count, 0)) AS scrap_rate,
        (energia_kwh / NULLIF(good_count, 0)) AS energia_por_unidad_buena,
        (downtime_no_planificado_min::numeric
            / NULLIF(tiempo_planificado_min, 0)) AS downtime_no_planificado_pct
    FROM base
)
SELECT
    calc.*,
    (disponibilidad * rendimiento * calidad) AS oee
FROM calc;

-- ---------------------------------------------------------------------------
-- v_kpi_oee_maquina_turno — grano: fecha × máquina × turno.
-- Es el grano más fino para la matriz máquina-turno del informe (006).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_oee_maquina_turno AS
WITH base AS (
    SELECT
        fecha,
        anio_mes,
        id_planta,
        planta_codigo,
        planta_nombre,
        id_linea,
        linea_codigo,
        linea_nombre,
        id_maquina,
        maquina_codigo,
        maquina_nombre,
        maquina_tipo,
        maquina_criticidad,
        id_turno,
        turno_codigo,
        turno_nombre,
        SUM(tiempo_calendario_min)        AS tiempo_calendario_min,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(downtime_planificado_min)     AS downtime_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(scrap_count)                  AS scrap_count,
        SUM(minutos_ideales)              AS minutos_ideales,
        SUM(energia_kwh)                  AS energia_kwh,
        COUNT(*)                          AS filas_produccion
    FROM v_kpi_produccion
    GROUP BY fecha, anio_mes, id_planta, planta_codigo, planta_nombre,
             id_linea, linea_codigo, linea_nombre, id_maquina, maquina_codigo,
             maquina_nombre, maquina_tipo, maquina_criticidad,
             id_turno, turno_codigo, turno_nombre
), calc AS (
    SELECT
        base.*,
        (tiempo_operativo_min::numeric / NULLIF(tiempo_planificado_min, 0)) AS disponibilidad,
        (minutos_ideales / NULLIF(tiempo_operativo_min, 0)) AS rendimiento,
        (good_count::numeric / NULLIF(total_count, 0)) AS calidad,
        (scrap_count::numeric / NULLIF(total_count, 0)) AS scrap_rate,
        (energia_kwh / NULLIF(good_count, 0)) AS energia_por_unidad_buena,
        (downtime_no_planificado_min::numeric
            / NULLIF(tiempo_planificado_min, 0)) AS downtime_no_planificado_pct
    FROM base
)
SELECT
    calc.*,
    (disponibilidad * rendimiento * calidad) AS oee
FROM calc;

-- ---------------------------------------------------------------------------
-- v_kpi_oee_producto_dia — grano: fecha × familia × producto.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_oee_producto_dia AS
WITH base AS (
    SELECT
        fecha,
        anio_mes,
        id_familia,
        familia_codigo,
        familia_nombre,
        id_producto,
        producto_codigo,
        producto_nombre,
        SUM(tiempo_calendario_min)        AS tiempo_calendario_min,
        SUM(tiempo_planificado_min)       AS tiempo_planificado_min,
        SUM(downtime_planificado_min)     AS downtime_planificado_min,
        SUM(tiempo_operativo_min)         AS tiempo_operativo_min,
        SUM(downtime_no_planificado_min)  AS downtime_no_planificado_min,
        SUM(total_count)                  AS total_count,
        SUM(good_count)                   AS good_count,
        SUM(scrap_count)                  AS scrap_count,
        SUM(minutos_ideales)              AS minutos_ideales,
        SUM(energia_kwh)                  AS energia_kwh,
        COUNT(*)                          AS filas_produccion,
        COUNT(DISTINCT (id_maquina, id_turno)) AS turnos_maquina
    FROM v_kpi_produccion
    GROUP BY fecha, anio_mes, id_familia, familia_codigo, familia_nombre,
             id_producto, producto_codigo, producto_nombre
), calc AS (
    SELECT
        base.*,
        (tiempo_operativo_min::numeric / NULLIF(tiempo_planificado_min, 0)) AS disponibilidad,
        (minutos_ideales / NULLIF(tiempo_operativo_min, 0)) AS rendimiento,
        (good_count::numeric / NULLIF(total_count, 0)) AS calidad,
        (scrap_count::numeric / NULLIF(total_count, 0)) AS scrap_rate,
        (energia_kwh / NULLIF(good_count, 0)) AS energia_por_unidad_buena,
        (downtime_no_planificado_min::numeric
            / NULLIF(tiempo_planificado_min, 0)) AS downtime_no_planificado_pct
    FROM base
)
SELECT
    calc.*,
    (disponibilidad * rendimiento * calidad) AS oee
FROM calc;
