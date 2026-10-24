-- ============================================================================
-- 05_parada_consolidada.sql — Validaciones de la consolidación de paradas.
--
-- Invariantes de v_parada_consolidada (D-023):
--   - no contiene solapes;
--   - no inventa ni pierde episodios de origen;
--   - la unión nunca dura más que la suma bruta;
--   - duraciones, fechas y reglas G6 son coherentes.
--
-- Al final se muestra un resumen informativo: si el dataset no tiene solapes,
-- episodios y minutos crudos deben coincidir con los consolidados.
--
-- Resultado esperado: todas las filas de "checks" con incidencias = 0.
-- ============================================================================

WITH checks AS (
    -- --- Invariantes de la vista consolidada -----------------------------
    SELECT 'v_parada_consolidada: pares de episodios solapados' AS chequeo,
           count(*)::bigint AS valor,
           count(*)::bigint AS incidencias
    FROM v_parada_consolidada a
    JOIN v_parada_consolidada b
      ON a.id_maquina = b.id_maquina
     AND a.id_parada < b.id_parada
     AND a.inicio_at < COALESCE(b.fin_at, 'infinity'::timestamptz)
     AND b.inicio_at < COALESCE(a.fin_at, 'infinity'::timestamptz)

    UNION ALL
    SELECT 'v_parada_consolidada: episodios consolidados <= crudos',
           (SELECT count(*) FROM v_parada_consolidada)::bigint,
           CASE
               WHEN (SELECT count(*) FROM v_parada_consolidada)
                  <= (SELECT count(*) FROM fact_parada)
               THEN 0 ELSE 1
           END::bigint

    UNION ALL
    SELECT 'v_parada_consolidada: minutos unión <= minutos brutos',
           (SELECT sum(duracion_min) FROM v_parada_consolidada)::bigint,
           CASE
               WHEN (SELECT sum(duracion_min) FROM v_parada_consolidada)
                  <= (SELECT sum(duracion_min) FROM fact_parada)
               THEN 0 ELSE 1
           END::bigint

    UNION ALL
    SELECT 'v_parada_consolidada: cobertura exacta de ids_origen',
           count(*)::bigint,
           count(*)::bigint
    FROM (
        SELECT id_parada
        FROM fact_parada
        EXCEPT
        SELECT unnest(ids_origen)
        FROM v_parada_consolidada
        UNION ALL
        SELECT unnest(ids_origen) AS id_parada
        FROM v_parada_consolidada
        GROUP BY 1
        HAVING count(*) > 1
    ) x

    UNION ALL
    SELECT 'v_parada_consolidada: episodios_origen >= 1',
           count(*)::bigint,
           count(*)::bigint
    FROM v_parada_consolidada
    WHERE episodios_origen < 1

    UNION ALL
    SELECT 'v_parada_consolidada: episodios_origen = cardinalidad(ids_origen)',
           count(*)::bigint,
           count(*)::bigint
    FROM v_parada_consolidada
    WHERE episodios_origen <> cardinality(ids_origen)

    UNION ALL
    SELECT 'v_parada_consolidada: duración negativa',
           count(*)::bigint,
           count(*)::bigint
    FROM v_parada_consolidada
    WHERE duracion_min < 0

    UNION ALL
    SELECT 'v_parada_consolidada: fin anterior al inicio',
           count(*)::bigint,
           count(*)::bigint
    FROM v_parada_consolidada
    WHERE fin_at IS NOT NULL AND fin_at < inicio_at

    UNION ALL
    SELECT 'v_parada_consolidada: minutos solapados negativos',
           count(*)::bigint,
           count(*)::bigint
    FROM v_parada_consolidada
    WHERE minutos_solapados < 0

    UNION ALL
    SELECT 'v_parada_consolidada: planificada marcada como microparada',
           count(*)::bigint,
           count(*)::bigint
    FROM v_parada_consolidada
    WHERE es_planificada AND es_microparada

    UNION ALL
    SELECT 'v_parada_consolidada: microparada inconsistente con G6',
           count(*)::bigint,
           count(*)::bigint
    FROM v_parada_consolidada
    WHERE NOT es_planificada
      AND duracion_min < 5
      AND id_mantenimiento IS NULL
      AND NOT es_microparada

    UNION ALL
    SELECT 'v_kpi_parada: filas = v_parada_consolidada',
           (SELECT count(*) FROM v_kpi_parada)::bigint,
           abs((SELECT count(*) FROM v_kpi_parada)
               - (SELECT count(*) FROM v_parada_consolidada))::bigint

    UNION ALL
    SELECT 'v_kpi_parada: es_planificada vs causa_es_planificada',
           count(*)::bigint,
           count(*)::bigint
    FROM v_kpi_parada
    WHERE es_planificada <> causa_es_planificada
)
SELECT chequeo,
       valor,
       incidencias,
       CASE WHEN incidencias = 0 THEN 'OK' ELSE 'REVISAR' END AS estado
FROM checks
ORDER BY estado DESC, chequeo;

-- Resumen informativo: con el dataset actual (sin solapes) debe ser 0.
SELECT
    (SELECT count(*) FROM fact_parada) AS episodios_crudos,
    (SELECT count(*) FROM v_parada_consolidada) AS episodios_consolidados,
    (SELECT sum(duracion_min) FROM fact_parada) AS minutos_crudos,
    (SELECT sum(duracion_min) FROM v_parada_consolidada) AS minutos_consolidados,
    (SELECT COALESCE(sum(minutos_solapados), 0) FROM v_parada_consolidada)
        AS minutos_solapados;
