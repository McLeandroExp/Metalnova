-- ============================================================================
-- 04_catalogo_referencia.sql — Catálogo estático de referencia (sintético)
-- Datos sintéticos del prototipo: 3 plantas, 6 líneas, 52 máquinas, 3 familias,
-- 12 productos, 3 turnos, 12 causas y 12 técnicos. La dimensión tiempo cubre
-- 2025-01-01 .. 2027-12-31 para no depender de la fecha de ejecución.
-- Idempotente: INSERT ... ON CONFLICT DO NOTHING.
-- ============================================================================

INSERT INTO dim_planta (id_planta, codigo, nombre, ciudad, pais) VALUES
    (1, 'P-NORTE',  'Planta Norte',  'Córdoba', 'Argentina'),
    (2, 'P-CENTRO', 'Planta Centro', 'Rosario', 'Argentina'),
    (3, 'P-SUR',    'Planta Sur',    'Mendoza', 'Argentina')
ON CONFLICT DO NOTHING;

INSERT INTO dim_linea (id_linea, id_planta, codigo, nombre) VALUES
    (1, 1, 'L1-1', 'Línea 1 — Planta Norte'),
    (2, 1, 'L1-2', 'Línea 2 — Planta Norte'),
    (3, 2, 'L2-1', 'Línea 1 — Planta Centro'),
    (4, 2, 'L2-2', 'Línea 2 — Planta Centro'),
    (5, 3, 'L3-1', 'Línea 1 — Planta Sur'),
    (6, 3, 'L3-2', 'Línea 2 — Planta Sur')
ON CONFLICT DO NOTHING;

-- 52 máquinas repartidas 9/9/9/9/8/8 por línea.
INSERT INTO dim_maquina (id_maquina, id_linea, codigo, nombre, tipo, criticidad, fabricante, modelo, fecha_alta)
SELECT
    g,
    CASE
        WHEN g <= 9  THEN 1
        WHEN g <= 18 THEN 2
        WHEN g <= 27 THEN 3
        WHEN g <= 36 THEN 4
        WHEN g <= 44 THEN 5
        ELSE 6
    END,
    'M-' || LPAD(g::text, 3, '0'),
    (ARRAY['CNC', 'Prensa', 'Inyectora', 'Soldadora', 'Rectificadora'])[1 + ((g - 1) % 5)]
        || ' ' || LPAD(g::text, 2, '0'),
    (ARRAY['CNC', 'Prensa', 'Inyectora', 'Soldadora', 'Rectificadora'])[1 + ((g - 1) % 5)],
    (ARRAY['A', 'A', 'B', 'B', 'C'])[1 + ((g - 1) % 5)],
    (ARRAY['FANUC', 'SCHULER', 'ENGEL', 'KUKA', 'STUDER'])[1 + ((g - 1) % 5)],
    'MOD-' || LPAD((((g - 1) % 5) + 1)::text, 2, '0'),
    DATE '2020-01-01' + ((g * 37) % 1800)
FROM generate_series(1, 52) AS g
ON CONFLICT DO NOTHING;

INSERT INTO dim_familia (id_familia, codigo, nombre) VALUES
    (1, 'FAM-FRE', 'Frenos'),
    (2, 'FAM-SUS', 'Suspensión'),
    (3, 'FAM-TRA', 'Transmisión')
ON CONFLICT DO NOTHING;

INSERT INTO dim_producto (id_producto, id_familia, codigo, nombre) VALUES
    (1,  1, 'PRD-001', 'Pastilla de freno'),
    (2,  1, 'PRD-002', 'Disco de freno'),
    (3,  1, 'PRD-003', 'Tambor de freno'),
    (4,  1, 'PRD-004', 'Cilindro de freno'),
    (5,  2, 'PRD-005', 'Amortiguador delantero'),
    (6,  2, 'PRD-006', 'Amortiguador trasero'),
    (7,  2, 'PRD-007', 'Rótula de suspensión'),
    (8,  2, 'PRD-008', 'Buje de barra estabilizadora'),
    (9,  3, 'PRD-009', 'Eje cardán'),
    (10, 3, 'PRD-010', 'Engranaje de transmisión'),
    (11, 3, 'PRD-011', 'Sincronizador'),
    (12, 3, 'PRD-012', 'Horquilla de cambio')
