-- ============================================================================
-- 02_hechos.sql — Tablas de hechos
-- El grano de cada tabla está documentado en 03_comentarios.sql.
-- Idempotente: CREATE TABLE IF NOT EXISTS con constraints declaradas inline.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- fact_mantenimiento — una fila por orden/intervención de mantenimiento.
-- Se crea antes de fact_parada porque esta última puede referenciarla.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_mantenimiento (
    id_mantenimiento     bigserial PRIMARY KEY,
    codigo_orden_trabajo text NOT NULL UNIQUE,
    id_maquina           integer NOT NULL REFERENCES dim_maquina (id_maquina),
    id_tecnico           integer NOT NULL REFERENCES dim_tecnico (id_tecnico),
    id_causa             integer NOT NULL REFERENCES dim_causa (id_causa),
    id_turno             smallint NOT NULL REFERENCES dim_turno (id_turno),
    id_tiempo            integer NOT NULL REFERENCES dim_tiempo (id_tiempo),
    tipo                 text NOT NULL
                         CHECK (tipo IN ('preventivo', 'correctivo', 'predictivo', 'mejora')),
    inicio_at            timestamptz NOT NULL,
    fin_at               timestamptz,
    duracion_min         integer NOT NULL CHECK (duracion_min >= 0),
    costo_estimado_usd   numeric(12, 2) NOT NULL DEFAULT 0
                         CHECK (costo_estimado_usd >= 0),
    estado               text NOT NULL DEFAULT 'cerrada'
                         CHECK (estado IN ('abierta', 'cerrada')),
    CONSTRAINT fact_mantenimiento_fechas_ck
        CHECK (fin_at IS NULL OR fin_at >= inicio_at)
);

-- ---------------------------------------------------------------------------
-- fact_parada — una fila por episodio de parada.
-- id_tiempo corresponde a la fecha de inicio del episodio.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_parada (
    id_parada        bigserial PRIMARY KEY,
    id_maquina       integer NOT NULL REFERENCES dim_maquina (id_maquina),
    id_turno         smallint NOT NULL REFERENCES dim_turno (id_turno),
    id_tiempo        integer NOT NULL REFERENCES dim_tiempo (id_tiempo),
    id_causa         integer NOT NULL REFERENCES dim_causa (id_causa),
    id_mantenimiento bigint REFERENCES fact_mantenimiento (id_mantenimiento),
    inicio_at        timestamptz NOT NULL,
    fin_at           timestamptz,
    duracion_min     integer NOT NULL CHECK (duracion_min >= 0),
    es_planificada   boolean NOT NULL,
    es_microparada   boolean NOT NULL,
    causa_detalle    text,
    -- Dos paradas de la misma máquina no pueden empezar en el mismo instante.
    CONSTRAINT fact_parada_maquina_inicio_uq UNIQUE (id_maquina, inicio_at),
    CONSTRAINT fact_parada_fechas_ck
        CHECK (fin_at IS NULL OR fin_at >= inicio_at),
    CONSTRAINT fact_parada_planificada_micro_ck
        CHECK (NOT (es_planificada AND es_microparada))
);

-- ---------------------------------------------------------------------------
-- fact_produccion — una fila por orden + máquina + turno + día.
-- La FK compuesta garantiza que el producto del hecho sea el de la orden.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_produccion (
    id_produccion               bigserial PRIMARY KEY,
    id_orden                    bigint NOT NULL,
    id_maquina                  integer NOT NULL REFERENCES dim_maquina (id_maquina),
    id_producto                 integer NOT NULL,
    id_turno                    smallint NOT NULL REFERENCES dim_turno (id_turno),
    id_tiempo                   integer NOT NULL REFERENCES dim_tiempo (id_tiempo),
    inicio_at                   timestamptz NOT NULL,
    fin_at                      timestamptz NOT NULL,
    tiempo_calendario_min       integer NOT NULL CHECK (tiempo_calendario_min >= 0),
    tiempo_planificado_min      integer NOT NULL CHECK (tiempo_planificado_min >= 0),
    downtime_planificado_min    integer NOT NULL CHECK (downtime_planificado_min >= 0),
    tiempo_operativo_min        integer NOT NULL CHECK (tiempo_operativo_min >= 0),
    downtime_no_planificado_min integer NOT NULL CHECK (downtime_no_planificado_min >= 0),
    total_count                 integer NOT NULL CHECK (total_count >= 0),
    good_count                  integer NOT NULL CHECK (good_count >= 0),
    scrap_count                 integer NOT NULL CHECK (scrap_count >= 0),
    ciclo_ideal_segundos        numeric(10, 3) NOT NULL CHECK (ciclo_ideal_segundos > 0),
    energia_kwh                 numeric(12, 4) NOT NULL CHECK (energia_kwh >= 0),
    CONSTRAINT fact_produccion_orden_turno_uq
        UNIQUE (id_orden, id_maquina, id_turno, id_tiempo),
    CONSTRAINT fact_produccion_orden_producto_fk
        FOREIGN KEY (id_orden, id_producto) REFERENCES dim_orden (id_orden, id_producto),
    CONSTRAINT fact_produccion_fechas_ck
        CHECK (fin_at >= inicio_at),
    CONSTRAINT fact_produccion_calendario_ck
        CHECK (tiempo_planificado_min + downtime_planificado_min = tiempo_calendario_min),
    CONSTRAINT fact_produccion_runtime_ck
        CHECK (tiempo_operativo_min + downtime_no_planificado_min = tiempo_planificado_min),
    CONSTRAINT fact_produccion_counts_ck
        CHECK (good_count <= total_count AND scrap_count <= total_count)
);

