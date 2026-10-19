# Verificación — Incremento 001

Fecha de las pruebas: 2026-10-18 (hora local) / 2026-10-19 UTC.
Entorno: Windows 11, 8 GB, Docker Desktop 29.4.0, Docker Compose v5.1.1, motor WSL2 ~3,7 GB.

| AC | Comando | Salida esperada | Salida observada | Veredicto |
|---|---|---|---|---|
| AC-101 | `docker compose config` | sin errores | configuración renderizada correctamente (services, networks, volumes) | **superada** |
| AC-102 | `docker compose up --build -d` | servicios creados | `Container metalnova_db Started` | **superada** |
| AC-103 | `docker compose ps` | `db healthy` | `metalnova_db  Up (healthy)  127.0.0.1:5432->5432/tcp` | **superada** |
| AC-104 | `docker compose run --rm ingestor python src/check_connection.py` | `SELECT 1 -> 1` | `SELECT 1 -> 1` · `Base: metalinova` · `Servidor: PostgreSQL 16.4` · `Conexión OK` | **superada** |
| AC-105 | crear marca → `down` → `up -d` → consultar | fila intacta | `filas=1` tras reinicio | **superada** |
| AC-106 | `netstat -ano \| findstr :5432` | solo loopback | `TCP 127.0.0.1:5432 ... LISTENING` | **superada** |
| AC-107 | `git check-ignore -v .env` | ignorado | `.gitignore:2:.env` | **superada** |

## Evidencia adicional

- Healthcheck efectivo dentro del contenedor:
  `docker inspect metalnova_db --format '{{json .Config.Healthcheck.Test}}'`
  → `["CMD-SHELL","pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]`
- Publicación de puerto: `docker port metalnova_db` → `5432/tcp -> 127.0.0.1:5432`.
- Imagen del pipeline construida: `metalnova/ingestor:local` (Python 3.13-slim + psycopg 3.2.9).
- Tabla de prueba `_persistencia_prueba` eliminada tras verificar.

## Observaciones

- `docker compose up -d` devuelve código 0 verificado con `$LASTEXITCODE`. La aparente falla
  (código 1 / `NativeCommandError`) es un artefacto de PowerShell al leer el progreso de Docker
  desde *stderr*; el arranque se confirma con `docker compose ps`.
- El volumen `metalinova_pgdata` conserva los datos entre reinicios siempre que no se use `-v`.
