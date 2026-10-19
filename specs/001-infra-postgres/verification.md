# Verificación — Incremento 001

Registrar cada prueba con su salida real. No marcar como superada sin evidencia observada.

| AC | Comando | Salida esperada | Salida observada | Fecha | Veredicto |
|---|---|---|---|---|---|
| AC-101 | `docker compose config` | sin errores | — | — | pendiente |
| AC-102 | `docker compose up --build -d` | servicios creados | — | — | pendiente |
| AC-103 | `docker compose ps` | `db ... (healthy)` | — | — | pendiente |
| AC-104 | `docker compose run --rm ingestor python src/check_connection.py` | `SELECT 1 -> 1` | — | — | pendiente |
| AC-105 | crear tabla marca → `down` → `up -d` → consultar | fila intacta | — | — | pendiente |
| AC-106 | `netstat -ano \| findstr :5432` | solo `127.0.0.1:5432` | — | — | pendiente |
| AC-107 | `git status --porcelain` | `.env` ausente | — | — | pendiente |

## Notas

- Evidencia adjunta (opcional): fragmentos de `docker compose logs db`.
- Bloqueos y decisiones que requieran autorización del usuario se anotan al pie.