-- ---------------------------------------------------------------------------
-- fact_calidad — una fila por inspección/lote.
-- unidades_retrabajo es un subconjunto de las unidades procesadas que requirió
-- retrabajo; permite calcular FPY = (procesadas - retrabajo) / procesadas.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_calidad (
    id_calidad              bigserial PRIMARY KEY,
    codigo_inspeccion       text NOT NULL UNIQUE,
    codigo_lote             text NOT NULL,
    id_maquina              integer NOT NULL REFERENCES dim_maquina (id_maquina),
    id_producto             integer NOT NULL REFERENCES dim_producto (id_producto),
    id_turno                smallint NOT NULL REFERENCES dim_turno (id_turno),
    id_tiempo               integer NOT NULL REFERENCES dim_tiempo (id_tiempo),
    id_causa                integer REFERENCES dim_causa (id_causa),
    inspeccion_at           timestamptz NOT NULL,
    unidades_inspeccionadas integer NOT NULL CHECK (unidades_inspeccionadas >= 0),
    unidades_buenas         integer NOT NULL CHECK (unidades_buenas >= 0),
    unidades_defectuosas    integer NOT NULL CHECK (unidades_defectuosas >= 0),
    unidades_retrabajo      integer NOT NULL DEFAULT 0 CHECK (unidades_retrabajo >= 0),
    es_retrabajo            boolean NOT NULL DEFAULT false,
    CONSTRAINT fact_calidad_conteos_ck
        CHECK (unidades_buenas + unidades_defectuosas <= unidades_inspeccionadas),
    CONSTRAINT fact_calidad_retrabajo_ck
        CHECK (unidades_retrabajo <= unidades_inspeccionadas)
);

-- ---------------------------------------------------------------------------
-- fact_evento — aterrizaje de eventos crudos de origen.
-- La clave única (source_system, source_event_id) garantiza idempotencia.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_evento (
    id_evento       bigserial PRIMARY KEY,
    source_system   text NOT NULL
                    CHECK (source_system IN ('iot', 'scada', 'mes', 'cmms', 'erp', 'calidad', 'turnos')),
    source_event_id text NOT NULL,
    tipo_evento     text NOT NULL
                    CHECK (tipo_evento IN ('transicion_estado', 'lectura_proceso',
                                           'orden_produccion', 'parada',
                                           'mantenimiento', 'inspeccion')),
    id_maquina      integer REFERENCES dim_maquina (id_maquina),
    event_time      timestamptz NOT NULL,
    generated_at    timestamptz NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    run_id          text,
    estado          text,
    temperatura_c   numeric(6, 2) CHECK (temperatura_c IS NULL OR temperatura_c BETWEEN -20 AND 150),
    energia_kwh     numeric(12, 4) CHECK (energia_kwh IS NULL OR energia_kwh >= 0),
    payload         jsonb,
    CONSTRAINT fact_evento_source_uq UNIQUE (source_system, source_event_id)
);

-- ---------------------------------------------------------------------------
-- fact_evento_rechazado — cuarentena de eventos inválidos.
-- Nunca se descarta un evento en silencio: queda aquí con su motivo.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_evento_rechazado (
    id_rechazo      bigserial PRIMARY KEY,
    source_system   text,
    source_event_id text,
    motivo          text NOT NULL,
    payload         jsonb,
    recibido_at     timestamptz NOT NULL DEFAULT now()
);
