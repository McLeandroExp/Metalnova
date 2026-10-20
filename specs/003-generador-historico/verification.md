# Verificación — Incremento 003

Fecha de las pruebas: 2026-10-19.
Entorno: Windows 11, 8 GB, Docker Desktop, PostgreSQL 16.4 en Docker, Python 3.13 en el
contenedor `ingestor`. Todos los datos son **sintéticos**.

Parámetros de la ejecución canónica:

```text
semilla     42
días        180
rango       2026-04-22 → 2026-10-18
escenario   degradado
intensidad  1.0
plantas     3
máquinas    52
run_id      hist-h55dac4e285
```

## Criterios de aceptación

| AC | Comando | Salida esperada | Salida observada | Veredicto |
|---|---|---|---|---|
| AC-301 | `python src/verify_history.py` | ≥ 200 000 eventos de origen | `fact_evento = 405.995` | **superada** |
| AC-302 | consulta de cobertura en `fact_produccion` | 180 días exactos | `2026-04-22 → 2026-10-18`, `días distintos = 180` | **superada** |
| AC-303 | `sql/validation/02_historico.sql` | 0 registros con `fin < inicio` | 0 en `fact_produccion`, `fact_parada` y `fact_mantenimiento` | **superada** |
| AC-304 | `sql/validation/02_historico.sql` | 0 cantidades/tiempos inválidos | 0 conteos negativos, 0 desbalances de tiempos | **superada** |
| AC-305 | regenerar con la misma semilla y comparar | recuentos y contenido idénticos | mismo `run_id`; los 6 CSV con **SHA-256 idéntico** | **superada** |
| AC-306 | manifiestos de generación y carga | memoria acotada y métricas documentadas | generación 16,98 s / 43,0 MB; carga 75,89 s / 61,4 MB; CSV 98.835.174 bytes | **superada** |
| AC-307 | `sql/validation/02_historico.sql` | 0 claves huérfanas | 0 huérfanos en las 8 relaciones comprobadas | **superada** |

## Recuentos por tabla

| Tabla | Filas |
|---|---:|
| `dim_orden` | 28.080 |
| `fact_produccion` | 28.080 |
| `fact_parada` | 76.827 |
| `fact_mantenimiento` | 4.400 |
| `fact_calidad` | 28.080 |
| `fact_evento` | **405.995** |

Resultado de `python src/verify_history.py`: **17/17 comprobaciones OK** (incluye que el `run_id`
del manifiesto y el de la base coincidan).
Resultado de `sql/validation/02_historico.sql`: **24 chequeos, todos con `estado = OK`**.

## Distribución de eventos (FR-304)

| Fuente | Tipo | Eventos |
|---|---|---:|
| `iot` | `transicion_estado` | 209.814 |
| `iot` | `parada` | 76.827 |
| `scada` | `lectura_proceso` | 58.794 |
| `mes` | `orden_produccion` | 28.080 |
| `calidad` | `inspeccion` | 28.080 |
| `cmms` | `mantenimiento` | 4.400 |

Los eventos se emiten **por transición y por evento de negocio**, no por snapshots periódicos.
Compatibilidad con la Constitución §2: ~43 eventos/máquina/día (405.995 / 52 / 180).

## Clasificación de paradas (FR-310, regla G6)

| Planificada | Microparada | Paradas | Duración media |
|---|---|---|---:|
| sí | no | 29.919 | 30,45 min |
| no | sí | 42.734 | 2,51 min |
| no | no | 4.174 | 17,45 min |

Las microparadas tienen duración < 5 min y no tienen orden CMMS. Las fallas tienen orden de
trabajo correctiva asociada. Los mantenimientos preventivos también generan parada planificada.

## Degradación del OEE (FR-303)

Agregado mensual ponderado calculado desde `fact_produccion` + `dim_tiempo`:

| Mes | Disponibilidad | Rendimiento | Calidad | OEE |
|---|---:|---:|---:|---:|
| 2026-04 | 0,9915 | 0,9300 | 0,9916 | **0,9144** |
| 2026-05 | 0,9896 | 0,9186 | 0,9860 | 0,8963 |
| 2026-06 | 0,9877 | 0,9034 | 0,9775 | 0,8722 |
| 2026-07 | 0,9860 | 0,8878 | 0,9690 | 0,8483 |
| 2026-08 | 0,9841 | 0,8707 | 0,9604 | 0,8229 |
| 2026-09 | 0,9819 | 0,8559 | 0,9520 | 0,8000 |
| 2026-10 | 0,9813 | 0,8421 | 0,9452 | **0,7811** |

