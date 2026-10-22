-- ============================================================================
-- 01_indices.sql — Índices basados en los filtros y joins reales
-- Idempotente: CREATE INDEX IF NOT EXISTS.
-- ============================================================================

-- Producción: filtros por fecha, máquina, turno y orden.
CREATE INDEX IF NOT EXISTS ix_fact_produccion_tiempo
    ON fact_produccion (id_tiempo);
CREATE INDEX IF NOT EXISTS ix_fact_produccion_maquina_tiempo
    ON fact_produccion (id_maquina, id_tiempo);
CREATE INDEX IF NOT EXISTS ix_fact_produccion_turno
    ON fact_produccion (id_turno);
CREATE INDEX IF NOT EXISTS ix_fact_produccion_orden
    ON fact_produccion (id_orden);

-- Paradas: serie temporal por máquina y análisis por causa.
CREATE INDEX IF NOT EXISTS ix_fact_parada_maquina_inicio
    ON fact_parada (id_maquina, inicio_at);
CREATE INDEX IF NOT EXISTS ix_fact_parada_inicio
    ON fact_parada (inicio_at);
CREATE INDEX IF NOT EXISTS ix_fact_parada_causa
    ON fact_parada (id_causa);
CREATE INDEX IF NOT EXISTS ix_fact_parada_no_planificada
    ON fact_parada (id_maquina, inicio_at)
    WHERE NOT es_planificada;

-- Mantenimiento: intervenciones por máquina y técnico.
CREATE INDEX IF NOT EXISTS ix_fact_mantenimiento_maquina_inicio
    ON fact_mantenimiento (id_maquina, inicio_at);
CREATE INDEX IF NOT EXISTS ix_fact_mantenimiento_tecnico
    ON fact_mantenimiento (id_tecnico);
CREATE INDEX IF NOT EXISTS ix_fact_mantenimiento_inicio
    ON fact_mantenimiento (inicio_at);

-- Calidad: inspecciones por máquina, producto y fecha.
CREATE INDEX IF NOT EXISTS ix_fact_calidad_maquina_inspeccion
    ON fact_calidad (id_maquina, inspeccion_at);
CREATE INDEX IF NOT EXISTS ix_fact_calidad_producto
    ON fact_calidad (id_producto);
CREATE INDEX IF NOT EXISTS ix_fact_calidad_tiempo
    ON fact_calidad (id_tiempo);

-- Eventos: consultas de latencia y series por máquina.
CREATE INDEX IF NOT EXISTS ix_fact_evento_maquina_time
    ON fact_evento (id_maquina, event_time);
CREATE INDEX IF NOT EXISTS ix_fact_evento_time
    ON fact_evento (event_time);
-- Lecturas de proceso para la regla de temperatura (T-616): índice parcial y
-- covering para que el LATERAL de v_alerta_maquina_critica resuelva cada turno
-- sin recorrer transiciones ni paradas.
CREATE INDEX IF NOT EXISTS ix_fact_evento_lectura_maquina_time
    ON fact_evento (id_maquina, event_time)
    INCLUDE (temperatura_c)
    WHERE tipo_evento = 'lectura_proceso';
CREATE INDEX IF NOT EXISTS ix_fact_evento_ingested
    ON fact_evento (ingested_at);

CREATE INDEX IF NOT EXISTS ix_fact_evento_rechazado_recibido
    ON fact_evento_rechazado (recibido_at);
