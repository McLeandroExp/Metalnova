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
| 002 · Modelo dimensional SQL | **hecho** |
| 003 · Generador histórico (180 días) | **hecho** |
| 004 · Ingesta continua simulada | **hecho** |
| 005 · Vistas KPI y validación | **hecho** |
| 006 · Informe Power BI (4 páginas) | **en curso** |
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
python/src/generate_history.py  generador del histórico sintético
python/src/load_history.py      carga por lotes a PostgreSQL
python/src/verify_history.py    verificación post-carga
python/src/ingest.py            inserción idempotente y métricas de ingesta (004)
python/src/simulate_events.py   simulador de ingesta continua (004)
python/src/validate_data.py     validación independiente de los KPI (005)
sql/                         esquema, vistas, índices y validaciones (montado en /sql)
sql/views/                   4 vistas base + 20 vistas KPI (005)
data/                        CSV generados y manifiestos (no versionados)
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

Objetos creados: 10 dimensiones, 6 tablas de hechos, 18 índices, 4 vistas base y 20 vistas KPI. El catálogo
sintético incluye 3 plantas, 6 líneas, 52 máquinas, 3 familias, 12 productos, 3 turnos, 13 causas,
12 técnicos y 1095 días de calendario (2025-01-01 → 2027-12-31). El incremento 003 añade la
causa planificada `DESCANSO`.

Detalle completo en `docs/DATA_DICTIONARY.md`.

---

## Histórico sintético (incremento 003)

Genera **180 días** de datos sintéticos (52 máquinas × 3 turnos) y los carga en PostgreSQL.

> Si modificas el código de `python/src/`, reconstruye la imagen antes de ejecutar:
> `docker compose build ingestor`.

```powershell
# 1. Generar CSV + manifiesto reproducible
docker compose run --rm ingestor python src/generate_history.py --seed 42

# 2. Cargar por lotes (idempotente para la misma ejecución)
docker compose run --rm ingestor python src/load_history.py

# 3. Verificar integridad, cobertura y recuentos
docker compose run --rm ingestor python src/verify_history.py

# Alternativa SQL (24 chequeos; todos deben dar estado = OK)
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/02_historico.sql
```

Parámetros principales de `generate_history.py`:

| Parámetro | Default | Descripción |
|---|---|---|
| `--seed` | `42` | Semilla; misma semilla ⇒ mismos archivos |
| `--days` | `180` | Días de histórico |
| `--end-date` | ayer (UTC) | Último día; el rango es `end-date − days + 1` … `end-date` |
| `--escenario` | `degradado` | `base` (degradación leve) o `degradado` (OEE decreciente marcado) |
| `--intensidad` | `1.0` | Multiplicador de fallas, microparadas y excursiones térmicas |
| `--plantas` | `3` | Plantas incluidas |
| `--maquinas` | `52` | Máximo de máquinas incluidas |

Salidas:

- `data/raw/*.csv`: `dim_orden`, `fact_produccion`, `fact_parada`, `fact_mantenimiento`,
  `fact_calidad`, `fact_evento` (no versionados).
- `data/processed/manifest.json`: semilla, parámetros, `run_id`, recuentos por tabla, tamaños,
  duración, memoria pico y serie diaria de OEE.
- `data/processed/load_manifest.json`: filas leídas/insertadas/omitidas y tiempos de carga.

Resultado observado con los valores por defecto (2026-10-19):

```text
run_id            hist-h55dac4e285
eventos de origen 405.995
dim_orden         28.080     fact_produccion   28.080
fact_parada       76.827     fact_mantenimiento 4.400
fact_calidad      28.080     fact_evento       405.995
generación        16,98 s · pico 43,0 MB
carga             75,89 s · pico 61,4 MB · CSV ≈ 98,8 MB
OEE 7 primeros días 0,9141 → 7 últimos 0,7772
```

Reproducibilidad: dos ejecuciones con la misma semilla y parámetros producen los seis CSV con
SHA-256 idéntico y el mismo `run_id`.

