# Verificación del Bloque 2 — Modelado dimensional y preparación de datos

> **Todos los datos son sintéticos.** Las cifras corresponden a la base local
> `metalinova` consultada el **2026-10-24**. Si se ejecuta nueva ingesta simulada,
> los totales pueden variar.

- **Alcance:** modelo dimensional, jerarquías, transformaciones, normalización de
  unidades, microparadas/fallas y tratamiento de datos IoT.
- **Fuente de verdad:** `specs/CONSTITUTION.md` §5–§7.
- **Documento asociado:** [`bloque1-negocio-modelo.md`](./bloque1-negocio-modelo.md) y
  [`pregunta-principal-business-understanding.md`](./pregunta-principal-business-understanding.md).

## Resumen de veredictos

| # | Punto a verificar | Veredicto |
|---|---|---|
| 1 | Cuatro tablas de hechos con el grano pedido | **Cumple** |
| 2 | Dimensiones conformadas (Máquina, Planta, Turno, Producto, Causa, Tiempo, Técnico) | **Cumple**; matiz: Técnico no es tabla separada en Power BI |
| 3 | Jerarquías Planta → Línea → Máquina y Familia → Producto sin duplicar medidas | **Cumple con matiz** (navegación por slicers/matriz; no un visual único de 4 niveles) |
| 4 | Transformaciones: tiempo planificado, runtime, ciclo ideal, good/total count, downtime | **Cumple**; invariantes sin violaciones |
| 5 | Normalización de unidades | **Cumple** |
| 6 | Distinguir microparadas de fallas | **Cumple** (regla G6) |
| 7 | Duplicados, desordenados, timestamps fuera de rango | **Cumple** |
| 8 | Lecturas faltantes | **Cumple con matiz**: se declaran el hueco y la cadencia; el estado `unknown` no se emite |
| 9 | Fuente de verdad para inicio/fin de una parada | **Cumple**: transición IoT/SCADA; CMMS explica, no define |
| 10 | Solapes de paradas | **Cumple con matiz**: `v_parada_consolidada` une solapes estrictos; el OEE sigue usando `fact_produccion` (ver `solapes-paradas.md`) |

---

## 1. Modelo dimensional

### 1.1 Tablas de hechos

| Tabla | Grano | Filas | Clave de unicidad | Evidencia |
|---|---|---:|---|---|
| `fact_produccion` | orden + máquina + turno + día | 28.080 | `(id_orden, id_maquina, id_turno, id_tiempo)` | 0 duplicados |
| `fact_parada` | un episodio de parada | 76.045 | `(id_maquina, inicio_at)` | 0 duplicados |
| `fact_mantenimiento` | una orden de trabajo / intervención | 2.628 | `codigo_orden_trabajo` | 0 duplicados |
| `fact_calidad` | una inspección / lote | 28.080 | `codigo_inspeccion` | 0 duplicados |

**Matiz de grano en `fact_produccion`:** el esquema incluye `id_tiempo` (día) en la
clave, por lo que el grano declarado es orden + máquina + turno + día. En este
dataset cada orden tiene exactamente **una fila** (`max_filas = 1` y 0 pares
orden-máquina-turno con más de una fila), así que el grano efectivo es
**orden + máquina + turno**. El día se conserva para permitir órdenes que crucen
medianoche en una futura ampliación.

**Matiz de grano en `fact_calidad`:** cada inspección tiene un lote y en este
dataset hay **28.080 inspecciones y 28.080 lotes** (relación 1:1). El grano es
inspección/lote, tal como pide el caso.

**Tablas adicionales de aterrizaje:** el modelo tiene 6 tablas de hechos, no solo
4. Las dos restantes son la capa cruda y la cuarentena:

| Tabla | Rol | Filas |
|---|---|---:|
| `fact_evento` | evento crudo de origen, idempotente por `(source_system, source_event_id)` | 401.838 |
| `fact_evento_rechazado` | evento descartado con motivo y payload | 2 |

No se mezclan con los hechos analíticos: `fact_evento` es la capa de aterrizaje y
`fact_evento_rechazado` la cuarentena. El modelo estrella para BI usa las cuatro
tablas de hechos analíticos.

### 1.2 Dimensiones conformadas

