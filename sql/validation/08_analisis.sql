-- ============================================================================
-- 08_analisis.sql — Controles estructurales del análisis estadístico (008)
--
-- Verifica que la base sobre la que se ejecuta `analyze_data.py` mantiene la
-- forma esperada: cobertura, granularidad, fórmulas, nulos, rangos y señal.
-- No sustituye a `validate_analysis.py`, que compara SQL contra los CSV.
--
-- Resultado esperado: todas las filas con incidencias = 0 y estado 'OK'.
-- Ventana canónica: 2026-04-22 → 2026-10-18 (180 días).
-- ============================================================================

\echo 'Análisis 008 — estructura, cobertura y señal'

WITH o AS (
    SELECT count(*)::numeric AS n,
           count(DISTINCT id_maquina)::numeric AS maquinas,
           count(DISTINCT fecha)::numeric AS dias,
           avg(disponibilidad) AS a_media,
           stddev_samp(disponibilidad) AS a_sd,
           avg(oee) AS oee_media,
           stddev_samp(oee) AS oee_sd,
           corr(oee, rendimiento) AS r_rendimiento,
           corr(oee, calidad) AS r_calidad,
           corr(oee, energia_por_unidad_buena) AS r_energia,
           corr(oee, downtime_no_planificado_pct) AS r_downtime,
           count(*) FILTER (
               WHERE disponibilidad IS NULL OR rendimiento IS NULL
                  OR calidad IS NULL OR oee IS NULL
           )::numeric AS nulos,
           count(*) FILTER (
               WHERE round((disponibilidad * rendimiento * calidad)::numeric, 6) <> oee
           )::numeric AS formula_mal,
           count(*) FILTER (WHERE oee < 0 OR oee > 1)::numeric AS fuera_rango
    FROM v_kpi_oee_maquina_dia
    WHERE fecha BETWEEN DATE '2026-04-22' AND DATE '2026-10-18'
), t AS (
    SELECT count(*)::numeric AS n,
           count(DISTINCT (fecha, id_maquina, id_turno))::numeric AS claves
    FROM v_kpi_oee_maquina_turno
    WHERE fecha BETWEEN DATE '2026-04-22' AND DATE '2026-10-18'
), p AS (
    SELECT count(*)::numeric AS n,
           count(DISTINCT (fecha, planta_codigo))::numeric AS claves
    FROM v_kpi_oee_planta_dia
    WHERE fecha BETWEEN DATE '2026-04-22' AND DATE '2026-10-18'
), s AS (
    SELECT count(*)::numeric AS n,
           max(duracion_min)::numeric AS dur_max,
           count(*) FILTER (WHERE duracion_min < 0)::numeric AS negativas
    FROM v_parada_consolidada
    WHERE id_tiempo BETWEEN 20260422 AND 20261018
      AND causa_detalle NOT LIKE 'Ingesta 004:%'
), e AS (
    SELECT count(*) FILTER (WHERE run_id LIKE 'hist-%')::numeric AS n,
           count(*) FILTER (WHERE run_id LIKE 'sim-%')::numeric AS sim
    FROM fact_evento
), temp AS (
    SELECT count(*) FILTER (WHERE temperatura_c IS NOT NULL)::numeric AS n,
           count(*) FILTER (WHERE temperatura_c < -20 OR temperatura_c > 150)::numeric AS fuera
    FROM fact_evento
    WHERE run_id LIKE 'hist-%'
), rech AS (
    SELECT count(*)::numeric AS n FROM fact_evento_rechazado
)
SELECT 'Cobertura: 180 días distintos' AS chequeo,
       o.dias AS valor,
       CASE WHEN o.dias = 180 THEN 0 ELSE 1 END::numeric AS incidencias
FROM o
UNION ALL
SELECT 'Cobertura: 52 máquinas distintas', o.maquinas,
       CASE WHEN o.maquinas = 52 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Granularidad: máquina-día = máquinas × días', o.n,
       CASE WHEN o.n = o.maquinas * o.dias THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Granularidad: máquina-turno = máquina-día × 3', t.n,
       CASE WHEN t.n = (SELECT n * 3 FROM o WHERE o.n > 0) THEN 0 ELSE 1 END
FROM t
UNION ALL
SELECT 'Granularidad: planta-día = 3 plantas × 180 días', p.n,
       CASE WHEN p.n = 3 * 180 THEN 0 ELSE 1 END
FROM p
UNION ALL
SELECT 'Paradas consolidadas en la ventana', s.n,
       CASE WHEN s.n > 0 THEN 0 ELSE 1 END
FROM s
UNION ALL
SELECT 'Eventos históricos (>= 200.000)', e.n,
       CASE WHEN e.n >= 200000 THEN 0 ELSE 1 END
FROM e
UNION ALL
SELECT 'Eventos sim-* separados para latencia', e.sim,
       CASE WHEN e.sim > 0 AND e.sim < 1000 THEN 0 ELSE 1 END
FROM e
UNION ALL
SELECT 'OEE = A × P × Q redondeado a 6 decimales', o.formula_mal,
       CASE WHEN o.formula_mal = 0 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Sin nulos en A, P, Q u OEE', o.nulos,
       CASE WHEN o.nulos = 0 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'OEE dentro de [0, 1]', o.fuera_rango,
       CASE WHEN o.fuera_rango = 0 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Disponibilidad media en [0,95; 1]', round(o.a_media, 4),
       CASE WHEN o.a_media BETWEEN 0.95 AND 1 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Disponibilidad en techo (sd < 0,05)', round(o.a_sd, 4),
       CASE WHEN o.a_sd < 0.05 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Correlación OEE-rendimiento en [0,9; 1]', round(o.r_rendimiento::numeric, 4),
       CASE WHEN o.r_rendimiento BETWEEN 0.9 AND 1 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Correlación OEE-calidad en [0,6; 0,9]', round(o.r_calidad::numeric, 4),
       CASE WHEN o.r_calidad BETWEEN 0.6 AND 0.9 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Correlación OEE-energía en [-0,7; -0,2]', round(o.r_energia::numeric, 4),
       CASE WHEN o.r_energia BETWEEN -0.7 AND -0.2 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Correlación OEE-downtime en [-0,6; -0,1]', round(o.r_downtime::numeric, 4),
       CASE WHEN o.r_downtime BETWEEN -0.6 AND -0.1 THEN 0 ELSE 1 END
FROM o
UNION ALL
SELECT 'Paradas: duración máxima <= 240 min', s.dur_max,
       CASE WHEN s.dur_max <= 240 THEN 0 ELSE 1 END
FROM s
UNION ALL
SELECT 'Paradas: sin duraciones negativas', s.negativas,
       CASE WHEN s.negativas = 0 THEN 0 ELSE 1 END
FROM s
UNION ALL
SELECT 'Temperatura: lecturas dentro de [-20, 150] °C', temp.fuera,
       CASE WHEN temp.fuera = 0 THEN 0 ELSE 1 END
FROM temp
UNION ALL
SELECT 'Temperatura: lecturas disponibles (> 50.000)', temp.n,
       CASE WHEN temp.n > 50000 THEN 0 ELSE 1 END
FROM temp
UNION ALL
SELECT 'Cuarentena: solo eventos de prueba (<= 10)', rech.n,
       CASE WHEN rech.n <= 10 THEN 0 ELSE 1 END
FROM rech
ORDER BY chequeo;

\echo 'Fin de los controles del análisis 008'
