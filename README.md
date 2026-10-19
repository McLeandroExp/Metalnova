# MetalNova Smart Factory BI

Prototipo académico de Business Intelligence que analiza el rendimiento de una fábrica de
componentes automotrices (3 plantas, 52 máquinas) a partir de **datos sintéticos** de 180 días
más una simulación de eventos cercanos al tiempo real.

> ⚠️ **Los datos son sintéticos.** No son telemetría real de ninguna fábrica. Este repositorio no
> reproduce necesariamente las cifras del enunciado del caso (OEE 78 %→66 %, USD 540 000/mes).

**Stack:** PostgreSQL en Docker · Python · Power BI Desktop (Windows) · sin nube.

---

## Estado del proyecto

| Incremento | Estado |
|---|---|
| 001 · Infraestructura PostgreSQL en Docker | **hecho** |
| 002 · Modelo dimensional SQL | propuesto |
| 003 · Generador histórico (180 días) | propuesto |
| 004 · Ingesta continua simulada | propuesto |
| 005 · Vistas KPI y validación | propuesto |
| 006 · Informe Power BI (4 páginas) | propuesto |
| 007 · Integración, demo y plan de mejora | propuesto |

El detalle de cada incremento vive en `specs/`. Ver también `specs/CONSTITUTION.md` (fuente de
verdad normativa) y `AGENTS.md`.

---

## Requisitos previos

- Windows 11 con **Docker Desktop** en ejecución.
- **Power BI Desktop** (para el incremento 006).
- Puerto `5432` libre en `127.0.0.1`.
- No se necesita Python instalado en Windows: el pipeline corre en un contenedor.

---

## Estructura

```text
compose.yaml                 servicios db (PostgreSQL) e ingestor (Python)
.env.example                 plantilla de variables de entorno
specs/                       especificaciones SDD (fuente de verdad)
docs/                        arquitectura, diccionario, pruebas, runbook
docs/reference/              insumos académicos originales (no normativos)
docker/postgres/init/        scripts de initdb (solo corren con volumen vacío)
docker/pgadmin/servers.json  servidor PostgreSQL pre-registrado en pgAdmin
python/                      Dockerfile del pipeline + código
sql/                         esquema, vistas, índices y validaciones (montado en /sql)
data/                        CSV/Parquet generados (no versionados)
logs/                        logs del pipeline (no versionados)
powerbi/                     informe .pbix / .pbip
```

---

## Configuración inicial

```powershell
Copy-Item .env.example .env
# editar .env y cambiar POSTGRES_PASSWORD
```

`.env` está ignorado por Git. Nunca se commitea.

---

## Arranque y parada

```powershell
# Arrancar la base de datos
docker compose up -d

# Ver estado (debe aparecer "healthy")
docker compose ps

# Ver logs
docker compose logs --tail 50 db
docker compose logs -f db

# Parar conservando los datos
docker compose down
```

> ⚠️ **No ejecutes `docker compose down -v`**: elimina el volumen `metalinova_pgdata` y con él
> toda la base de datos.

> ℹ️ **Nota sobre PowerShell:** Docker escribe su progreso en *stderr*. PowerShell puede mostrar
> `NativeCommandError` y un código de salida 1 aunque el comando haya funcionado. Verifica
> siempre con `docker compose ps`.

---

## Prueba de conectividad

```powershell
docker compose run --rm ingestor python src/check_connection.py
```

Salida observada (2026-10-19):

```text
SELECT 1 -> 1
Base: metalinova
Servidor: PostgreSQL 16.4 on x86_64-pc-linux-musl
Conexión OK
```

---

## Prueba de persistencia

```powershell
# 1. Crear una marca
docker compose exec -T db psql -U metalinova -d metalinova `
  -c "CREATE TABLE IF NOT EXISTS _persistencia_prueba(id int primary key, creado_en timestamptz NOT NULL DEFAULT now());" `
  -c "INSERT INTO _persistencia_prueba(id) VALUES (1) ON CONFLICT (id) DO NOTHING;"

# 2. Reiniciar sin borrar el volumen
docker compose down
docker compose up -d

# 3. Comprobar que la marca sobrevivió
docker compose exec -T db psql -U metalinova -d metalinova `
  -c "SELECT count(*) FROM _persistencia_prueba;"