> ⚠️ **Cambiar la semilla o los parámetros cambia el `run_id`.** Si la base ya contiene otra
> ejecución, `load_history.py` se detiene para no mezclar datos. Para reemplazarlos de forma
> explícita usa `--reset` (vacía hechos y `dim_orden`; no toca el catálogo ni el volumen).

> ⚠️ Los datos son **sintéticos**. El generador no pretende reproducir las cifras exactas del
> enunciado; la tendencia de OEE se controla con el escenario elegido.

---

## Ingesta continua simulada (incremento 004)

Simula la llegada de eventos **por transición** (arranque/parada) para las 52 máquinas y los
inserta en PostgreSQL. No muestrea una fila por máquina y minuto: cada ciclo decide qué máquinas
cambian de estado y emite únicamente esos eventos, más el arranque de las paradas que terminan en
el ciclo.

```powershell
# Bucle continuo: un ciclo cada 60 s hasta Ctrl+C
docker compose --profile tools run --rm ingestor python src/simulate_events.py

# Un solo ciclo (verificación rápida)
docker compose --profile tools run --rm ingestor python src/simulate_events.py --once

# Escenario reproducible para la demo: parada de 20 min en M-001
docker compose --profile tools run --rm ingestor python src/simulate_events.py --scenario stop M-001 --once

# Reloj fijo: repetir el mismo comando no inserta duplicados
docker compose --profile tools run --rm ingestor python src/simulate_events.py --once --at 2026-10-21T00:10:00Z
```

Parámetros principales:

| Parámetro | Default | Descripción |
|---|---|---|
| `--interval` | `60` (`SIM_INTERVAL_SECONDS`) | Segundos entre ciclos (mínimo 5) |
| `--cycles` | `0` | Número de ciclos; `0` = indefinido |
| `--once` | — | Un solo ciclo y termina (sin esperas) |
| `--at` | ahora (UTC) | Reloj fijo ISO-8601 para pruebas reproducibles |
| `--seed` | `42` (`SIM_SEED`) | Semilla de las decisiones por máquina y slot |
| `--intensity` | `1.0` (`SIM_INTENSITY`) | Multiplicador de la probabilidad de parada |
| `--scenario stop M-001` | — | Parada inducida para la demo |
| `--stop-duration-min` | `20` | Duración del escenario |
| `--dry-run` | — | Genera y registra sin insertar |
| `--max-attempts` / `--retry-delay` | `3` / `1.0` | Reintentos y *backoff* ante error de base |

Salidas:

- `logs/simulate_events.log`: log UTC con `run_id`, ciclo, eventos generados/insertados,
  duración, latencia y errores (sin credenciales).
- `logs/simulate_events_<run_id>.json`: métricas por ejecución (`run_id`, ciclos, recuentos,
  latencia media/máxima, cobertura de máquinas/plantas, motivo de salida).
- `fact_evento` y `fact_parada`: eventos y episodios de parada.

**Idempotencia.** Cada ciclo se alinea a una rejilla temporal y las decisiones se derivan de
`SHA-256(seed, máquina, slot)`. Los `source_event_id` son estables (`sim-down-…`, `sim-parada-…`,
`sim-up-…`) y la inserción usa `ON CONFLICT` sobre `(source_system, source_event_id)`; la parada usa
`(id_maquina, inicio_at)`. Reiniciar el proceso o repetir un ciclo no duplica filas. Las paradas
simuladas se identifican con `fact_parada.causa_detalle LIKE 'Ingesta 004:%'`.

**Latencia.** Se mide `ingested_at − generated_at` (latencia de pipeline). Resultado observado:
entre **4 ms y 36 ms** en las ejecuciones de verificación, muy por debajo del objetivo de 10 min.
`ingested_at − event_time` se registra aparte como desfase de evento porque `event_time` es el
inicio del slot simulado.

**Cierre limpio.** `Ctrl+C` (o `docker kill -s INT`) registra `interrupción recibida`, escribe el
JSON de métricas y termina con código 0. Si la base no responde tras los reintentos, registra el
error y termina con código 2.

**Escenario de la demo.** `--scenario stop M-001` inserta una parada de 20 min con causa fija
`F-MEC` en el turno actual. El cambio se observa en las vistas KPI de mantenimiento:

