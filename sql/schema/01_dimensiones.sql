-- ============================================================================
-- 01_dimensiones.sql — Dimensiones conformadas
-- Idempotente: puede ejecutarse varias veces sin duplicar objetos ni filas.
-- Jerarquías: Planta -> Línea -> Máquina  y  Familia -> Producto
-- ============================================================================

CREATE TABLE IF NOT EXISTS dim_planta (
    id_planta  smallint PRIMARY KEY,
    codigo     text NOT NULL UNIQUE,
    nombre     text NOT NULL,
    ciudad     text,
    pais       text NOT NULL DEFAULT 'Argentina'
);

CREATE TABLE IF NOT EXISTS dim_linea (
    id_linea   smallint PRIMARY KEY,
    id_planta  smallint NOT NULL REFERENCES dim_planta (id_planta),
    codigo     text NOT NULL UNIQUE,
    nombre     text NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_maquina (
    id_maquina  integer PRIMARY KEY,
    id_linea    smallint NOT NULL REFERENCES dim_linea (id_linea),
    codigo      text NOT NULL UNIQUE,
    nombre      text NOT NULL,
    tipo        text NOT NULL,
    criticidad  text NOT NULL CHECK (criticidad IN ('A', 'B', 'C')),
    fabricante  text,
    modelo      text,
    fecha_alta  date,
    activa      boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS dim_familia (
    id_familia  smallint PRIMARY KEY,
    codigo      text NOT NULL UNIQUE,
    nombre      text NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_producto (
    id_producto   integer PRIMARY KEY,
    id_familia    smallint NOT NULL REFERENCES dim_familia (id_familia),
    codigo        text NOT NULL UNIQUE,
    nombre        text NOT NULL,
    unidad_medida text NOT NULL DEFAULT 'unidad'
);

CREATE TABLE IF NOT EXISTS dim_turno (
    id_turno         smallint PRIMARY KEY,
    codigo           text NOT NULL UNIQUE,
    nombre           text NOT NULL,
    hora_inicio      time NOT NULL,
    hora_fin         time NOT NULL,
    duracion_min     smallint NOT NULL CHECK (duracion_min > 0),
    cruza_medianoche boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS dim_causa (
    id_causa       integer PRIMARY KEY,
    codigo         text NOT NULL UNIQUE,
    descripcion    text NOT NULL,
    categoria      text NOT NULL,
    es_planificada boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS dim_tecnico (
    id_tecnico   integer PRIMARY KEY,
    codigo       text NOT NULL UNIQUE,
    nombre       text NOT NULL,
    especialidad text NOT NULL,
    activo       boolean NOT NULL DEFAULT true
);

-- Grano: un día calendario. id_tiempo = YYYYMMDD.
CREATE TABLE IF NOT EXISTS dim_tiempo (
    id_tiempo     integer PRIMARY KEY,
    fecha         date NOT NULL UNIQUE,
    anio          smallint NOT NULL,
    trimestre     smallint NOT NULL CHECK (trimestre BETWEEN 1 AND 4),
    mes           smallint NOT NULL CHECK (mes BETWEEN 1 AND 12),
    dia           smallint NOT NULL CHECK (dia BETWEEN 1 AND 31),
    semana_iso    smallint NOT NULL CHECK (semana_iso BETWEEN 1 AND 53),
    dia_semana    smallint NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),
    nombre_dia    text NOT NULL,
    es_fin_semana boolean NOT NULL,
    anio_mes      text NOT NULL
);

-- La orden es una dimensión degenerada ampliada: permite filtrar por producto
-- sin duplicar medidas y conserva la cantidad planificada.
CREATE TABLE IF NOT EXISTS dim_orden (
    id_orden             bigint PRIMARY KEY,
    codigo_orden         text NOT NULL UNIQUE,
    id_producto          integer NOT NULL REFERENCES dim_producto (id_producto),
    cantidad_planificada integer NOT NULL CHECK (cantidad_planificada >= 0),
    fecha_plan           date NOT NULL,
    estado               text NOT NULL DEFAULT 'planificada'
                         CHECK (estado IN ('planificada', 'en_curso', 'cerrada', 'cancelada')),
    -- Clave compuesta que permite a fact_produccion validar que el producto
    -- del hecho coincide con el producto de la orden.
    CONSTRAINT dim_orden_orden_producto_uq UNIQUE (id_orden, id_producto)
);