| Dimensión | Filas | Uso |
|---|---:|---|
| `dim_planta` | 3 | P-NORTE, P-CENTRO, P-SUR |
| `dim_linea` | 6 | 2 líneas por planta |
| `dim_maquina` | 52 | jerarquía Planta → Línea → Máquina |
| `dim_familia` | 3 | Frenos, Suspensión, Transmisión |
| `dim_producto` | 12 | jerarquía Familia → Producto |
| `dim_turno` | 3 | A, B, C; 480 min |
| `dim_causa` | 13 | causa de parada y causa raíz |
| `dim_tiempo` | 1.095 | calendario 2025-01-01 → 2027-12-31 |
| `dim_tecnico` | 12 | técnico de mantenimiento |
| `dim_orden` | 28.080 | orden de producción |

Las siete dimensiones pedidas están presentes: **Máquina, Planta, Turno,
Producto, Causa, Tiempo y Técnico**. Además se añaden Línea, Familia y Orden para
sostener las jerarquías y el grano de producción.

**Conformidad:** las dimensiones se comparten entre hechos donde aplica. No todos
los hechos tienen todas las claves (por ejemplo, `fact_calidad` no tiene técnico y
`fact_produccion` no tiene causa), lo cual es correcto: una dimensión conformada
se comparte cuando el hecho tiene esa clave, no se duplica en cada hecho.

**Matiz de Power BI:** el modelo semántico no expone `dim_tecnico` como tabla
separada; las columnas `id_tecnico`, `tecnico_codigo`, `tecnico_nombre` y
`tecnico_especialidad` están denormalizadas en `v_kpi_mantenimiento`. La dimensión
existe en SQL y el hecho tiene la FK, pero no hay un slicer de técnico en el
informe. Si la rúbrica exige una dimensión de técnico navegable en Power BI, es una
brecha de exposición, no de modelo.

### 1.3 Relaciones del modelo

El modelo TMDL tiene **27 relaciones** y todas van de una vista de hechos a una
dimensión (`fromColumn: v_kpi_*` / `toColumn: dim_*`). **No hay relaciones
hecho-hecho**, que es la condición para que un drill-down no multiplique filas.

| Grupo | Relaciones |
|---|---:|
| Hechos KPI → `v_dim_maquina` / `dim_turno` / `dim_tiempo` / `dim_causa` | 27 |
| Hechos → otros hechos | **0** |

---

## 2. Jerarquías y drill-down sin duplicar medidas

### 2.1 Jerarquías definidas

| Jerarquía | Niveles | Dónde |
|---|---|---|
| `Ubicación` | Planta → Línea → Máquina | `v_dim_maquina` (TMDL) |
| `Producto` | Familia → Producto | `v_dim_producto` (TMDL) |
| `Causa` | Categoría → Detalle | `dim_causa` (TMDL) |
| `Calendario` | Año → Trimestre → Mes → Día | `dim_tiempo` (TMDL) |

El turno no es un nivel de `Ubicación`: se resuelve con `dim_turno`, el slicer de
turno y la matriz máquina-turno de la página 02.

### 2.2 Justificación de no duplicación

1. Cada KPI se define **una sola vez** en `powerbi/final/measures.dax`.
2. Las medidas suman **numeradores y denominadores**; nunca promedian porcentajes.
3. Las relaciones son **hecho → dimensión**; no hay joins hecho-hecho.
4. Al filtrar por planta, línea, máquina o turno, se reduce el conjunto de filas
   del mismo hecho; la fórmula no cambia.
5. La jerarquía pertenece a la dimensión, no al hecho; por eso el drill-down no
   agrega filas ni duplica medidas.

**Prueba empírica:**

| Comparación | Filas | Discrepancias |
|---|---:|---:|
| Planta-día vs suma de máquina-turno | 540 | **0** |
| Línea-día vs suma de máquina-turno | 1.080 | **0** |
| Producción por fila: OEE vs `round(A×P×Q,6)` | 28.080 | **0** |

**Ejemplo:** P-SUR (62,04 % en 30 días) → L3-2 (60,98 %) → M-047 (47,47 %) →
turno C (45,33 %). El OEE de la planta es el ponderado, no el promedio simple de
las máquinas.

**Matiz de implementación:** el modelo tiene la jerarquía `Ubicación`, pero el
informe no tiene un único visual con flecha de drill-down de cuatro niveles. La
navegación se hace con slicers sincronizados, la matriz máquina-turno y el
drill-through. Funcionalmente se recorre planta → línea → máquina → turno; si la
rúbrica exige la flecha en un solo visual, habría que añadir ese visual.

