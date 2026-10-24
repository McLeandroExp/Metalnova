-- ============================================================================
-- 06_parada_consolidada_prueba.sql — Prueba controlada de consolidación.
--
-- Inserta dos casos ficticios y los revierte al final:
--   A) solape estricto: 10 min + 15 min con 5 min de solape => 1 episodio de
--      20 min, episodios_origen = 2, minutos_solapados = 5.
--   B) intervalos adyacentes: 10 min + 10 min con fin = inicio => 2 episodios.
--   C) mixto planificado/no planificado => 1 episodio no planificado y causa
--      del tramo no planificado.
--
-- No deja datos persistidos: termina en ROLLBACK.
-- Ejecutar solo con la base local de verificación.
-- ============================================================================

BEGIN;

INSERT INTO fact_parada (
    id_maquina, id_turno, id_tiempo, id_causa, id_mantenimiento,
    inicio_at, fin_at, duracion_min, es_planificada, es_microparada,
    causa_detalle
) VALUES
    (1, 1, 20261025, 1, NULL,
     '2026-10-25 10:00+00', '2026-10-25 10:10+00', 10, false, false,
     'PRUEBA solape A'),
    (1, 1, 20261025, 2, NULL,
     '2026-10-25 10:05+00', '2026-10-25 10:20+00', 15, false, false,
     'PRUEBA solape B'),
    (2, 1, 20261026, 1, NULL,
     '2026-10-26 10:00+00', '2026-10-26 10:10+00', 10, false, false,
     'PRUEBA adyacente A'),
    (2, 1, 20261026, 1, NULL,
     '2026-10-26 10:10+00', '2026-10-26 10:20+00', 10, false, false,
     'PRUEBA adyacente B'),
    (3, 1, 20261027, 13, NULL,
     '2026-10-27 10:00+00', '2026-10-27 10:30+00', 30, true, false,
     'PRUEBA mixta planificada'),
    (3, 1, 20261027, 1, NULL,
     '2026-10-27 10:10+00', '2026-10-27 10:20+00', 10, false, false,
     'PRUEBA mixta no planificada');

\echo 'Caso A — solape estricto (debe dar 1 episodio de 20 min, 2 orígenes y 5 min solapados)'
SELECT id_parada,
       inicio_at,
       fin_at,
       duracion_min,
       episodios_origen,
       minutos_solapados,
       id_causa,
       es_planificada,
       es_microparada
FROM v_parada_consolidada
WHERE id_maquina = 1
  AND inicio_at >= '2026-10-25 10:00+00'
ORDER BY inicio_at;

\echo 'Caso B — intervalos adyacentes (deben quedar 2 episodios de 10 min)'
SELECT id_parada,
       inicio_at,
       fin_at,
       duracion_min,
       episodios_origen,
       minutos_solapados,
       id_causa,
       es_planificada,
       es_microparada
FROM v_parada_consolidada
WHERE id_maquina = 2
  AND inicio_at >= '2026-10-26 10:00+00'
ORDER BY inicio_at;

\echo 'Caso C — mixto planificado/no planificado (debe dar 1 episodio de 30 min, no planificado, causa 1)'
SELECT id_parada,
       inicio_at,
       fin_at,
       duracion_min,
       episodios_origen,
       minutos_solapados,
       id_causa,
       es_planificada,
       es_microparada
FROM v_parada_consolidada
WHERE id_maquina = 3
  AND inicio_at >= '2026-10-27 10:00+00'
ORDER BY inicio_at;

\echo 'Caso C — clasificación en v_kpi_parada (debe ser falla, causa no planificada)'
SELECT clasificacion,
       es_falla,
       es_microparada_regla,
       causa_categoria,
       es_planificada
FROM v_kpi_parada
WHERE id_maquina = 3
  AND fecha = DATE '2026-10-27'
ORDER BY inicio_at;

\echo 'Comprobación dentro de la transacción: no debe quedar ningún solape consolidado'
SELECT count(*) AS solapes_consolidados
FROM v_parada_consolidada a
JOIN v_parada_consolidada b
  ON a.id_maquina = b.id_maquina
 AND a.id_parada < b.id_parada
 AND a.inicio_at < COALESCE(b.fin_at, 'infinity'::timestamptz)
 AND b.inicio_at < COALESCE(a.fin_at, 'infinity'::timestamptz);

ROLLBACK;

\echo 'Después del ROLLBACK no deben quedar filas de prueba'
SELECT count(*) AS filas_prueba
FROM fact_parada
WHERE causa_detalle LIKE 'PRUEBA %';