Manifiesto: OEE de los 7 primeros días `0,9141`; últimos 7 días `0,7772`.

## Reproducibilidad (AC-305)

Dos generaciones con los mismos parámetros produjeron los mismos recuentos y archivos
byte a byte idénticos. Hash SHA-256:

```text
dim_orden            BF6B54FCA7F056F3133193D368AE0493516DD7E823AC67DFD32E37000C1D7F07
fact_produccion      5573F935D169E87B7324AECB43FA1898998B2AF43B6F700EA2443F781821D54B
fact_parada          56FE177C7F3FB4C980E1BE40AE81B3F7ED3B74226CA4A0BA50188915A6479E22
fact_mantenimiento   A0B838B4B679D198990904842FC65D657EA03502795F11DBDB4AA2871F7B9805
fact_calidad         A3475CD25F155C770E3F15EC2D2C0C0CAB4D810AF6205F51F9E3D9B9583E814E
fact_evento          E05F24B1C8A8A5039C1AB23A8F7905A19499FED304D3BFE6B6D9E2E4C3C7FC7F
```

## Idempotencia de la carga (T-308)

Segunda ejecución de `load_history.py` sobre el mismo `run_id`:

```text
duración 43,21 s · memoria 61,3 MB
dim_orden            leídas 28.080 · insertadas 0 · omitidas 28.080 · total 28.080
fact_mantenimiento   leídas  4.400 · insertadas 0 · omitidas  4.400 · total  4.400
fact_parada          leídas 76.827 · insertadas 0 · omitidas 76.827 · total 76.827
fact_produccion      leídas 28.080 · insertadas 0 · omitidas 28.080 · total 28.080
fact_calidad         leídas 28.080 · insertadas 0 · omitidas 28.080 · total 28.080
fact_evento          leídas 405.995 · insertadas 0 · omitidas 405.995 · total 405.995
```

La guardia de `run_id` también se probó: intentar cargar otra semilla sin `--reset` aborta con
`La base ya contiene datos de otra ejecución (...)`.

## Escenarios y filtros (FR-302, FR-309)

| Prueba | Resultado |
|---|---|
| Escenario `base`, 180 días | 366.707 eventos; OEE 0,9164 → 0,8948 (degradación leve) |
| Escenario `degradado`, 180 días | 405.995 eventos; OEE 0,9141 → 0,7772 (degradación marcada) |
| `--plantas 1 --maquinas 18 --days 1` | catálogo filtrado a 18 máquinas; `dim_orden` = 54 filas; 641 eventos |

## Volumen y rendimiento (AC-306)

| Archivo | Filas | Bytes |
|---|---:|---:|
| `dim_orden.csv` | 28.080 | 1.511.904 |
| `fact_produccion.csv` | 28.080 | 3.304.299 |
| `fact_parada.csv` | 76.827 | 8.849.465 |
| `fact_mantenimiento.csv` | 4.400 | 531.603 |
| `fact_calidad.csv` | 28.080 | 2.957.261 |
| `fact_evento.csv` | 405.995 | 81.680.642 |
| **Total** | **571.462** | **98.835.174** |

- Generación: 16,98 s, pico 43,0 MB (streaming a CSV, sin cargar el histórico en memoria).
- Carga limpia (`--reset`): 75,89 s, pico 61,4 MB (lotes de 10.000 filas con `COPY` a tabla temporal).
- Carga idempotente: 43,21 s, pico 61,3 MB.

## Observaciones

- El turno C empieza a las 22:00 y termina a las 06:00 del día siguiente; la cobertura se mide
  sobre las 180 fechas de producción (`fact_produccion.id_tiempo`), no sobre el rango de
  `timestamptz`. Los eventos del último turno se extienden hasta la mañana siguiente por diseño.
- El OEE no se fuerza a las cifras del enunciado (78 % → 66 %): la Constitución §12 lo prohíbe
  salvo calibración documentada. La tendencia se genera con perfiles de degradación explícitos.
- `manifest.json` (generación) y `load_manifest.json` (carga) viven en `data/processed/`, que no se
  versiona. La evidencia reproducible está en este documento y en los comandos del `README.md`.
