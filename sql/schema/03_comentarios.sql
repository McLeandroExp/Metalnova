-- ============================================================================
-- 03_comentarios.sql — Documentación del grano y de las reglas en el propio esquema
-- Idempotente: COMMENT ON sobrescribe el comentario anterior.
-- ============================================================================

-- --- Dimensiones -----------------------------------------------------------
COMMENT ON TABLE dim_planta IS 'Dimensión. Grano: una planta.';
COMMENT ON TABLE dim_linea IS 'Dimensión. Grano: una línea. Jerarquía: dim_planta -> dim_linea.';
COMMENT ON TABLE dim_maquina IS 'Dimensión. Grano: una máquina. Jerarquía: dim_planta -> dim_linea -> dim_maquina.';
COMMENT ON TABLE dim_familia IS 'Dimensión. Grano: una familia de producto.';
COMMENT ON TABLE dim_producto IS 'Dimensión. Grano: un producto. Jerarquía: dim_familia -> dim_producto.';
COMMENT ON TABLE dim_turno IS 'Dimensión. Grano: un turno (A/B/C). Incluye horario y duración.';
COMMENT ON TABLE dim_causa IS 'Dimensión. Grano: una causa de parada o defecto. es_planificada indica si es parada programada.';
COMMENT ON TABLE dim_tecnico IS 'Dimensión. Grano: un técnico de mantenimiento.';
COMMENT ON TABLE dim_tiempo IS 'Dimensión. Grano: un día calendario. id_tiempo = YYYYMMDD.';
COMMENT ON TABLE dim_orden IS 'Dimensión. Grano: una orden de producción. Conserva cantidad planificada y estado.';

COMMENT ON COLUMN dim_maquina.criticidad IS 'Criticidad operacional: A (alta), B (media), C (baja).';
COMMENT ON COLUMN dim_maquina.perfil_rendimiento IS 'Perfil sintético de calibración: estandar, desgastada, critica, calidad o energia. Solo lo aplica el escenario calibracion.';
COMMENT ON COLUMN dim_causa.es_planificada IS 'true = parada planificada (mantenimiento preventivo, cambio de producto).';

-- --- Hechos ----------------------------------------------------------------
COMMENT ON TABLE fact_produccion IS
    'Hecho. Grano: una fila por id_orden + id_maquina + id_turno + id_tiempo (día). '
    'Contiene tiempos, conteos, ciclo ideal y energía. '
    'Invariantes: tiempo_planificado + downtime_planificado = tiempo_calendario; '
    'tiempo_operativo + downtime_no_planificado = tiempo_planificado.';

COMMENT ON COLUMN fact_produccion.tiempo_calendario_min IS 'Duración total del turno en minutos.';
COMMENT ON COLUMN fact_produccion.tiempo_planificado_min IS 'Tiempo de producción planificado = calendario - downtime planificado (descansos, mantenimiento programado).';
COMMENT ON COLUMN fact_produccion.tiempo_operativo_min IS 'Runtime real = tiempo planificado - downtime no planificado. Denominador de Disponibilidad.';
COMMENT ON COLUMN fact_produccion.downtime_no_planificado_min IS 'Minutos de parada no planificada, incluidas microparadas.';
COMMENT ON COLUMN fact_produccion.total_count IS 'Unidades totales producidas.';
COMMENT ON COLUMN fact_produccion.good_count IS 'Unidades buenas (incluye unidades retrabajadas que quedaron conformes).';
COMMENT ON COLUMN fact_produccion.scrap_count IS 'Unidades rechazadas.';
COMMENT ON COLUMN fact_produccion.ciclo_ideal_segundos IS 'Tiempo de ciclo ideal aplicado a la orden/máquina.';

COMMENT ON TABLE fact_parada IS
    'Hecho. Grano: un episodio de parada. id_tiempo = fecha de inicio. '
    'es_microparada se deriva de duración < 5 min y ausencia de orden CMMS.';

COMMENT ON COLUMN fact_parada.duracion_min IS 'Duración del episodio en minutos. 0 si el fin aún no se conoce.';
COMMENT ON COLUMN fact_parada.es_planificada IS 'true = parada planificada; se excluye del downtime no planificado.';
COMMENT ON COLUMN fact_parada.es_microparada IS 'true = parada breve (< 5 min) sin orden de mantenimiento asociada.';

COMMENT ON TABLE fact_mantenimiento IS
    'Hecho. Grano: una orden/intervención de mantenimiento. '
    'Base para MTTR (intervenciones cerradas) y para asociar fallas a reparaciones.';

COMMENT ON COLUMN fact_mantenimiento.tipo IS 'preventivo | correctivo | predictivo | mejora.';
COMMENT ON COLUMN fact_mantenimiento.duracion_min IS 'Tiempo total de reparación/intervención en minutos.';

COMMENT ON TABLE fact_calidad IS
    'Hecho. Grano: una inspección/lote. '
    'unidades_retrabajo es un subconjunto de las procesadas que requirió retrabajo.';

COMMENT ON COLUMN fact_calidad.es_retrabajo IS 'true si la inspección/lote requirió retrabajo.';
COMMENT ON COLUMN fact_calidad.unidades_retrabajo IS 'Unidades que requirieron retrabajo. FPY = (inspeccionadas - retrabajo) / inspeccionadas.';

COMMENT ON TABLE fact_evento IS
    'Hecho crudo. Grano: un evento de origen. '
    'Clave idempotente: (source_system, source_event_id). '
    'event_time = cuándo ocurrió; generated_at = cuándo se generó; ingested_at = cuándo se persistió.';

COMMENT ON COLUMN fact_evento.event_time IS 'Hora del evento (reloj de la fuente simulada).';
COMMENT ON COLUMN fact_evento.generated_at IS 'Hora en que el generador creó el evento.';
COMMENT ON COLUMN fact_evento.ingested_at IS 'Hora en que el evento se persistió en PostgreSQL.';

COMMENT ON TABLE fact_evento_rechazado IS
    'Cuarentena. Grano: un evento descartado. Conserva motivo y payload original.';
