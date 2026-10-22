-- ============================================================================
-- 02_kpi_base.sql — Vistas KPI base (grano de hecho)
-- Cada vista expone el hecho con sus dimensiones conformadas y las medidas
-- calculadas a nivel de fila. Las vistas agregadas de 03..08 se construyen
-- sobre estas, de modo que la fórmula se define una sola vez.
--
-- Regla de agregación: los KPI de porcentaje nunca se promedian. Se suman
-- numeradores y denominadores y se divide al final (ponderación).
--
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Parámetros de las reglas de negocio (una sola fila).
-- Centraliza los umbrales de la Constitución §7.3 y §8 para que las vistas
-- sean verificables e idénticas entre SQL, Python y Power BI.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_parametros AS
SELECT
    5             AS microparada_min,
    30            AS falla_corta_min,
    20::numeric   AS mtbf_umbral_h,
    0.55::numeric AS oee_umbral,
    120           AS downtime_umbral_min,
    85::numeric   AS temperatura_umbral_c,
    15            AS temperatura_ventana_min,
    2             AS temperatura_lecturas_min,
    -- Cadencia declarada del feed sintético: dos lecturas de proceso por turno
    -- (el histórico emite en los minutos 90 y 300; las excursiones térmicas
    -- añaden tres más). La cadencia ideal de 15 min se evalúa aparte.
    2             AS senal_lecturas_turno_min;

-- ---------------------------------------------------------------------------
-- v_kpi_produccion — grano: una fila de fact_produccion.
-- Disponibilidad, Rendimiento, Calidad y OEE se calculan por fila; las vistas
-- agregadas las recombinan con SUM numerador / SUM denominador.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_produccion AS
WITH base AS (
    SELECT
        f.id_produccion,
        f.id_orden,
        o.codigo_orden,
        f.id_tiempo,
        ti.fecha,
        ti.anio,
        ti.mes,
        ti.anio_mes,
        ti.es_fin_semana,
        f.id_turno,
        t.codigo AS turno_codigo,
        t.nombre AS turno_nombre,
        l.id_planta,
        pl.codigo AS planta_codigo,
        pl.nombre AS planta_nombre,
        l.id_linea,
        l.codigo AS linea_codigo,
        l.nombre AS linea_nombre,
        m.id_maquina,
        m.codigo AS maquina_codigo,
        m.nombre AS maquina_nombre,
        m.tipo AS maquina_tipo,
        m.criticidad AS maquina_criticidad,
        f.id_producto,
        pr.codigo AS producto_codigo,
        pr.nombre AS producto_nombre,
        pr.id_familia,
        fa.codigo AS familia_codigo,
        fa.nombre AS familia_nombre,
        f.tiempo_calendario_min,
        f.tiempo_planificado_min,
        f.downtime_planificado_min,
        f.tiempo_operativo_min,
        f.downtime_no_planificado_min,
        f.total_count,
        f.good_count,
        f.scrap_count,
        f.ciclo_ideal_segundos,
        f.energia_kwh,
        (f.ciclo_ideal_segundos * f.total_count / 60.0) AS minutos_ideales,
        (f.tiempo_operativo_min * 60.0 / NULLIF(f.ciclo_ideal_segundos, 0)) AS unidades_potenciales,
        (f.tiempo_operativo_min::numeric / NULLIF(f.tiempo_planificado_min, 0)) AS disponibilidad,
        ((f.ciclo_ideal_segundos * f.total_count / 60.0)
            / NULLIF(f.tiempo_operativo_min, 0)) AS rendimiento,
        (f.good_count::numeric / NULLIF(f.total_count, 0)) AS calidad,
        (f.scrap_count::numeric / NULLIF(f.total_count, 0)) AS scrap_rate,
        (f.energia_kwh / NULLIF(f.good_count, 0)) AS energia_por_unidad_buena,
        (f.downtime_no_planificado_min::numeric
            / NULLIF(f.tiempo_planificado_min, 0)) AS downtime_no_planificado_pct
    FROM fact_produccion f
    JOIN dim_orden    o  ON o.id_orden     = f.id_orden
    JOIN dim_maquina  m  ON m.id_maquina   = f.id_maquina
    JOIN dim_linea    l  ON l.id_linea     = m.id_linea
    JOIN dim_planta   pl ON pl.id_planta   = l.id_planta
    JOIN dim_producto pr ON pr.id_producto = f.id_producto
    JOIN dim_familia  fa ON fa.id_familia  = pr.id_familia
    JOIN dim_turno    t  ON t.id_turno     = f.id_turno
    JOIN dim_tiempo   ti ON ti.id_tiempo   = f.id_tiempo
)
SELECT
    base.*,
    (base.disponibilidad * base.rendimiento * base.calidad) AS oee
FROM base;

