-- ============================================================================
-- 09_dimensiones_bi.sql — Dimensiones conformadas para el modelo de Power BI.
--
-- Las tablas normalizadas (dim_planta, dim_linea, dim_maquina, dim_producto,
-- dim_familia) siguen siendo la fuente de verdad. Estas vistas las desnormalizan
-- para que el modelo tenga una sola dimensión de máquina y una sola de producto,
-- con jerarquías Planta→Línea→Máquina y Familia→Producto.
--
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

CREATE OR REPLACE VIEW v_dim_maquina AS
SELECT
    m.id_maquina,
    m.codigo AS maquina_codigo,
    m.nombre AS maquina_nombre,
    m.tipo AS maquina_tipo,
    m.criticidad AS maquina_criticidad,
    m.fabricante,
    m.modelo,
    m.fecha_alta,
    m.activa,
    l.id_linea,
    l.codigo AS linea_codigo,
    l.nombre AS linea_nombre,
    p.id_planta,
    p.codigo AS planta_codigo,
    p.nombre AS planta_nombre,
    p.ciudad,
    p.pais,
    m.perfil_rendimiento
FROM dim_maquina m
JOIN dim_linea l  ON l.id_linea  = m.id_linea
JOIN dim_planta p ON p.id_planta = l.id_planta;

CREATE OR REPLACE VIEW v_dim_producto AS
SELECT
    pr.id_producto,
    pr.codigo AS producto_codigo,
    pr.nombre AS producto_nombre,
    pr.unidad_medida,
    f.id_familia,
    f.codigo AS familia_codigo,
    f.nombre AS familia_nombre
FROM dim_producto pr
JOIN dim_familia f ON f.id_familia = pr.id_familia;
