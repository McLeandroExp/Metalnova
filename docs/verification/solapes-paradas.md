# Solapes de paradas — implementación y verificación

> **Todos los datos son sintéticos.** La verificación se ejecutó el **2026-10-24**
> contra la base local `metalinova`. La prueba de solapes se hizo dentro de
> `BEGIN … ROLLBACK`; no dejó filas persistidas.

- **Decisión:** `docs/DECISIONS.md` D-023.
- **Alcance:** consolidar solapes en la capa analítica sin modificar
  `fact_parada` ni `fact_produccion`.
- **Documentos relacionados:** `bloque1-negocio-modelo.md` §3,
  `bloque2-modelado-dimensional.md` §4.

## 1. Qué se implementó

| Cambio | Archivo | Efecto |
|---|---|---|
| Vista `v_parada_consolidada` | `sql/views/02_kpi_base.sql` | Une intervalos estrictamente solapados por máquina; conserva el hecho crudo |
| `v_kpi_parada` lee de la vista consolidada | `sql/views/02_kpi_base.sql` | Pareto, fallas, microparadas y MTBF usan la unión |
| `v_kpi_mantenimiento_maquina_turno` lee de la vista consolidada | `sql/views/04_kpi_mantenimiento.sql` | Conteos y minutos de parada no duplican solapes |
| Validaciones de invariantes | `sql/validation/05_parada_consolidada.sql` | 13 comprobaciones |
| Prueba controlada | `sql/validation/06_parada_consolidada_prueba.sql` | Solape 10+15 → 20; adyacentes → 2 episodios; mixto → no planificado; termina en `ROLLBACK` |
| Ajuste del validador de KPI | `python/src/validate_data.py` | `oee` se compara con 1e-6 (redondeo a 6 decimales); el resto sigue en 1e-9 |

`fact_parada` **no se modificó** y `fact_produccion` **no se modificó**. El OEE,
la disponibilidad y el Loss Tree siguen usando
`fact_produccion.downtime_no_planificado_min`.

## 2. Regla aplicada

- Se unen **solo solapes estrictos**:
  `a.inicio_at < b.fin_at AND b.inicio_at < a.fin_at`.
- **No se unen intervalos adyacentes** (`fin = siguiente inicio`): pueden tener
  causas distintas y deben seguir contando como dos episodios para MTBF/fallas.
- `fin_at IS NULL` se trata como intervalo abierto para detectar solapes.
- Inicio = mínimo; fin = máximo; duración = minutos de la unión.
- Turno/día: los del episodio que inicia primero.
- Causa: la del episodio no planificado de mayor duración; si todos son
  planificados, la del de mayor duración (empate: el más temprano).
- CMMS: la primera OT no nula, priorizando la de mayor duración y, si hay un
  tramo no planificado, la de ese tramo.
- `es_planificada`: `true` solo si todos los orígenes son planificados.
- `es_microparada`: se recalcula con la unión y `microparada_min = 5`.

La vista expone `episodios_origen`, `ids_origen` y `minutos_solapados` para
auditoría.

## 3. Impacto en los datos actuales

El dataset actual **no tiene solapes estrictos**, así que la consolidación es un
no-op:

| Métrica | Crudo | Consolidado |
|---|---:|---:|
| Episodios | 76.045 | 76.045 |
| Minutos | 1.063.948 | 1.063.948 |
| Minutos solapados | — | 0 |
| Orígenes cubiertos | — | 76.045 |

**Clasificación resultante (sin cambios):**

| Clasificación | Episodios | Minutos |
|---|---:|---:|
| Falla | 2.417 | 43.207 |
| Microparada | 43.692 | 109.020 |
| Planificada | 29.936 | 911.721 |
| **Total** | **76.045** | **1.063.948** |

**OEE global (sin cambios):** 71,96 %; A 98,79 % · P 76,55 % · Q 95,16 %.

## 4. Verificación de invariantes

Comando:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/validation/05_parada_consolidada.sql
```

Salida observada (2026-10-24):

| Chequeo | Incidencias | Estado |
|---|---:|---|
| Pares de episodios solapados en la vista | 0 | OK |
| Episodios consolidados <= crudos | 0 | OK |
| Minutos unión <= minutos brutos | 0 | OK |
| Cobertura exacta de `ids_origen` | 0 | OK |
| `episodios_origen >= 1` | 0 | OK |
| `episodios_origen = cardinalidad(ids_origen)` | 0 | OK |
| Duración negativa | 0 | OK |
| Fin anterior al inicio | 0 | OK |
| Minutos solapados negativos | 0 | OK |
| Planificada marcada como microparada | 0 | OK |
| Microparada inconsistente con G6 | 0 | OK |
| `v_kpi_parada` filas = `v_parada_consolidada` | 0 | OK |
| `v_kpi_parada` planificada vs causa planificada | 0 | OK |

Resumen:

```text
episodios_crudos = 76045
episodios_consolidados = 76045
minutos_crudos = 1063948
minutos_consolidados = 1063948
minutos_solapados = 0
```

## 5. Prueba controlada

Comando:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/validation/06_parada_consolidada_prueba.sql
```

La prueba inserta tres casos y los revierte:

### Caso A — solape estricto

Dos paradas: 10:00–10:10 (10 min) y 10:05–10:20 (15 min).

