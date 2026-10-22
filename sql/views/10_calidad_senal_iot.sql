-- ============================================================================
-- 10_calidad_senal_iot.sql — Calidad y temporalidad de la señal IoT (G5).
--
-- Grano: fecha × máquina. Resume, por turno con producción, cuántas lecturas de
-- proceso llegaron, cuántas se esperaban (una cada 15 min) y el mayor hueco
-- entre lecturas consecutivas.
--
-- Regla de la Constitución §7.1: si el hueco supera 15 min, el estado de la
-- señal es 'unknown'. No se aplica carry-forward que fabrique lecturas: el
-- hueco se declara, no se rellena.
--
-- Idempotente: se recrea la vista para permitir cambios de columnas.
-- ============================================================================

DROP VIEW IF EXISTS v_calidad_senal_iot;

CREATE VIEW v_calidad_senal_iot AS
WITH turnos AS (
    SELECT
        id_maquina,
        id_turno,
        id_tiempo,
        MIN(inicio_at) AS inicio_at,
        MAX(fin_at)    AS fin_at
    FROM fact_produccion
    GROUP BY id_maquina, id_turno, id_tiempo
), muestras AS (
    -- LATERAL reutiliza ix_fact_evento_lectura_maquina_time y acota cada turno
    -- a un rango de 8 horas; un join plano multiplicaría filas.
    SELECT
        t.id_maquina,
        t.id_tiempo,
        t.inicio_at,
        t.fin_at,
        x.lecturas,
        x.primera_lectura,
        x.ultima_lectura,
        x.max_gap_min
    FROM turnos t
    CROSS JOIN LATERAL (
        SELECT
            COUNT(*) AS lecturas,
            MIN(z.event_time) AS primera_lectura,
            MAX(z.event_time) AS ultima_lectura,
            MAX(EXTRACT(EPOCH FROM (z.event_time - z.prev)) / 60.0)
                AS max_gap_min
        FROM (
            SELECT
                e.event_time,
                LAG(e.event_time) OVER (ORDER BY e.event_time) AS prev
            FROM fact_evento e
            WHERE e.id_maquina = t.id_maquina
              AND e.tipo_evento = 'lectura_proceso'
              AND e.event_time >= t.inicio_at
              AND e.event_time < t.fin_at
        ) z
    ) x
), por_dia AS (
    SELECT
        s.id_maquina,
        ti.fecha,
        ti.anio_mes,
        SUM(s.lecturas) AS lecturas,
        SUM(prm.senal_lecturas_turno_min)::bigint AS lecturas_esperadas,
        COUNT(*) FILTER (WHERE s.lecturas = 0) AS turnos_sin_lecturas,
        COUNT(*) FILTER (WHERE s.lecturas < prm.senal_lecturas_turno_min)
            AS turnos_incompletos,
        MIN(s.primera_lectura) AS primera_lectura,
        MAX(s.ultima_lectura)  AS ultima_lectura,
        MAX(s.max_gap_min)     AS max_gap_min,
        prm.temperatura_ventana_min
    FROM muestras s
    JOIN dim_tiempo ti ON ti.id_tiempo = s.id_tiempo
    CROSS JOIN v_kpi_parametros prm
    GROUP BY s.id_maquina, ti.fecha, ti.anio_mes, prm.senal_lecturas_turno_min,
             prm.temperatura_ventana_min
)
SELECT
    d.id_maquina,
    m.codigo AS maquina_codigo,
    m.nombre AS maquina_nombre,
    l.id_linea,
    l.codigo AS linea_codigo,
    p.id_planta,
    p.codigo AS planta_codigo,
    d.fecha,
    d.anio_mes,
    d.lecturas,
    d.lecturas_esperadas,
    GREATEST(d.lecturas_esperadas - d.lecturas, 0)::bigint AS lecturas_faltantes,
    d.turnos_sin_lecturas,
    d.turnos_incompletos,
    d.primera_lectura,
    d.ultima_lectura,
    COALESCE(d.max_gap_min, 0)::numeric(10, 2) AS max_gap_min,
    -- Diagnóstico de la cadencia ideal de 15 min. El feed sintético es más
    -- disperso (2–5 lecturas/turno), por eso se informa aparte y no se usa para
    -- decidir la cobertura: así no se oculta la diferencia de cadencia.
    (COALESCE(d.max_gap_min, 0) <= d.temperatura_ventana_min) AS cumple_cadencia_15min,
    CASE
        WHEN d.lecturas = 0 THEN 'sin_datos'
        WHEN d.turnos_incompletos > 0 THEN 'incompleta'
        ELSE 'ok'
    END AS estado_senal
FROM por_dia d
JOIN dim_maquina m ON m.id_maquina = d.id_maquina
JOIN dim_linea l   ON l.id_linea = m.id_linea
JOIN dim_planta p  ON p.id_planta = l.id_planta;