---

## 3. Transformaciones y normalización

### 3.1 Transformaciones principales

| Transformación | Fórmula / regla | Columna | Evidencia |
|---|---|---|---|
| Tiempo de calendario | duración del turno | `tiempo_calendario_min` | 480 min en las 28.080 filas |
| Downtime planificado | descanso + cambio + mantenimiento preventivo | `downtime_planificado_min` | 0 negativos |
| Tiempo planificado | calendario − downtime planificado | `tiempo_planificado_min` | `planificado + planificado_downtime = calendario` en 28.080/28.080 |
| Runtime | planificado − downtime no planificado | `tiempo_operativo_min` | `runtime + no_planificado = planificado` en 28.080/28.080 |
| Ciclo ideal | segundos por unidad según producto | `ciclo_ideal_segundos` | rango 30–55 s |
| Minutos ideales | ciclo × total_count / 60 | `minutos_ideales` | 0 diferencias con la fórmula |
| Total count | unidades totales | `total_count` | `total = good + scrap` en 28.080/28.080 |
| Good count | unidades buenas | `good_count` | 0 negativos |
| Scrap count | unidades rechazadas | `scrap_count` | 0 negativos |
| Disponibilidad | runtime / planificado | `disponibilidad` | 0 diferencias |
| Rendimiento | minutos ideales / runtime | `rendimiento` | 0 diferencias |
| Calidad | good / total | `calidad` | 0 diferencias |
| OEE | A × P × Q; las vistas `v_kpi_oee_*` lo redondean a 6 decimales y `v_kpi_produccion` lo deja sin redondear | `oee` | 0 diferencias con `round(A×P×Q,6)` con tolerancia 1e-6 |

**Ejemplo de una fila (P-NORTE, M-001, turno A, PRD-001):**

| Campo | Valor |
|---|---:|
| Tiempo planificado | 450 min |
| Runtime | 450 min |
| Downtime no planificado | 0 min |
| Total count | 821 |
| Good count | 803 |
| Scrap count | 18 |
| Ciclo ideal | 30 s |
| Minutos ideales | 410,5 |
| Disponibilidad | 1,000000 |
| Rendimiento | 0,912222 |
| Calidad | 0,978076 |
| OEE | 0,892222 |

Comprobación: `410,5 / 450 = 0,912222`; `803 / 821 = 0,978076`;
`1,000000 × 0,912222 × 0,978076 = 0,892222`.

**Invariantes verificadas en toda la tabla:**

| Invariante | Violaciones |
|---|---:|
| `tiempo_planificado + downtime_planificado = tiempo_calendario` | 0 |
| `tiempo_operativo + downtime_no_planificado = tiempo_planificado` | 0 |
| `good_count <= total_count` y `scrap_count <= total_count` | 0 |
| `fin_at >= inicio_at` | 0 |
| `total_count = good_count + scrap_count` | 0 |

### 3.2 Unidades canónicas

| Magnitud | Unidad | Dónde se usa |
|---|---|---|
| Duración | minutos (`integer`) | tiempo, downtime, MTBF/MTTR calculados |
| Ciclo ideal | segundos (`numeric(10,3)`) | `ciclo_ideal_segundos`; se convierte a minutos en rendimiento |
| Energía | kWh (`numeric(12,4)`) | `energia_kwh` |
| Temperatura | °C (`numeric(6,2)`) | `fact_evento.temperatura_c` |
| Conteos | unidades (`integer`) | total, good, scrap, inspeccionadas |
| Fechas | `timestamptz` UTC | `event_time`, `generated_at`, `ingested_at` |
| Clave de tiempo | `integer` `YYYYMMDD` | `dim_tiempo.id_tiempo` |

La conversión crítica es **ciclo en segundos → minutos**:
`minutos_ideales = ciclo_ideal_segundos × total_count / 60`. Sin esa conversión,
el rendimiento quedaría 60 veces desviado.

### 3.3 Microparadas vs fallas

Regla G6, umbral `microparada_min = 5`:

- **Microparada:** duración `< 5 min` y sin orden CMMS.
- **Falla:** con orden CMMS o duración `>= 5 min`.
- **Falla corta:** falla con duración `< 30 min`.

Se materializa en `fact_parada.es_microparada` y se recalcula en `v_kpi_parada`
(`es_falla`, `es_microparada_regla`, `es_falla_corta`).