-- ---------------------------------------------------------------------------
-- v_kpi_calidad — grano: una inspección/lote de fact_calidad.
-- FPY = (inspeccionadas - retrabajo) / inspeccionadas.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_calidad AS
WITH base AS (
    SELECT
        c.id_calidad,
        c.codigo_inspeccion,
        c.codigo_lote,
        c.id_maquina,
        m.codigo AS maquina_codigo,
        m.nombre AS maquina_nombre,
        l.id_planta,
        pl.codigo AS planta_codigo,
        l.id_linea,
        l.codigo AS linea_codigo,
        c.id_producto,
        pr.codigo AS producto_codigo,
        pr.nombre AS producto_nombre,
        pr.id_familia,
        fa.codigo AS familia_codigo,
        c.id_turno,
        t.codigo AS turno_codigo,
        c.id_tiempo,
        ti.fecha,
        ti.anio_mes,
        c.id_causa,
        ca.codigo AS causa_codigo,
        c.inspeccion_at,
        c.unidades_inspeccionadas,
        c.unidades_buenas,
        c.unidades_defectuosas,
        c.unidades_retrabajo,
        c.es_retrabajo,
        (c.unidades_defectuosas::numeric
            / NULLIF(c.unidades_inspeccionadas, 0)) AS tasa_defectos,
        (c.unidades_retrabajo::numeric
            / NULLIF(c.unidades_inspeccionadas, 0)) AS tasa_retrabajo,
        ((c.unidades_inspeccionadas - c.unidades_retrabajo)::numeric
            / NULLIF(c.unidades_inspeccionadas, 0)) AS fpy
    FROM fact_calidad c
    JOIN dim_maquina  m  ON m.id_maquina   = c.id_maquina
    JOIN dim_linea    l  ON l.id_linea     = m.id_linea
    JOIN dim_planta   pl ON pl.id_planta   = l.id_planta
    JOIN dim_producto pr ON pr.id_producto = c.id_producto
    JOIN dim_familia  fa ON fa.id_familia  = pr.id_familia
    JOIN dim_turno    t  ON t.id_turno     = c.id_turno
    JOIN dim_tiempo   ti ON ti.id_tiempo   = c.id_tiempo
    LEFT JOIN dim_causa ca ON ca.id_causa  = c.id_causa
)
SELECT base.*
FROM base;

-- ---------------------------------------------------------------------------
-- v_kpi_parada — grano: un episodio de parada.
-- Clasificación según Constitución §7.3 (G6):
--   microparada = no planificada, duración < microparada_min y sin CMMS.
--   falla       = no planificada y no microparada.
-- Se conserva el flag calculado por el ETL para trazabilidad.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_parada AS
WITH base AS (
    SELECT
        p.id_parada,
        p.id_maquina,
        m.codigo AS maquina_codigo,
        m.nombre AS maquina_nombre,
        m.tipo AS maquina_tipo,
        m.criticidad AS maquina_criticidad,
        l.id_planta,
        pl.codigo AS planta_codigo,
        l.id_linea,
        l.codigo AS linea_codigo,
        p.id_turno,
        t.codigo AS turno_codigo,
        p.id_tiempo,
        ti.fecha,
        ti.anio_mes,
        p.id_causa,
        ca.codigo AS causa_codigo,
        ca.categoria AS causa_categoria,
        ca.es_planificada AS causa_es_planificada,
        p.id_mantenimiento,
        p.inicio_at,
        p.fin_at,
        p.duracion_min,
        p.es_planificada,
        p.es_microparada AS es_microparada_etl,
        parm.microparada_min,
        parm.falla_corta_min,
        (NOT p.es_planificada
            AND p.duracion_min < parm.microparada_min
            AND p.id_mantenimiento IS NULL) AS es_microparada_regla
    FROM fact_parada p
    JOIN dim_maquina m  ON m.id_maquina = p.id_maquina
    JOIN dim_linea   l  ON l.id_linea   = m.id_linea
    JOIN dim_planta  pl ON pl.id_planta = l.id_planta
    JOIN dim_turno   t  ON t.id_turno   = p.id_turno
    JOIN dim_tiempo  ti ON ti.id_tiempo = p.id_tiempo
    JOIN dim_causa   ca ON ca.id_causa  = p.id_causa
    CROSS JOIN v_kpi_parametros parm
)
SELECT
    base.*,
    (NOT base.es_planificada AND NOT base.es_microparada_regla) AS es_falla,
    (NOT base.es_planificada
        AND NOT base.es_microparada_regla
        AND base.duracion_min < base.falla_corta_min) AS es_falla_corta,
    CASE
        WHEN base.es_planificada THEN 'planificada'
        WHEN base.es_microparada_regla THEN 'microparada'
        ELSE 'falla'
    END AS clasificacion
FROM base;

-- ---------------------------------------------------------------------------
-- v_kpi_mantenimiento — grano: una orden/intervención de mantenimiento.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_kpi_mantenimiento AS
SELECT
    f.id_mantenimiento,
    f.codigo_orden_trabajo,
    f.id_maquina,
    m.codigo AS maquina_codigo,
    m.nombre AS maquina_nombre,
    m.tipo AS maquina_tipo,
    m.criticidad AS maquina_criticidad,
    l.id_planta,
    pl.codigo AS planta_codigo,
    l.id_linea,
    l.codigo AS linea_codigo,
    f.id_tecnico,
    te.codigo AS tecnico_codigo,
    te.nombre AS tecnico_nombre,
    te.especialidad AS tecnico_especialidad,
    f.id_causa,
    ca.codigo AS causa_codigo,
    f.id_turno,
    t.codigo AS turno_codigo,
    f.id_tiempo,
    ti.fecha,
    ti.anio_mes,
    f.tipo,
    f.inicio_at,
    f.fin_at,
    f.duracion_min,
    f.costo_estimado_usd,
    f.estado,
    (f.tipo = 'correctivo' AND f.estado = 'cerrada') AS es_correctivo_cerrado
FROM fact_mantenimiento f
JOIN dim_maquina m  ON m.id_maquina = f.id_maquina
JOIN dim_linea   l  ON l.id_linea   = m.id_linea
JOIN dim_planta  pl ON pl.id_planta = l.id_planta
JOIN dim_tecnico te ON te.id_tecnico = f.id_tecnico
JOIN dim_causa   ca ON ca.id_causa  = f.id_causa
JOIN dim_turno   t  ON t.id_turno   = f.id_turno
JOIN dim_tiempo  ti ON ti.id_tiempo = f.id_tiempo;
