-- ============================================================================
-- 04_iot.sql — Validación de las reglas IoT (Constitución §7.1 / G5).
-- Uso:
--   docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/04_iot.sql
-- Todos los chequeos deben devolver estado = OK.
-- ============================================================================

\pset pager off

\echo '>>> 1. La cuarentena existe y tiene el grano esperado'
SELECT
    CASE
        WHEN COUNT(*) = 5 THEN 'OK'
        ELSE 'FALLA: columnas inesperadas'
    END AS estado,
    'fact_evento_rechazado' AS objeto,
    COUNT(*)::text AS detalle
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'fact_evento_rechazado'
  AND column_name IN (
      'id_rechazo', 'source_system', 'source_event_id', 'motivo', 'payload'
  );

\echo '>>> 2. Ningún evento aceptado está fuera del rango válido'
WITH rango AS (
    SELECT MIN(event_time) AS inicio
    FROM fact_evento
    WHERE run_id LIKE 'hist-%'
)
SELECT
    CASE
        WHEN COUNT(*) = 0 THEN 'OK'
        ELSE 'FALLA: ' || COUNT(*) || ' eventos fuera de rango'
    END AS estado,
    'fact_evento' AS objeto,
    COALESCE(COUNT(*)::text, '0') AS detalle
FROM fact_evento e
CROSS JOIN rango r
WHERE e.event_time > NOW() + INTERVAL '5 minutes'
   OR (r.inicio IS NOT NULL AND e.event_time < r.inicio - INTERVAL '1 day');

\echo '>>> 3. La vista de calidad de señal cubre todas las máquinas con producción'
WITH esperadas AS (
    SELECT COUNT(DISTINCT id_maquina) AS n FROM fact_produccion
), vistas AS (
    SELECT COUNT(DISTINCT id_maquina) AS n FROM v_calidad_senal_iot
)
SELECT
    CASE WHEN v.n = e.n THEN 'OK' ELSE 'FALLA' END AS estado,
    'v_calidad_senal_iot cobertura' AS objeto,
    v.n || '/' || e.n || ' máquinas' AS detalle
FROM esperadas e, vistas v;

\echo '>>> 4. Los estados de señal son válidos y no hay métricas negativas'
SELECT
    CASE WHEN COUNT(*) = 0 THEN 'OK' ELSE 'FALLA' END AS estado,
    'v_calidad_senal_iot estados' AS objeto,
    COALESCE(COUNT(*)::text, '0') AS detalle
FROM v_calidad_senal_iot
WHERE estado_senal NOT IN ('ok', 'incompleta', 'sin_datos')
   OR lecturas < 0
   OR lecturas_esperadas < 0
   OR lecturas_faltantes < 0
   OR max_gap_min < 0;

\echo '>>> 5. La cadencia de 15 min se informa sin ocultar la diferencia'
SELECT
    CASE
        WHEN COUNT(*) FILTER (
            WHERE max_gap_min <= 15 AND cumple_cadencia_15min = false
        ) = 0
        AND COUNT(*) FILTER (
            WHERE max_gap_min > 15 AND cumple_cadencia_15min = true
        ) = 0
        THEN 'OK'
        ELSE 'FALLA: indicador de cadencia incoherente'
    END AS estado,
    'v_calidad_senal_iot cadencia 15 min' AS objeto,
    COUNT(*) FILTER (WHERE cumple_cadencia_15min) || '/' || COUNT(*)
        || ' días cumplen 15 min' AS detalle
FROM v_calidad_senal_iot;