| Clasificación | Eventos | Minutos |
|---|---:|---:|
| Microparadas | 43.692 | 109.020 |
| Fallas no planificadas | 2.417 | 43.207 |
| Paradas planificadas | 29.936 | 911.721 |
| **Total** | **76.045** | **1.063.948** |

Ejemplo: M-002, 4 min, sin CMMS ⇒ microparada. M-049, 19 min, OT correctivo
cerrada ⇒ falla. El detalle está en el bloque 1, §4.

---

## 4. Datos IoT: calidad, temporalidad y fuente de verdad

### 4.1 Reglas implementadas

| Problema | Regla | Implementación | Evidencia observada |
|---|---|---|---|
| Duplicados | `ON CONFLICT (source_system, source_event_id)` | `ingest.py`, `load_history.py` | 0 duplicados en `fact_evento` |
| Desordenados | Se aceptan y se marcan `payload.calidad.reordenado = true` | `event_quality.py`; ventana de 5 min | 1 evento reordenado |
| Tardíos | Se aceptan y se marcan `payload.calidad.tardio = true` | `event_quality.py`; > 5 min | 1 evento tardío |
| Timestamps fuera de rango | Rechazo a `fact_evento_rechazado` con motivo | `event_quality.py`; rango `[inicio − 1 d, ahora + 5 min]` | 2 rechazos: 1 futuro, 1 anterior |
| Lecturas faltantes | `v_calidad_senal_iot` compara lecturas vs mínimo por turno y mide `max_gap_min`; no hay *carry-forward* | `10_calidad_senal_iot.sql` | 9.360 filas `ok`; 0 faltantes vs mínimo; `max_gap_min = 210`; `cumple_cadencia_15min = false` en 9.360/9.360 |
| Duplicado de parada con el mismo inicio | Restricción única `(id_maquina, inicio_at)` | `fact_parada` | 0 duplicados |
| Solapes con inicios distintos | **Consolidados en la vista** | `v_parada_consolidada` (unión estricta, sin unir adyacentes) | 0 solapes en el dataset; prueba 10+15 → 20 min (ver `solapes-paradas.md`) |

**Alcance de la consolidación:** `v_kpi_parada` y
`v_kpi_mantenimiento_maquina_turno` usan la vista consolidada. `fact_parada`
permanece crudo y el OEE/Loss Tree siguen usando
`fact_produccion.downtime_no_planificado_min`; por eso la consolidación no altera
el OEE. La implementación y la regresión están en
[`solapes-paradas.md`](./solapes-paradas.md).

**Matiz de lecturas faltantes:** la vista declara el hueco con `max_gap_min` y
`cumple_cadencia_15min`, pero el estado `estado_senal` solo toma `ok`, `incompleta`
o `sin_datos`; **no emite `unknown`**. En este dataset todas las filas quedan `ok`
porque hay al menos 2 lecturas por turno, aunque la cadencia de 15 min no se cumple
(hueco máximo de 210 min). El feed sintético emite 2–5 lecturas por turno, no una
cada 15 min; está documentado en D-022. La Constitución pide `unknown` cuando el
hueco supera 15 min, así que hay una **brecha de etiquetado**: el hueco se informa,
pero no se cambia el estado a `unknown`.

### 4.2 Fuente de verdad

| Dato | Fuente de verdad | Evidencia |
|---|---|---|
| Inicio/fin de una parada | Transición de estado IoT/SCADA | `fact_evento` (`transicion_estado` DOWN/RUNNING); `fact_parada.inicio_at/fin_at` |
| Confirmación de reparación | CMMS | `fact_mantenimiento`; explica la parada, no la define |
| Conteos de producción | MES | `fact_produccion`; `fact_evento` tipo `orden_produccion` |
| Energía y temperatura | IoT/SCADA | `fact_evento.energia_kwh`, `temperatura_c` |
| Unidades buenas/defectuosas/retrabajo | Calidad / MES | `fact_calidad` |
| Calendario de turnos | `dim_turno` / `dim_tiempo` | Turnos A/B/C, 480 min |

**Ejemplo de microparada (M-002, 2026-04-22 08:12 UTC):**

| Evento | `source_event_id` | Tipo | Estado |
|---|---|---|---|
| Transición | `h3a58b2b659-00000012` | `transicion_estado` | `DOWN` |
| Parada | `h3a58b2b659-00000013` | `parada` | `DOWN` (`microparada=true`, 4 min) |
| Transición | `h3a58b2b659-00000014` | `transicion_estado` | `RUNNING` a las 08:16 |

