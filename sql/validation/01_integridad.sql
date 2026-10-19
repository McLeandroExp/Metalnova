-- ============================================================================
-- 01_integridad.sql — Validaciones de integridad del modelo
-- Devuelve una fila por chequeo con el número de incidencias.
-- Resultado esperado: todas las filas con incidencias = 0 y estado 'OK'.
-- ============================================================================

WITH checks AS (
    -- --- Grano e integridad de hechos -------------------------------------
    SELECT 'fact_produccion: duplicados de grano (orden+maquina+turno+dia)' AS chequeo,
           count(*)::bigint AS incidencias
    FROM (
        SELECT id_orden, id_maquina, id_turno, id_tiempo
        FROM fact_produccion
        GROUP BY id_orden, id_maquina, id_turno, id_tiempo
        HAVING count(*) > 1
    ) d

    UNION ALL
    SELECT 'fact_produccion: producto distinto al de la orden',
           count(*)::bigint
    FROM fact_produccion f
    JOIN dim_orden o ON o.id_orden = f.id_orden
    WHERE f.id_producto <> o.id_producto

    UNION ALL
    SELECT 'fact_produccion: fin anterior al inicio',
           count(*)::bigint
    FROM fact_produccion
    WHERE fin_at < inicio_at

    UNION ALL
    SELECT 'fact_produccion: desbalance de tiempos',
           count(*)::bigint
    FROM fact_produccion
    WHERE tiempo_planificado_min + downtime_planificado_min <> tiempo_calendario_min
       OR tiempo_operativo_min + downtime_no_planificado_min <> tiempo_planificado_min

    UNION ALL
    SELECT 'fact_produccion: good_count o scrap_count mayor que total_count',
           count(*)::bigint
    FROM fact_produccion
    WHERE good_count > total_count OR scrap_count > total_count

    UNION ALL
    SELECT 'fact_parada: fin anterior al inicio',
           count(*)::bigint
    FROM fact_parada
    WHERE fin_at IS NOT NULL AND fin_at < inicio_at

    UNION ALL
    SELECT 'fact_parada: microparada con duracion >= 5 min',
           count(*)::bigint
    FROM fact_parada
    WHERE es_microparada AND duracion_min >= 5

    UNION ALL
    SELECT 'fact_parada: planificada marcada como microparada',
           count(*)::bigint
    FROM fact_parada
    WHERE es_planificada AND es_microparada

    UNION ALL
    SELECT 'fact_mantenimiento: fin anterior al inicio',
           count(*)::bigint
    FROM fact_mantenimiento
    WHERE fin_at IS NOT NULL AND fin_at < inicio_at

    UNION ALL
    SELECT 'fact_calidad: buenas + defectuosas > inspeccionadas',
           count(*)::bigint
    FROM fact_calidad
    WHERE unidades_buenas + unidades_defectuosas > unidades_inspeccionadas

    UNION ALL
    SELECT 'fact_calidad: retrabajo > inspeccionadas',
           count(*)::bigint
    FROM fact_calidad
    WHERE unidades_retrabajo > unidades_inspeccionadas

    UNION ALL
    SELECT 'fact_evento: duplicados por (source_system, source_event_id)',
           count(*)::bigint
    FROM (
        SELECT source_system, source_event_id
        FROM fact_evento
        GROUP BY source_system, source_event_id
        HAVING count(*) > 1
    ) e

    UNION ALL
    SELECT 'fact_evento: temperatura fuera de rango',
           count(*)::bigint
    FROM fact_evento
    WHERE temperatura_c IS NOT NULL AND temperatura_c NOT BETWEEN -20 AND 150

    -- --- Claves huérfanas (las FK ya deberían impedirlas) -----------------
    UNION ALL
    SELECT 'fact_parada: máquina huérfana',
           count(*)::bigint
    FROM fact_parada f
    LEFT JOIN dim_maquina m ON m.id_maquina = f.id_maquina
    WHERE m.id_maquina IS NULL

    UNION ALL
    SELECT 'fact_produccion: máquina huérfana',
           count(*)::bigint
    FROM fact_produccion f
    LEFT JOIN dim_maquina m ON m.id_maquina = f.id_maquina
    WHERE m.id_maquina IS NULL

    UNION ALL
    SELECT 'fact_calidad: producto huérfano',
           count(*)::bigint
    FROM fact_calidad f
    LEFT JOIN dim_producto p ON p.id_producto = f.id_producto
    WHERE p.id_producto IS NULL

    UNION ALL
    SELECT 'dim_maquina: línea huérfana',
           count(*)::bigint
    FROM dim_maquina m
    LEFT JOIN dim_linea l ON l.id_linea = m.id_linea
    WHERE l.id_linea IS NULL

    -- --- Multiplicación por joins en las vistas base -----------------------
    UNION ALL
    SELECT 'v_produccion_detalle: filas distintas de fact_produccion',
           abs((SELECT count(*) FROM v_produccion_detalle)
               - (SELECT count(*) FROM fact_produccion))::bigint

    UNION ALL
    SELECT 'v_parada_detalle: filas distintas de fact_parada',
           abs((SELECT count(*) FROM v_parada_detalle)
               - (SELECT count(*) FROM fact_parada))::bigint

    UNION ALL
    SELECT 'v_mantenimiento_detalle: filas distintas de fact_mantenimiento',
           abs((SELECT count(*) FROM v_mantenimiento_detalle)
               - (SELECT count(*) FROM fact_mantenimiento))::bigint

    UNION ALL
    SELECT 'v_calidad_detalle: filas distintas de fact_calidad',
           abs((SELECT count(*) FROM v_calidad_detalle)
               - (SELECT count(*) FROM fact_calidad))::bigint
)
SELECT chequeo,
       incidencias,
       CASE WHEN incidencias = 0 THEN 'OK' ELSE 'REVISAR' END AS estado
FROM checks
ORDER BY estado DESC, chequeo;
