-- ============================================================================
-- apply_all.sql — Aplica el esquema completo en orden.
-- Uso:
--   docker compose exec -T db psql -U metalinova -d metalinova -f /sql/apply_all.sql
-- Idempotente: puede ejecutarse varias veces.
-- ============================================================================

\set ON_ERROR_STOP on

\echo '>>> 01 dimensiones'
\i /sql/schema/01_dimensiones.sql

\echo '>>> 02 hechos'
\i /sql/schema/02_hechos.sql

\echo '>>> 03 comentarios de grano'
\i /sql/schema/03_comentarios.sql

\echo '>>> 04 catálogo de referencia'
\i /sql/schema/04_catalogo_referencia.sql

\echo '>>> 05 índices'
\i /sql/indexes/01_indices.sql

\echo '>>> 06 vistas base'
\i /sql/views/01_vistas_base.sql

\echo '>>> 07 vistas KPI base'
\i /sql/views/02_kpi_base.sql

\echo '>>> 08 KPI OEE'
\i /sql/views/03_kpi_oee.sql

\echo '>>> 09 KPI mantenimiento'
\i /sql/views/04_kpi_mantenimiento.sql

\echo '>>> 10 KPI calidad y energía'
\i /sql/views/05_kpi_calidad_energia.sql

\echo '>>> 11 KPI confiabilidad (apoyo)'
\i /sql/views/06_kpi_confiabilidad.sql

\echo '>>> 12 Loss Tree'
\i /sql/views/07_loss_tree.sql

\echo '>>> 13 alerta de máquina crítica'
\i /sql/views/08_alerta_maquina_critica.sql

\echo '>>> esquema aplicado'