No hay orden CMMS: la parada se define por la transición IoT y se clasifica como
microparada.

**Ejemplo de falla (M-049, 2026-04-22 12:45 UTC):**

| Evento | `source_event_id` | Tipo | Estado |
|---|---|---|---|
| Transición | `h3a58b2b659-00000583` | `transicion_estado` | `DOWN` |
| Parada | `h3a58b2b659-00000584` | `parada` | `DOWN` (19 min) |
| CMMS | `h3a58b2b659-00000586` | `mantenimiento` | OT correctivo cerrada |
| Transición | `h3a58b2b659-00000585` | `transicion_estado` | `RUNNING` a las 13:04 |

La transición IoT define el inicio y el fin; el CMMS explica la reparación, pero
no redefine la parada. En el dataset, **2.401 de las 2.417 fallas** tienen OT; las
16 restantes son fallas de duración `>= 5 min` sin orden CMMS. Las 43.692
microparadas no tienen OT.

### 4.3 Trazabilidad de eventos

`fact_evento` conserva:

- `source_system` y `source_event_id` para idempotencia;
- `event_time` (ocurrió), `generated_at` (se generó) e `ingested_at` (se persistió);
- `estado` (RUNNING/IDLE/DOWN/MAINT);
- `temperatura_c`, `energia_kwh` y `payload` JSONB con la calidad y el detalle.

Los eventos rechazados conservan `motivo` y `payload` en
`fact_evento_rechazado`; no se descartan en silencio.

---

## 5. Hallazgos y brechas

| Hallazgo | Impacto | Estado |
|---|---|---|
| Solapes de paradas | Se consolidan en `v_parada_consolidada`; el OEE no se reconcilia y sigue usando `fact_produccion` | **Resuelto con matiz**; ver `solapes-paradas.md` |
| `unknown` no se emite en `v_calidad_senal_iot` | La cadencia de 15 min se informa, pero el estado no cambia a `unknown` | **Brecha de etiquetado**; documentada en D-022 |
| `fact_produccion` tiene `id_tiempo` en la clave | El grano declarado es orden+máquina+turno+día; en el dataset es 1 fila por orden | **Matiz**; no afecta los KPI actuales |
| Técnico no es tabla separada en Power BI | La dimensión existe en SQL y las columnas están en `v_kpi_mantenimiento`, pero no hay slicer de técnico | **Matiz de exposición** |
| Producto/familia confundido con planta | Cada planta produce una sola familia | **Limitación del escenario**; ver pregunta principal |
| ERP no etiquetado como fuente | `dim_orden`/`dim_producto` existen, pero no hay `source_system='erp'` | **Brecha de trazabilidad**; ver bloque 1, §5.2 |

---

## 6. Cómo responder en la demo

### Modelo dimensional

1. Abrir pgAdmin y mostrar las 4 tablas de hechos y sus claves únicas.
2. Mostrar los recuentos: 28.080 producciones, 76.045 paradas, 2.628
   mantenimientos y 28.080 inspecciones.
3. Mostrar las 10 dimensiones y las 7 pedidas.
4. Aclarar que `fact_evento` y `fact_evento_rechazado` son capa cruda/cuarentena,
   no hechos analíticos.

### Jerarquías

1. Mostrar el panel de campos con `v_dim_maquina → Ubicación` y
   `v_dim_producto → Producto`.
2. Mostrar la página 02 con la matriz máquina-turno y los slicers de planta,
   línea, máquina y turno.
3. Mostrar la prueba de consistencia: 0 discrepancias.

### Transformaciones

1. Mostrar una fila de `fact_produccion` con planificado, runtime, counts y ciclo.
2. Recalcular A, P, Q y OEE en pantalla.
3. Mostrar las invariantes: 0 violaciones.

### IoT

1. Mostrar un evento duplicado rechazado y uno fuera de rango en
   `fact_evento_rechazado`.
2. Mostrar un evento tardío/reordenado con `payload.calidad`.
3. Mostrar `v_calidad_senal_iot` con `max_gap_min` y
   `cumple_cadencia_15min`.
4. Mostrar M-002 (microparada) y M-049 (falla con OT) para explicar la fuente de
   verdad.

---

## Anexo A. Comandos de reproducción