```sql
SELECT fecha, turno_codigo, downtime_no_planificado_min, fallas, mtbf_h
FROM v_kpi_mantenimiento_maquina_turno
WHERE maquina_codigo = 'M-001'
ORDER BY fecha DESC, turno_codigo DESC
LIMIT 3;
```

Resultado observado (2026-10-21): M-001 pasó de no tener fila en el turno C del 2026-10-20 a
`downtime_no_planificado_min = 20`, `fallas = 1`, `mtbf_h = NULL`; la planta P-NORTE pasó de
5 a 25 min de downtime y de 0 a 1 falla. Si el turno elegido ya tiene producción histórica, la
vista de downtime prioriza `fact_produccion` y el simulador emite una advertencia.

> ℹ️ Los `run_id` de la ingesta usan el prefijo `sim-` y no interfieren con el histórico `hist-*`:
> `load_history.py` y `verify_history.py` los ignoran al comparar la ejecución histórica.

Evidencia completa: `specs/004-ingesta-continua/verification.md` y `logs/ingest_004_*.txt`.

---

## Vistas KPI y validación (incremento 005)

Las 20 vistas KPI son el contrato analítico para Power BI. Se aplican junto con el esquema:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/apply_all.sql
```

| Grupo | Vistas |
|---|---|
| Base de hechos | `v_kpi_produccion`, `v_kpi_calidad`, `v_kpi_parada`, `v_kpi_mantenimiento` |
| OEE | `v_kpi_oee_planta_dia`, `_linea_dia`, `_maquina_dia`, `_maquina_turno`, `_producto_dia` |
| Mantenimiento | `v_kpi_mantenimiento_maquina_turno`, `_maquina_dia`, `_maquina_mes`, `_planta_dia` |
| Confiabilidad | `v_kpi_confiabilidad_apoyo_maquina_dia` |
| Calidad/energía | `v_kpi_calidad_maquina_dia`, `v_kpi_calidad_producto_dia` |
| Loss Tree | `v_loss_tree`, `v_loss_tree_maquina_mes` |
| Alerta | `v_alerta_maquina_critica` |

Validación independiente (recalcula los KPI desde los hechos y compara con las vistas):

```powershell
docker compose --profile tools run --rm ingestor python src/validate_data.py
```

Resultado observado (2026-10-20): **49/49 comprobaciones OK**, diferencia máxima `4,37e-11`
(tolerancia `1e-9`). Resumen global: disponibilidad `0,9857`, rendimiento `0,8851`, calidad
`0,9683`, OEE `0,8447`; MTBF `49,46 h`; MTTR `17,45 min`; 23.403 turnos sin alerta, 4.528 en
alerta y 149 críticos. El OEE de octubre (0,7811) coincide con el histórico verificado en 003.
La validación se repitió el 2026-10-21 después de la ingesta simulada: **49/49 OK** de nuevo.

Reglas: los porcentajes se agregan con `SUM(numerador) / SUM(denominador)`, nunca promediando
porcentajes; las razones indefinidas devuelven `NULL` (D-014). Umbrales y definiciones completas
en `docs/DATA_DICTIONARY.md`; evidencia en `specs/005-kpi-y-vistas/verification.md`.

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
| `load_history.py` aborta por «datos de otra ejecución» | la base contiene otro `run_id` | revisar y usar `--reset` de forma consciente |
| `generate_history.py` pide la causa `DESCANSO` | catálogo 002 sin la causa 13 | ejecutar `sql/apply_all.sql` |
| `simulate_events.py` rechaza `--at` por futuro | el rango válido termina en `ahora + 5 min` | usar una hora pasada o quitar `--at` |
| El simulador no genera eventos en un ciclo | es normal: solo emite transiciones | esperar más ciclos o subir `--intensity` |
| Repetir un ciclo inserta 0 filas | idempotencia esperada | verificar que no haya duplicados; es correcto |
| El escenario no cambia el downtime | el turno ya tiene producción histórica | usar un turno actual fuera del histórico (ver advertencia en el log) |
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
