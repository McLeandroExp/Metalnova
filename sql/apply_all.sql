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

\echo '>>> esquema aplicado'
