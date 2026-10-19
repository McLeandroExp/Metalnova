-- ============================================================================
-- 01_vistas_base.sql — Vistas base para Power BI
-- Contrato estable: exponen cada hecho con sus dimensiones conformadas.
-- Los joins son 1:1 sobre claves primarias, por lo que no multiplican filas.
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

CREATE OR REPLACE VIEW v_produccion_detalle AS
SELECT
    f.id_produccion,
    f.id_orden,
    o.codigo_orden,
    o.cantidad_planificada,
    f.id_maquina,
    m.codigo            AS maquina_codigo,
    m.nombre            AS maquina_nombre,
    m.criticidad        AS maquina_criticidad,
    l.id_linea,
    l.codigo            AS linea_codigo,
    l.nombre            AS linea_nombre,
    pl.id_planta,
    pl.codigo           AS planta_codigo,
    pl.nombre           AS planta_nombre,
    f.id_producto,
    pr.codigo           AS producto_codigo,
    pr.nombre           AS producto_nombre,
    fa.id_familia,
    fa.codigo           AS familia_codigo,
    fa.nombre           AS familia_nombre,
    f.id_turno,
    t.codigo            AS turno_codigo,
    t.nombre            AS turno_nombre,
    f.id_tiempo,
    ti.fecha,
    ti.anio,
    ti.mes,
    ti.anio_mes,
    f.inicio_at,
    f.fin_at,
    f.tiempo_calendario_min,
    f.tiempo_planificado_min,
    f.tiempo_operativo_min,
    f.downtime_planificado_min,
    f.downtime_no_planificado_min,
    f.total_count,
    f.good_count,
    f.scrap_count,
    f.ciclo_ideal_segundos,
    f.energia_kwh
FROM fact_produccion f
JOIN dim_orden    o  ON o.id_orden   = f.id_orden
JOIN dim_maquina  m  ON m.id_maquina = f.id_maquina
JOIN dim_linea    l  ON l.id_linea   = m.id_linea
JOIN dim_planta   pl ON pl.id_planta = l.id_planta
JOIN dim_producto pr ON pr.id_producto = f.id_producto
JOIN dim_familia  fa ON fa.id_familia = pr.id_familia
JOIN dim_turno    t  ON t.id_turno   = f.id_turno
JOIN dim_tiempo   ti ON ti.id_tiempo = f.id_tiempo;

CREATE OR REPLACE VIEW v_parada_detalle AS
SELECT
    f.id_parada,
    f.id_maquina,
    m.codigo            AS maquina_codigo,
    m.nombre            AS maquina_nombre,
    m.criticidad        AS maquina_criticidad,
    l.id_linea,
    l.codigo            AS linea_codigo,
    pl.id_planta,
    pl.codigo           AS planta_codigo,
    pl.nombre           AS planta_nombre,
    f.id_turno,
    t.codigo            AS turno_codigo,
    f.id_tiempo,
    ti.fecha,
    ti.anio,
    ti.mes,
    ti.anio_mes,
    f.id_causa,
    c.codigo            AS causa_codigo,
    c.descripcion       AS causa_descripcion,
    c.categoria         AS causa_categoria,
    f.id_mantenimiento,
    f.inicio_at,
    f.fin_at,
    f.duracion_min,
    f.es_planificada,
    f.es_microparada,
    f.causa_detalle
FROM fact_parada f
JOIN dim_maquina m  ON m.id_maquina = f.id_maquina
JOIN dim_linea   l  ON l.id_linea   = m.id_linea
JOIN dim_planta  pl ON pl.id_planta = l.id_planta
JOIN dim_turno   t  ON t.id_turno   = f.id_turno
JOIN dim_tiempo  ti ON ti.id_tiempo = f.id_tiempo
JOIN dim_causa   c  ON c.id_causa   = f.id_causa;

CREATE OR REPLACE VIEW v_mantenimiento_detalle AS
SELECT
    f.id_mantenimiento,
    f.codigo_orden_trabajo,
    f.id_maquina,
    m.codigo            AS maquina_codigo,
    m.nombre            AS maquina_nombre,
    m.criticidad        AS maquina_criticidad,
    l.id_linea,
    l.codigo            AS linea_codigo,
    pl.id_planta,
    pl.codigo           AS planta_codigo,
    pl.nombre           AS planta_nombre,
    f.id_tecnico,
    te.codigo           AS tecnico_codigo,
    te.nombre           AS tecnico_nombre,
    te.especialidad     AS tecnico_especialidad,
    f.id_causa,
    c.codigo            AS causa_codigo,
    c.descripcion       AS causa_descripcion,
    f.id_turno,
    t.codigo            AS turno_codigo,
    f.id_tiempo,
    ti.fecha,
    ti.anio,
    ti.mes,
    ti.anio_mes,
    f.tipo,
    f.inicio_at,
    f.fin_at,
    f.duracion_min,
    f.costo_estimado_usd,
    f.estado
FROM fact_mantenimiento f
JOIN dim_maquina m  ON m.id_maquina = f.id_maquina
JOIN dim_linea   l  ON l.id_linea   = m.id_linea
JOIN dim_planta  pl ON pl.id_planta = l.id_planta
JOIN dim_tecnico te ON te.id_tecnico = f.id_tecnico
JOIN dim_causa   c  ON c.id_causa   = f.id_causa
JOIN dim_turno   t  ON t.id_turno   = f.id_turno
JOIN dim_tiempo  ti ON ti.id_tiempo = f.id_tiempo;

CREATE OR REPLACE VIEW v_calidad_detalle AS
SELECT
    f.id_calidad,
    f.codigo_inspeccion,
    f.codigo_lote,
    f.id_maquina,
    m.codigo            AS maquina_codigo,
    m.nombre            AS maquina_nombre,
    l.id_linea,
    l.codigo            AS linea_codigo,
    pl.id_planta,
    pl.codigo           AS planta_codigo,
    pl.nombre           AS planta_nombre,
    f.id_producto,
    pr.codigo           AS producto_codigo,
    pr.nombre           AS producto_nombre,
    fa.id_familia,
    fa.codigo           AS familia_codigo,
    f.id_turno,
    t.codigo            AS turno_codigo,
    f.id_tiempo,
    ti.fecha,
    ti.anio,
    ti.mes,
    ti.anio_mes,
    f.id_causa,
    c.codigo            AS causa_codigo,
    c.descripcion       AS causa_descripcion,
    f.inspeccion_at,
    f.unidades_inspeccionadas,
    f.unidades_buenas,
    f.unidades_defectuosas,
    f.unidades_retrabajo,
    f.es_retrabajo
FROM fact_calidad f
JOIN dim_maquina  m  ON m.id_maquina = f.id_maquina
JOIN dim_linea    l  ON l.id_linea   = m.id_linea
JOIN dim_planta   pl ON pl.id_planta = l.id_planta
JOIN dim_producto pr ON pr.id_producto = f.id_producto
JOIN dim_familia  fa ON fa.id_familia = pr.id_familia
JOIN dim_turno    t  ON t.id_turno   = f.id_turno
JOIN dim_tiempo   ti ON ti.id_tiempo = f.id_tiempo
LEFT JOIN dim_causa c ON c.id_causa  = f.id_causa;