| Resultado | Valor |
|---|---:|
| Episodios consolidados | 1 |
| Inicio / fin | 10:00 / 10:20 |
| Duración | **20 min** |
| `episodios_origen` | 2 |
| `minutos_solapados` | **5** |
| Causa | la del episodio de 15 min |
| `es_planificada` | `false` |
| `es_microparada` | `false` |

La suma bruta habría sido 25 min; la unión correcta es 20 min.

### Caso B — intervalos adyacentes

Dos paradas: 10:00–10:10 y 10:10–10:20.

| Resultado | Valor |
|---|---:|
| Episodios consolidados | **2** |
| Duración de cada uno | 10 min |
| `episodios_origen` | 1 por episodio |
| `minutos_solapados` | 0 |

Esto confirma que no se unen adyacentes: si se unieran, se perdería la distinción
de causas y se alterarían los conteos de fallas.

### Caso C — mixto planificado/no planificado

Un descanso planificado de 30 min (10:00–10:30) y una falla de 10 min
(10:10–10:20).

| Resultado | Valor |
|---|---:|
| Episodios consolidados | 1 |
| Duración | 30 min |
| `episodios_origen` | 2 |
| `minutos_solapados` | 10 |
| `es_planificada` | **false** (“no planificado gana”) |
| Causa | la del tramo no planificado |
| `v_kpi_parada.clasificacion` | **falla** |
| `v_kpi_parada.causa_categoria` | **Falla** |

### Comprobaciones posteriores

- Dentro de la transacción: `solapes_consolidados = 0`.
- Después de `ROLLBACK`: `filas_prueba = 0`.

## 6. Regresión de KPI

Se reaplicó el esquema completo con `sql/apply_all.sql` y se ejecutó:

```powershell
docker compose run --rm ingestor python src/validate_data.py
```

Resultado: **49/49 comprobaciones OK**.

Valores globales observados: OEE 0,7196; A 0,9879; P 0,7655; Q 0,9516;
MTBF 85,61 h con 2.417 fallas; MTTR 17,84 min con 2.401 reparaciones.

También se ejecutó `validate_iot.py`: **11/11 comprobaciones OK**, sin cambios en
la calidad y temporalidad de eventos IoT.

Validación del modelo y del informe:

```text
python tools/validate_model.py
OK: 70 medidas, 27 relaciones, 15 tablas; referencias y tipos coherentes.

python tools/validate_report.py
Páginas: 8 · Visuales: 105
Resultado: OK · todas las referencias y páginas son coherentes
```

No se modificó el TMDL ni el PBIR; las columnas de `v_kpi_parada` y
`v_kpi_mantenimiento_maquina_turno` se mantienen, por lo que el informe no necesita
cambios.

El validador compara `oee` con 1e-6 porque las vistas `v_kpi_oee_*` y
`v_alerta_maquina_critica` lo redondean a 6 decimales; el resto de métricas sigue
con 1e-9.

## 7. Rendimiento

`EXPLAIN ANALYZE SELECT count(*), sum(duracion_min) FROM v_parada_consolidada;`

```text
Execution Time: 245.613 ms
```

Es una vista no materializada sobre 76.045 filas. En DirectQuery puede repetirse
por visual; si el informe se degrada, la siguiente fase sería materializarla y
refrescarla tras la ingesta. No se hizo porque el dataset actual no tiene solapes
y el coste no se justifica todavía.

## 8. Limitaciones declaradas

1. **El OEE no cambia con esta decisión.** Sigue usando
   `fact_produccion.downtime_no_planificado_min`. Si se exige que el OEE también
   refleje la consolidación, hay que reconciliar `fact_produccion` en una segunda
   fase.
2. **Solape mixto planificado/no planificado:** se aplica “no planificado gana”.
   Esto evita ocultar una falla, pero puede atribuir minutos planificados como no
   planificados. La solución exacta sería partir en tramos por clase.
3. **Cruce de turno:** el episodio consolidado se atribuye al turno/día de inicio.
   Si se necesita precisión por turno, hay que segmentar la unión.
4. **Varias OT:** `fact_parada.id_mantenimiento` es una sola FK; se conserva la OT
   principal. Una tabla puente sería la solución completa.
5. **`fact_parada` crudo sigue admitiendo solapes.** La consolidación es
   analítica; el hecho crudo se conserva para trazabilidad.
6. **Validador Python:** `validate_data.py` sigue comparando `v_kpi_parada`
   contra `fact_parada` crudo; con 0 solapes es equivalente. La ruta de solapes se
   verifica con `05`/`06`; si se añaden solapes al dataset, el validador marcará
   diferencias esperadas y habrá que adaptarlo.
7. **Cifras mutables:** si se ejecuta nueva ingesta simulada, los totales cambian.

## 9. Reproducción completa

```powershell
# 1. Aplicar el esquema y las vistas
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/apply_all.sql

# 2. Invariantes de la consolidación
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/validation/05_parada_consolidada.sql

# 3. Prueba controlada (rollback)
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/validation/06_parada_consolidada_prueba.sql

# 4. Regresión de KPI y calidad IoT
docker compose run --rm ingestor python src/validate_data.py
docker compose run --rm ingestor python src/validate_iot.py
```

Si se modificó código Python, reconstruir la imagen antes del paso 4:

```powershell
docker compose build ingestor
```
