-- ============================================================================
-- 08_alerta_maquina_critica.sql — Regla de excepción de máquina crítica
-- (Constitución §8). Ventana de evaluación: un turno (máquina × turno × día).
--
-- Condiciones (se emite alerta si se cumple al menos una; severidad crítica
-- si se cumplen dos o más):
--   OEE < 55 %
--   MTBF < 20 h
--   Temperatura > 85 °C durante al menos 15 min
--   Downtime no planificado > 120 min/turno
--
-- La temperatura se muestrea cada 15 min en el histórico. Se exigen al menos
-- dos lecturas > 85 °C en el turno (dos muestras consecutivas = 15 min).
-- La vista expone la evaluación completa; el informe filtra severidad <> 'sin_alerta'.
-- Idempotente: CREATE OR REPLACE VIEW.
-- ============================================================================

CREATE OR REPLACE VIEW v_alerta_maquina_critica AS
WITH turnos AS (
    SELECT
        id_maquina,
        id_turno,
        id_tiempo,
        MIN(inicio_at) AS inicio_at,
        MAX(fin_at)    AS fin_at
    FROM fact_produccion
    GROUP BY id_maquina, id_turno, id_tiempo
), temp AS (
    -- LATERAL fuerza un recorrido de índice por turno. El join plano hacía
    -- que PostgreSQL comparara todas las lecturas de una máquina contra todos
    -- sus turnos (~10,5 M de comparaciones); este plan resuelve cada turno con
    -- un rango acotado sobre ix_fact_evento_maquina_time.
    SELECT
        t.id_maquina,
        t.id_turno,
        t.id_tiempo,
        x.lecturas_temp_alta,
        x.max_temperatura_c
    FROM turnos t
    CROSS JOIN LATERAL (
        SELECT
            COUNT(*) FILTER (WHERE e.temperatura_c > prm.temperatura_umbral_c)
                AS lecturas_temp_alta,
            MAX(e.temperatura_c) AS max_temperatura_c
        FROM fact_evento e
        CROSS JOIN v_kpi_parametros prm
        WHERE e.id_maquina = t.id_maquina
          AND e.tipo_evento = 'lectura_proceso'
          AND e.event_time >= t.inicio_at
          AND e.event_time < t.fin_at
    ) x
), eval AS (
    SELECT
        m.fecha,
        m.anio_mes,
        m.id_planta,
        m.planta_codigo,
        m.id_linea,
        m.linea_codigo,
        m.id_maquina,
        m.maquina_codigo,
        m.maquina_nombre,
        m.maquina_tipo,
        m.maquina_criticidad,
        m.id_turno,
        m.turno_codigo,
        m.turno_inicio_at,
        m.id_tiempo,
        m.tiempo_operativo_h,
        m.fallas,
        m.mtbf_h,
        m.microparadas,
        m.fallas_cortas,
        m.minutos_fallas,
        m.downtime_no_planificado_min,
        m.reparaciones,
        m.mttr_min,
        o.oee,
        o.disponibilidad,
        o.rendimiento,
        o.calidad,
        COALESCE(t.lecturas_temp_alta, 0) AS lecturas_temp_alta,
        COALESCE(t.max_temperatura_c, 0)  AS max_temperatura_c,
        prm.oee_umbral,
        prm.mtbf_umbral_h,
        prm.temperatura_umbral_c,
        prm.temperatura_ventana_min,
        prm.temperatura_lecturas_min,
        prm.downtime_umbral_min,
        -- El umbral se compara con 6 decimales para evitar que un OEE
        -- exactamente igual al 55 % caiga de un lado u otro por precisión
        -- numérica (el caso aparece en la máquina crítica calibrada).
        COALESCE(ROUND(o.oee, 6) < prm.oee_umbral, false) AS cumple_oee,
        (COALESCE(m.mtbf_h, 1000000000::numeric) < prm.mtbf_umbral_h) AS cumple_mtbf,
        (COALESCE(t.lecturas_temp_alta, 0) >= prm.temperatura_lecturas_min) AS cumple_temperatura,
        (m.downtime_no_planificado_min > prm.downtime_umbral_min) AS cumple_downtime
    FROM v_kpi_mantenimiento_maquina_turno m
    LEFT JOIN v_kpi_oee_maquina_turno o
      ON o.id_maquina = m.id_maquina
     AND o.fecha = m.fecha
     AND o.id_turno = m.id_turno
    LEFT JOIN temp t
      ON t.id_maquina = m.id_maquina
     AND t.id_turno = m.id_turno
     AND t.id_tiempo = m.id_tiempo
    CROSS JOIN v_kpi_parametros prm
), calc AS (
    SELECT
        eval.*,
        ((cumple_oee)::int + (cumple_mtbf)::int
            + (cumple_temperatura)::int + (cumple_downtime)::int)
            AS condiciones_cumplidas,
        (cumple_oee OR cumple_mtbf OR cumple_temperatura OR cumple_downtime)
            AS tiene_alerta,
        (lecturas_temp_alta * temperatura_ventana_min) AS minutos_temp_alta_estimados,
        concat_ws(' | ',
            CASE WHEN cumple_oee THEN 'OEE bajo: revisar pérdida dominante con ciclo PDCA' END,
            CASE WHEN cumple_mtbf THEN 'MTBF bajo: inspección preventiva anticipada' END,
            CASE WHEN cumple_temperatura THEN 'Temperatura alta: verificar refrigeración/lubricación' END,
            CASE WHEN cumple_downtime THEN 'Downtime alto: reasignar capacidad o intervenir' END
        ) AS acciones_sugeridas,
        concat_ws(' | ',
            CASE WHEN cumple_oee OR cumple_downtime THEN 'Producción' END,
            CASE WHEN cumple_mtbf OR cumple_temperatura THEN 'Mantenimiento' END
        ) AS responsables,
        concat_ws(' | ',
            CASE WHEN cumple_oee THEN 'OEE' END,
            CASE WHEN cumple_mtbf THEN 'MTBF' END,
            CASE WHEN cumple_temperatura THEN 'Temperatura' END,
            CASE WHEN cumple_downtime THEN 'Downtime no planificado' END
        ) AS kpis_seguimiento,
        concat_ws(' | ',
            CASE WHEN cumple_oee THEN 'OEE bajo' END,
            CASE WHEN cumple_mtbf THEN 'MTBF bajo' END,
            CASE WHEN cumple_temperatura THEN 'Temperatura alta' END,
            CASE WHEN cumple_downtime THEN 'Downtime alto' END
        ) AS condiciones
    FROM eval
)
SELECT
    calc.*,
    CASE
        WHEN condiciones_cumplidas = 0 THEN 'sin_alerta'
        WHEN condiciones_cumplidas = 1 THEN 'alerta'
        ELSE 'critica'
    END AS severidad,
    (row_number() OVER (
        PARTITION BY id_maquina
        ORDER BY fecha DESC, turno_inicio_at DESC
    ) = 1) AS es_ultimo_turno_maquina
FROM calc;

-- ---------------------------------------------------------------------------
-- v_alerta_ultimo_turno — subconjunto listo para la tabla de alertas del
-- informe. Evita depender de filtros visuales en Power BI y mantiene la regla
-- en SQL (una sola definición).
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_alerta_ultimo_turno;

CREATE VIEW v_alerta_ultimo_turno AS
SELECT *
FROM v_alerta_maquina_critica
WHERE es_ultimo_turno_maquina
  AND tiene_alerta;