### A.1 Hechos y dimensiones

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select 'dim_planta' t,count(*) from dim_planta union all select 'dim_linea',count(*) from dim_linea union all select 'dim_maquina',count(*) from dim_maquina union all select 'dim_turno',count(*) from dim_turno union all select 'dim_producto',count(*) from dim_producto union all select 'dim_familia',count(*) from dim_familia union all select 'dim_causa',count(*) from dim_causa union all select 'dim_tiempo',count(*) from dim_tiempo union all select 'dim_tecnico',count(*) from dim_tecnico union all select 'dim_orden',count(*) from dim_orden union all select 'fact_produccion',count(*) from fact_produccion union all select 'fact_parada',count(*) from fact_parada union all select 'fact_mantenimiento',count(*) from fact_mantenimiento union all select 'fact_calidad',count(*) from fact_calidad;"
```

### A.2 Duplicados de grano

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select 'prod_dups' k,count(*) from (select id_orden,id_maquina,id_turno,id_tiempo from fact_produccion group by 1,2,3,4 having count(*)>1) x union all select 'parada_dups',count(*) from (select id_maquina,inicio_at from fact_parada group by 1,2 having count(*)>1) x union all select 'mant_dups',count(*) from (select codigo_orden_trabajo from fact_mantenimiento group by 1 having count(*)>1) x union all select 'calidad_dups',count(*) from (select codigo_inspeccion from fact_calidad group by 1 having count(*)>1) x;"
```

### A.3 Invariantes de producción

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select count(*) as filas, count(*) filter (where tiempo_planificado_min + downtime_planificado_min <> tiempo_calendario_min) as mal_calendario, count(*) filter (where tiempo_operativo_min + downtime_no_planificado_min <> tiempo_planificado_min) as mal_runtime, count(*) filter (where good_count > total_count or scrap_count > total_count) as mal_conteos, count(*) filter (where total_count <> good_count + scrap_count) as no_cuadra from fact_produccion;"
```

### A.4 Transformaciones y OEE

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select count(*) as filas, count(*) filter (where abs(minutos_ideales - round(ciclo_ideal_segundos*total_count/60.0,6)) > 1e-6) as mal_min_ideales, count(*) filter (where abs(oee - round(disponibilidad*rendimiento*calidad,6)) > 1e-6) as mal_oee from v_kpi_produccion;"
```

### A.5 Microparadas y fallas

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select es_planificada, es_microparada, count(*) as eventos, sum(duracion_min) as minutos from fact_parada group by 1,2 order by 1,2;"
```

### A.6 Calidad de señal IoT

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select estado_senal, count(*) as filas, sum(lecturas) as lecturas, sum(lecturas_faltantes) as faltantes, max(max_gap_min) as max_gap from v_calidad_senal_iot group by 1 order by 1; select cumple_cadencia_15min, count(*) from v_calidad_senal_iot group by 1;"
```

### A.7 Cuarentena y marcas de calidad

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select motivo, count(*) from fact_evento_rechazado group by 1; select count(*) as tardios from fact_evento where payload->'calidad'->>'tardio'='true'; select count(*) as reordenados from fact_evento where payload->'calidad'->>'reordenado'='true';"
```

### A.8 Relaciones del modelo

```powershell
(Select-String -Path "powerbi\final\MetalNova.SemanticModel\definition\relationships.tmdl" -Pattern "^relationship ").Count
```

---

## Anexo B. Trazabilidad documental

| Tema | Archivo |
|---|---|
| Modelo dimensional | `specs/CONSTITUTION.md` §5; `docs/DATA_DICTIONARY.md` |
| Granos y claves | `docs/DATA_DICTIONARY.md`; `sql/schema/02_hechos.sql` |
| Transformaciones | `sql/views/03_kpi_oee.sql`; `v_kpi_produccion` |
| Unidades | `docs/DATA_DICTIONARY.md` §Convenciones |
| Microparadas/fallas | `specs/CONSTITUTION.md` §7.3; `docs/DATA_DICTIONARY.md` |
| IoT y fuente de verdad | `specs/CONSTITUTION.md` §7; `python/src/event_quality.py`; `sql/views/10_calidad_senal_iot.sql` |
| Relaciones y jerarquías | `powerbi/final/MetalNova.SemanticModel/definition/` |
| Validación de KPI | `python/src/validate_data.py`; `specs/005-kpi-y-vistas/verification.md` |