# 4. Limpiar
docker compose exec -T db psql -U metalinova -d metalinova `
  -c "DROP TABLE IF EXISTS _persistencia_prueba;"
```

Resultado observado (2026-10-19): `filas=1` tras el reinicio.

---

## Esquema de la base de datos

El esquema es versionado e idempotente (incremento 002). Se aplica explícitamente:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/apply_all.sql
```

Verificación de integridad:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/01_integridad.sql
```

Todas las filas deben mostrar `estado = OK`.

Objetos creados: 10 dimensiones, 6 tablas de hechos, 18 índices y 4 vistas base. El catálogo
sintético incluye 3 plantas, 6 líneas, 52 máquinas, 3 familias, 12 productos, 3 turnos, 12 causas,
12 técnicos y 1095 días de calendario (2025-01-01 → 2027-12-31).

Detalle completo en `docs/DATA_DICTIONARY.md`.

---

## Cliente de base de datos (pgAdmin)

Con `docker compose up -d` también arranca **pgAdmin**:

| Dato | Valor |
|---|---|
| URL | `http://127.0.0.1:5050` |
| Email | el definido en `.env` (`PGADMIN_DEFAULT_EMAIL`) |
| Contraseña | la definida en `.env` (`PGADMIN_DEFAULT_PASSWORD`) |

El servidor **«MetalNova PostgreSQL»** aparece pre-registrado (grupo *MetalNova*). Al abrirlo por
primera vez pedirá la contraseña de PostgreSQL: es `POSTGRES_PASSWORD` del `.env`.

```powershell
# Ver el estado de pgAdmin
docker compose ps pgadmin

# Logs
docker compose logs --tail 50 pgadmin
```

> ℹ️ pgAdmin importa `docker/pgadmin/servers.json` **solo al inicializar su volumen**. Si cambias
> ese archivo y quieres reimportarlo: `docker compose rm -sf pgadmin`, elimina el volumen
> `metalinova_pgadmin` (contiene solo configuración de pgAdmin, **no** datos de la base) y vuelve
> a arrancar.

---

## Conexión desde herramientas externas

| Parámetro | Valor |
|---|---|
| Host | `127.0.0.1` |
| Puerto | `5432` (solo loopback) |
| Base | `metalinova` |
| Usuario | `metalinova` (según `.env`) |
| Contraseña | la definida en `.env` |

Power BI Desktop se conecta a `127.0.0.1:5432` en el incremento 006.

---

## Backup y restauración

Pendiente de implementar y probar en el incremento 007.

---

## Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| `db` nunca llega a `healthy` | puerto ocupado o volumen corrupto | `docker compose logs db`; revisar `netstat -ano \| findstr :5432` |
| pgAdmin no responde en 5050 | contenedor arrancando o puerto ocupado | `docker compose logs pgadmin`; `netstat -ano \| findstr :5050` |
| pgAdmin no muestra el servidor | volumen inicializado antes de existir `servers.json` | recrear el volumen de pgAdmin (ver sección pgAdmin) |
| `failed to connect to the docker API` | Docker Desktop detenido | arrancar Docker Desktop |
| La conexión falla con `Faltan variables` | `.env` ausente | `Copy-Item .env.example .env` |
| PowerShell muestra error pero el servicio corre | progreso de Docker en stderr | verificar con `docker compose ps` |

---

## Documentación

| Documento | Contenido |
|---|---|
| `specs/CONSTITUTION.md` | Reglas, modelo de datos, KPI y decisiones normativas |
| `specs/README.md` | Índice y estado de incrementos |
| `AGENTS.md` | Contexto para futuras sesiones de trabajo |
| `docs/ARCHITECTURE.md` | Componentes, flujo, puertos y volúmenes |
| `docs/DECISIONS.md` | Registro de decisiones |
| `docs/DATA_DICTIONARY.md` | Tablas, columnas y definiciones de KPI |
| `docs/TEST_PLAN.md` | Casos de prueba y evidencias |
| `docs/DEMO_RUNBOOK.md` | Guion de demostración |