ON CONFLICT DO NOTHING;

INSERT INTO dim_turno (id_turno, codigo, nombre, hora_inicio, hora_fin, duracion_min, cruza_medianoche) VALUES
    (1, 'A', 'Turno A', TIME '06:00', TIME '14:00', 480, false),
    (2, 'B', 'Turno B', TIME '14:00', TIME '22:00', 480, false),
    (3, 'C', 'Turno C', TIME '22:00', TIME '06:00', 480, true)
ON CONFLICT DO NOTHING;

INSERT INTO dim_causa (id_causa, codigo, descripcion, categoria, es_planificada) VALUES
    (1,  'F-MEC',      'Falla mecánica',              'Falla',              false),
    (2,  'F-ELE',      'Falla eléctrica',             'Falla',              false),
    (3,  'F-HID',      'Falla hidráulica',            'Falla',              false),
    (4,  'F-NEU',      'Falla neumática',             'Falla',              false),
    (5,  'CAM-PROD',   'Cambio de producto',          'Cambio',             true),
    (6,  'AJUSTE',     'Ajuste de máquina',           'Ajuste',             false),
    (7,  'FALTA-MAT',  'Falta de material',           'Logística',          false),
    (8,  'MICRO',      'Microparada',                 'Microparada',        false),
    (9,  'MANT-PREV',  'Mantenimiento preventivo',    'Mantenimiento',      true),
    (10, 'CALIDAD',    'Parada por calidad',          'Calidad',            false),
    (11, 'SETUP',      'Setup inicial de turno',      'Cambio',             true),
    (12, 'OTRO',       'Otra causa',                  'Otro',               false)
ON CONFLICT DO NOTHING;

INSERT INTO dim_tecnico (id_tecnico, codigo, nombre, especialidad) VALUES
    (1,  'TEC-001', 'Técnico 01', 'Mecánica'),
    (2,  'TEC-002', 'Técnico 02', 'Eléctrica'),
    (3,  'TEC-003', 'Técnico 03', 'Automatización'),
    (4,  'TEC-004', 'Técnico 04', 'Calidad'),
    (5,  'TEC-005', 'Técnico 05', 'Mecánica'),
    (6,  'TEC-006', 'Técnico 06', 'Eléctrica'),
    (7,  'TEC-007', 'Técnico 07', 'Automatización'),
    (8,  'TEC-008', 'Técnico 08', 'Calidad'),
    (9,  'TEC-009', 'Técnico 09', 'Mecánica'),
    (10, 'TEC-010', 'Técnico 10', 'Eléctrica'),
    (11, 'TEC-011', 'Técnico 11', 'Automatización'),
    (12, 'TEC-012', 'Técnico 12', 'Calidad')
ON CONFLICT DO NOTHING;

INSERT INTO dim_tiempo (
    id_tiempo, fecha, anio, trimestre, mes, dia, semana_iso,
    dia_semana, nombre_dia, es_fin_semana, anio_mes
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::integer,
    d::date,
    EXTRACT(YEAR FROM d)::smallint,
    EXTRACT(QUARTER FROM d)::smallint,
    EXTRACT(MONTH FROM d)::smallint,
    EXTRACT(DAY FROM d)::smallint,
    EXTRACT(WEEK FROM d)::smallint,
    EXTRACT(ISODOW FROM d)::smallint,
    (ARRAY['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        [EXTRACT(ISODOW FROM d)::integer],
    EXTRACT(ISODOW FROM d)::integer >= 6,
    TO_CHAR(d, 'YYYY-MM')
FROM generate_series(DATE '2025-01-01', DATE '2027-12-31', INTERVAL '1 day') AS d
ON CONFLICT DO NOTHING;
