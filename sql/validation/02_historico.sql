-- ============================================================================
-- 02_historico.sql — Validaciones del histórico sintético (incremento 003)
-- Resultado esperado: todas las filas con incidencias = 0 y estado 'OK'.
-- Criterios: AC-301 a AC-307 de specs/003-generador-historico/spec.md.
-- ============================================================================

WITH checks AS (
    -- --- Volumen y cobertura ---------------------------------------------
    SELECT 'AC-301: fact_evento >= 200.000 eventos de origen' AS chequeo,
           (SELECT count(*) FROM fact_evento)::bigint AS valor,
           CASE WHEN (SELECT count(*) FROM fact_evento) >= 200000 THEN 0 ELSE 1 END::bigint
               AS incidencias

    UNION ALL
    SELECT 'AC-302: fact_produccion cubre exactamente 180 días',
           (SELECT count(DISTINCT id_tiempo) FROM fact_produccion)::bigint,
           abs((SELECT count(DISTINCT id_tiempo) FROM fact_produccion) - 180)::bigint

    -- --- Coherencia temporal ---------------------------------------------
    UNION ALL
    SELECT 'AC-303: fact_produccion con fin anterior al inicio',
           count(*)::bigint, count(*)::bigint
    FROM fact_produccion
    WHERE fin_at < inicio_at

    UNION ALL
    SELECT 'AC-303: fact_parada con fin anterior al inicio',
           count(*)::bigint, count(*)::bigint
    FROM fact_parada
    WHERE fin_at IS NOT NULL AND fin_at < inicio_at

    UNION ALL
    SELECT 'AC-303: fact_mantenimiento con fin anterior al inicio',
           count(*)::bigint, count(*)::bigint
    FROM fact_mantenimiento
    WHERE fin_at IS NOT NULL AND fin_at < inicio_at

    -- --- Cantidades y tiempos --------------------------------------------
    UNION ALL
    SELECT 'AC-304: conteos negativos o inconsistentes en fact_produccion',
           count(*)::bigint, count(*)::bigint
    FROM fact_produccion
    WHERE total_count < 0 OR good_count < 0 OR scrap_count < 0
       OR good_count > total_count OR scrap_count > total_count

    UNION ALL
    SELECT 'AC-304: tiempos negativos en fact_produccion',
           count(*)::bigint, count(*)::bigint
    FROM fact_produccion
    WHERE tiempo_calendario_min < 0 OR tiempo_planificado_min < 0
       OR downtime_planificado_min < 0 OR tiempo_operativo_min < 0
       OR downtime_no_planificado_min < 0 OR energia_kwh < 0

    UNION ALL
    SELECT 'fact_produccion: desbalance de tiempos',
           count(*)::bigint, count(*)::bigint
    FROM fact_produccion
    WHERE tiempo_planificado_min + downtime_planificado_min <> tiempo_calendario_min
       OR tiempo_operativo_min + downtime_no_planificado_min <> tiempo_planificado_min

    UNION ALL
    SELECT 'fact_mantenimiento: duración o costo negativos',
           count(*)::bigint, count(*)::bigint
    FROM fact_mantenimiento
    WHERE duracion_min < 0 OR costo_estimado_usd < 0

    UNION ALL
    SELECT 'fact_calidad: conteos inconsistentes',
           count(*)::bigint, count(*)::bigint
    FROM fact_calidad
    WHERE unidades_inspeccionadas < 0 OR unidades_buenas < 0
       OR unidades_defectuosas < 0 OR unidades_retrabajo < 0
       OR unidades_buenas + unidades_defectuosas > unidades_inspeccionadas
       OR unidades_retrabajo > unidades_inspeccionadas

    -- --- Claves huérfanas ------------------------------------------------
    UNION ALL
    SELECT 'AC-307: fact_produccion -> dim_orden huérfana',
           count(*)::bigint, count(*)::bigint
    FROM fact_produccion f
    LEFT JOIN dim_orden o ON o.id_orden = f.id_orden
    WHERE o.id_orden IS NULL

    UNION ALL
    SELECT 'AC-307: fact_produccion -> dim_maquina huérfana',
           count(*)::bigint, count(*)::bigint
    FROM fact_produccion f
    LEFT JOIN dim_maquina m ON m.id_maquina = f.id_maquina
    WHERE m.id_maquina IS NULL

    UNION ALL
    SELECT 'AC-307: fact_parada -> dim_maquina huérfana',
           count(*)::bigint, count(*)::bigint
    FROM fact_parada f
    LEFT JOIN dim_maquina m ON m.id_maquina = f.id_maquina
    WHERE m.id_maquina IS NULL

    UNION ALL
    SELECT 'AC-307: fact_parada -> dim_causa huérfana',
           count(*)::bigint, count(*)::bigint
    FROM fact_parada f
    LEFT JOIN dim_causa c ON c.id_causa = f.id_causa
    WHERE c.id_causa IS NULL

    UNION ALL
    SELECT 'AC-307: fact_parada -> fact_mantenimiento huérfana',
           count(*)::bigint, count(*)::bigint
    FROM fact_parada f
    LEFT JOIN fact_mantenimiento m ON m.id_mantenimiento = f.id_mantenimiento
    WHERE f.id_mantenimiento IS NOT NULL AND m.id_mantenimiento IS NULL

    UNION ALL
    SELECT 'AC-307: fact_calidad -> dim_producto huérfana',
           count(*)::bigint, count(*)::bigint
    FROM fact_calidad f
    LEFT JOIN dim_producto p ON p.id_producto = f.id_producto
    WHERE p.id_producto IS NULL

    UNION ALL
    SELECT 'AC-307: fact_evento -> dim_maquina huérfana',
           count(*)::bigint, count(*)::bigint
    FROM fact_evento f
    LEFT JOIN dim_maquina m ON m.id_maquina = f.id_maquina
    WHERE f.id_maquina IS NOT NULL AND m.id_maquina IS NULL

    -- --- Grano y reglas de clasificación ---------------------------------
    UNION ALL
    SELECT 'fact_produccion: duplicados de grano (orden+máquina+turno+día)',
           count(*)::bigint, count(*)::bigint
    FROM (
        SELECT id_orden, id_maquina, id_turno, id_tiempo
        FROM fact_produccion
        GROUP BY id_orden, id_maquina, id_turno, id_tiempo
        HAVING count(*) > 1
    ) d

    UNION ALL
    SELECT 'fact_evento: duplicados de (source_system, source_event_id)',
           count(*)::bigint, count(*)::bigint
    FROM (
        SELECT source_system, source_event_id
        FROM fact_evento
        GROUP BY source_system, source_event_id
        HAVING count(*) > 1
    ) e

    UNION ALL
    SELECT 'Regla G6: microparada con duración >= 5 min',
           count(*)::bigint, count(*)::bigint
    FROM fact_parada
    WHERE es_microparada AND duracion_min >= 5

    UNION ALL
    SELECT 'Regla G6: parada planificada marcada como microparada',
           count(*)::bigint, count(*)::bigint
    FROM fact_parada
    WHERE es_planificada AND es_microparada

    UNION ALL
    SELECT 'Regla G6: parada corta sin CMMS no clasificada como microparada',
           count(*)::bigint, count(*)::bigint
    FROM fact_parada
    WHERE NOT es_planificada AND NOT es_microparada
      AND duracion_min < 5 AND id_mantenimiento IS NULL

    UNION ALL
    SELECT 'Clasificación: es_planificada distinto de dim_causa.es_planificada',
           count(*)::bigint, count(*)::bigint
    FROM fact_parada f
    JOIN dim_causa c ON c.id_causa = f.id_causa
    WHERE f.es_planificada <> c.es_planificada

    UNION ALL
    SELECT 'fact_evento: eventos de transición de estado',
           count(*)::bigint,
           CASE WHEN count(*) > 0 THEN 0 ELSE 1 END::bigint
    FROM fact_evento
    WHERE tipo_evento = 'transicion_estado'
)
SELECT chequeo,
       valor,
       incidencias,
       CASE WHEN incidencias = 0 THEN 'OK' ELSE 'REVISAR' END AS estado
FROM checks
ORDER BY estado DESC, chequeo;
