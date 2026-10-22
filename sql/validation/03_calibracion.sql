-- ============================================================================
-- 03_calibracion.sql — Comprobaciones del escenario sintético `calibracion`
--
-- No sustituye a validate_data.py: comprueba que la distribución elegida para
-- el informe 006 siga dentro de las bandas documentadas. Todos los datos son
-- sintéticos. Ejecutar después de cargar el histórico calibrado.
-- ============================================================================

\echo 'Calibración 006 — bandas de OEE y outliers'

WITH b AS (
    SELECT MIN(fecha) AS mn, MAX(fecha) AS mx
    FROM v_kpi_oee_planta_dia
), p AS (
    SELECT
        planta_codigo,
        CASE
            WHEN fecha < b.mn + 30 THEN 'inicio'
            WHEN fecha >= b.mx - 29 THEN 'cierre'
        END AS periodo,
        SUM(tiempo_operativo_min) AS op,
        SUM(tiempo_planificado_min) AS tp,
        SUM(minutos_ideales) AS mi,
        SUM(good_count) AS g,
        SUM(total_count) AS tc
    FROM v_kpi_oee_planta_dia, b
    WHERE fecha < b.mn + 30 OR fecha >= b.mx - 29
    GROUP BY planta_codigo, periodo
), planta AS (
    SELECT
        periodo,
        planta_codigo,
        (mi / tp) * (g::numeric / tc) AS oee
    FROM p
), global AS (
    SELECT
        periodo,
        SUM(op) AS op,
        SUM(tp) AS tp,
        SUM(mi) AS mi,
        SUM(g) AS g,
        SUM(tc) AS tc
    FROM p
    GROUP BY periodo
), spread AS (
    SELECT periodo, MAX(oee) - MIN(oee) AS rango
    FROM planta
    GROUP BY periodo
), maquina AS (
    SELECT
        id_maquina,
        SUM(tiempo_operativo_min) AS op,
        SUM(tiempo_planificado_min) AS tp,
        SUM(minutos_ideales) AS mi,
        SUM(good_count) AS g,
        SUM(total_count) AS tc
    FROM v_kpi_oee_maquina_turno
    GROUP BY id_maquina
), maquina_oee AS (
    SELECT (mi / tp) * (g::numeric / tc) AS oee
    FROM maquina
), checks AS (
    SELECT 1 AS orden, 'OEE global inicio (30 d)' AS chequeo,
           (SELECT (mi / tp) * (g::numeric / tc) FROM global WHERE periodo = 'inicio') AS valor,
           0.765 AS limite_inf, 0.795 AS limite_sup
    UNION ALL
    SELECT 2, 'OEE global cierre (30 d)',
           (SELECT (mi / tp) * (g::numeric / tc) FROM global WHERE periodo = 'cierre'),
           0.645, 0.675
    UNION ALL
    SELECT 3, 'Dispersión entre plantas al inicio',
           (SELECT rango FROM spread WHERE periodo = 'inicio'), 0.05, 0.10
    UNION ALL
    SELECT 4, 'Dispersión entre plantas al cierre',
           (SELECT rango FROM spread WHERE periodo = 'cierre'), 0.05, 0.10
    UNION ALL
    SELECT 5, 'Máquinas con OEE < 55 %',
           (SELECT COUNT(*) FROM maquina_oee WHERE oee < 0.55)::numeric, 1, 8
    UNION ALL
    SELECT 6, 'Máquinas con OEE < 61 %',
           (SELECT COUNT(*) FROM maquina_oee WHERE oee < 0.61)::numeric, 1, 10
    UNION ALL
    SELECT 7, 'Máquinas con perfil outlier',
           (SELECT COUNT(*) FROM dim_maquina WHERE perfil_rendimiento <> 'estandar')::numeric, 6, 8
)
SELECT
    orden,
    chequeo,
    ROUND(valor, 4) AS valor,
    limite_inf,
    limite_sup,
    CASE
        WHEN valor BETWEEN limite_inf AND limite_sup THEN 'OK'
        ELSE 'FALLA'
    END AS estado
FROM checks
ORDER BY orden;
