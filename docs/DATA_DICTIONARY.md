# Diccionario de datos — MetalNova Smart Factory BI

Esquema PostgreSQL `public`, base `metalinova`. Modelo estrella con **6 tablas de hechos** y
**10 dimensiones conformadas**. Todos los datos son **sintéticos**.

## Convenciones

| Magnitud | Unidad canónica |
|---|---|
| Duración | minutos (`integer`) |
| Tiempo de ciclo ideal | segundos (`numeric(10,3)`) |
| Energía | kWh (`numeric(12,4)`) |
| Temperatura | °C (`numeric(6,2)`) |
| Conteos | unidades (`integer`) |
| Fechas | `timestamptz` (almacenamiento UTC) |
| Clave de tiempo | `integer` `YYYYMMDD` |

Se distinguen tres marcas temporales: `event_time` (ocurrió), `generated_at` (se generó) e
`ingested_at` (se persistió).

---

## Dimensiones

### `dim_planta` — grano: una planta

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_planta` | `smallint` | PK | |
| `codigo` | `text` | UNIQUE | `P-NORTE`, `P-CENTRO`, `P-SUR` |
| `nombre` | `text` | | |
| `ciudad` | `text` | | |
| `pais` | `text` | | |

### `dim_linea` — grano: una línea

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_linea` | `smallint` | PK | |
| `id_planta` | `smallint` | FK → `dim_planta` | |
| `codigo` | `text` | UNIQUE | |
| `nombre` | `text` | | |

### `dim_maquina` — grano: una máquina

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_maquina` | `integer` | PK | 1..52 |
| `id_linea` | `smallint` | FK → `dim_linea` | |
| `codigo` | `text` | UNIQUE | `M-001`..`M-052` |
| `nombre` | `text` | | |
| `tipo` | `text` | | CNC, Prensa, Inyectora, Soldadora, Rectificadora |
| `criticidad` | `text` | CHECK | A / B / C |
| `fabricante`, `modelo` | `text` | | |
| `fecha_alta` | `date` | | |
| `activa` | `boolean` | | |

### `dim_familia` — grano: una familia de producto

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_familia` | `smallint` | PK | |
| `codigo` | `text` | UNIQUE | |
| `nombre` | `text` | | Frenos, Suspensión, Transmisión |

### `dim_producto` — grano: un producto

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_producto` | `integer` | PK | |
| `id_familia` | `smallint` | FK → `dim_familia` | |
| `codigo` | `text` | UNIQUE | `PRD-001`..`PRD-012` |
| `nombre` | `text` | | |
| `unidad_medida` | `text` | | |

### `dim_turno` — grano: un turno

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_turno` | `smallint` | PK | |
| `codigo` | `text` | UNIQUE | A / B / C |
| `nombre` | `text` | | |
| `hora_inicio`, `hora_fin` | `time` | | |
| `duracion_min` | `smallint` | CHECK > 0 | 480 |
| `cruza_medianoche` | `boolean` | | Turno C |

### `dim_causa` — grano: una causa

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_causa` | `integer` | PK | |
| `codigo` | `text` | UNIQUE | |
| `descripcion` | `text` | | |
| `categoria` | `text` | | Falla, Cambio, Ajuste, Logística, Microparada, Mantenimiento, Calidad, Otro |
| `es_planificada` | `boolean` | | `true` = parada planificada |

### `dim_tecnico` — grano: un técnico

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_tecnico` | `integer` | PK | |
| `codigo` | `text` | UNIQUE | |
| `nombre` | `text` | | |
| `especialidad` | `text` | | Mecánica, Eléctrica, Automatización, Calidad |
| `activo` | `boolean` | | |

### `dim_tiempo` — grano: un día

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_tiempo` | `integer` | PK | `YYYYMMDD` |
| `fecha` | `date` | UNIQUE | |
| `anio`, `trimestre`, `mes`, `dia` | `smallint` | | |
| `semana_iso` | `smallint` | | |
| `dia_semana` | `smallint` | | 1 = lunes |
| `nombre_dia` | `text` | | |
| `es_fin_semana` | `boolean` | | |
| `anio_mes` | `text` | | `YYYY-MM` |

### `dim_orden` — grano: una orden de producción

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_orden` | `bigint` | PK | |
| `codigo_orden` | `text` | UNIQUE | |
| `id_producto` | `integer` | FK → `dim_producto` | |
| `cantidad_planificada` | `integer` | CHECK ≥ 0 | |
| `fecha_plan` | `date` | | |
| `estado` | `text` | CHECK | planificada / en_curso / cerrada / cancelada |

---

## Hechos

### `fact_produccion` — grano: orden + máquina + turno + día

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_produccion` | `bigserial` | PK | |
| `id_orden` | `bigint` | FK compuesta | |
| `id_maquina` | `integer` | FK → `dim_maquina` | |
| `id_producto` | `integer` | FK compuesta | debe coincidir con `dim_orden.id_producto` |
| `id_turno` | `smallint` | FK → `dim_turno` | |
| `id_tiempo` | `integer` | FK → `dim_tiempo` | |
| `inicio_at`, `fin_at` | `timestamptz` | | `fin >= inicio` |
| `tiempo_calendario_min` | `integer` | CHECK ≥ 0 | duración del turno |
| `tiempo_planificado_min` | `integer` | CHECK ≥ 0 | calendario − downtime planificado |
| `downtime_planificado_min` | `integer` | CHECK ≥ 0 | descansos, mantenimiento programado |
| `tiempo_operativo_min` | `integer` | CHECK ≥ 0 | runtime = planificado − downtime no planificado |
| `downtime_no_planificado_min` | `integer` | CHECK ≥ 0 | incluye microparadas |
| `total_count` | `integer` | CHECK ≥ 0 | unidades totales |
| `good_count` | `integer` | CHECK ≥ 0 | unidades buenas |
| `scrap_count` | `integer` | CHECK ≥ 0 | unidades rechazadas |
| `ciclo_ideal_segundos` | `numeric(10,3)` | CHECK > 0 | |
| `energia_kwh` | `numeric(12,4)` | CHECK ≥ 0 | |

**Invariantes verificadas:**

```text
tiempo_planificado_min + downtime_planificado_min = tiempo_calendario_min
tiempo_operativo_min   + downtime_no_planificado_min = tiempo_planificado_min
good_count <= total_count  y  scrap_count <= total_count
```

**Unicidad:** `(id_orden, id_maquina, id_turno, id_tiempo)`.

### `fact_parada` — grano: un episodio de parada

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_parada` | `bigserial` | PK | |
| `id_maquina` | `integer` | FK → `dim_maquina` | |
| `id_turno` | `smallint` | FK → `dim_turno` | turno del inicio |
| `id_tiempo` | `integer` | FK → `dim_tiempo` | fecha del inicio |
| `id_causa` | `integer` | FK → `dim_causa` | |
| `id_mantenimiento` | `bigint` | FK → `fact_mantenimiento` | nullable |
| `inicio_at`, `fin_at` | `timestamptz` | | `fin` nullable si sigue abierta |
| `duracion_min` | `integer` | CHECK ≥ 0 | |
| `es_planificada` | `boolean` | | |
| `es_microparada` | `boolean` | | |
| `causa_detalle` | `text` | | |

**Unicidad:** `(id_maquina, inicio_at)`.

### `fact_mantenimiento` — grano: una orden de trabajo

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_mantenimiento` | `bigserial` | PK | |
| `codigo_orden_trabajo` | `text` | UNIQUE | |
| `id_maquina` | `integer` | FK → `dim_maquina` | |
| `id_tecnico` | `integer` | FK → `dim_tecnico` | |
| `id_causa` | `integer` | FK → `dim_causa` | causa raíz |
| `id_turno` | `smallint` | FK → `dim_turno` | |
| `id_tiempo` | `integer` | FK → `dim_tiempo` | |
| `tipo` | `text` | CHECK | preventivo / correctivo / predictivo / mejora |
| `inicio_at`, `fin_at` | `timestamptz` | | |
| `duracion_min` | `integer` | CHECK ≥ 0 | |
| `costo_estimado_usd` | `numeric(12,2)` | CHECK ≥ 0 | |
| `estado` | `text` | CHECK | abierta / cerrada |

### `fact_calidad` — grano: una inspección/lote

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_calidad` | `bigserial` | PK | |
| `codigo_inspeccion` | `text` | UNIQUE | |
| `codigo_lote` | `text` | | |
| `id_maquina` | `integer` | FK → `dim_maquina` | |
| `id_producto` | `integer` | FK → `dim_producto` | |
| `id_turno` | `smallint` | FK → `dim_turno` | |
| `id_tiempo` | `integer` | FK → `dim_tiempo` | |
| `id_causa` | `integer` | FK → `dim_causa` | nullable |
| `inspeccion_at` | `timestamptz` | | |
| `unidades_inspeccionadas` | `integer` | CHECK ≥ 0 | |
| `unidades_buenas` | `integer` | CHECK ≥ 0 | |
| `unidades_defectuosas` | `integer` | CHECK ≥ 0 | |
| `unidades_retrabajo` | `integer` | CHECK ≥ 0 | subconjunto de procesadas |
| `es_retrabajo` | `boolean` | | |

### `fact_evento` — grano: un evento crudo de origen

| Columna | Tipo | Clave | Notas |
|---|---|---|---|
| `id_evento` | `bigserial` | PK | |
| `source_system` | `text` | UNIQUE compuesta | iot / scada / mes / cmms / erp / calidad / turnos |
| `source_event_id` | `text` | UNIQUE compuesta | clave idempotente |
| `tipo_evento` | `text` | CHECK | transicion_estado / lectura_proceso / orden_produccion / parada / mantenimiento / inspeccion |
| `id_maquina` | `integer` | FK → `dim_maquina` | nullable |
| `event_time` | `timestamptz` | | hora del evento |
| `generated_at` | `timestamptz` | | hora de generación |
| `ingested_at` | `timestamptz` | | hora de persistencia |
| `run_id` | `text` | | identificador de ejecución |
| `estado` | `text` | | RUNNING / IDLE / DOWN / MAINT |
| `temperatura_c` | `numeric(6,2)` | CHECK −20..150 | |
| `energia_kwh` | `numeric(12,4)` | CHECK ≥ 0 | |
| `payload` | `jsonb` | | evento original |

**Unicidad:** `(source_system, source_event_id)`.

### `fact_evento_rechazado` — grano: un evento descartado

| Columna | Tipo | Notas |
|---|---|---|
| `id_rechazo` | `bigserial` PK | |
| `source_system`, `source_event_id` | `text` | |
| `motivo` | `text` | causa del rechazo |
| `payload` | `jsonb` | evento original |
| `recibido_at` | `timestamptz` | |

---

## Vistas base

| Vista | Contenido |
|---|---|
| `v_produccion_detalle` | `fact_produccion` + todas las dimensiones conformadas |
| `v_parada_detalle` | `fact_parada` + máquina, línea, planta, turno, tiempo, causa |
| `v_mantenimiento_detalle` | `fact_mantenimiento` + máquina, técnico, causa, turno, tiempo |
| `v_calidad_detalle` | `fact_calidad` + máquina, producto, familia, turno, tiempo, causa |

---

## Definiciones de KPI

| KPI | Fórmula | Notas |
|---|---|---|
| OEE | Disponibilidad × Rendimiento × Calidad | ponderado por denominador; nunca promedio de porcentajes |
| Disponibilidad | `tiempo_operativo_min / tiempo_planificado_min` | excluye descansos y paradas planificadas |
| Rendimiento | `(ciclo_ideal_segundos × total_count / 60) / tiempo_operativo_min` | ciclo en segundos, tiempo en minutos |
| Calidad | `good_count / total_count` | |
| MTBF | tiempo operativo / nº de fallas | fallas = paradas no planificadas según regla |
| MTTR | suma de `duracion_min` de mantenimiento correctivo cerrado / nº de reparaciones | |
| Downtime no planificado | `downtime_no_planificado_min / tiempo_planificado_min` | |
| Scrap Rate | `scrap_count / total_count` | |
| FPY | `(unidades_inspeccionadas − unidades_retrabajo) / unidades_inspeccionadas` | |
| Energía por Unidad Buena | `energia_kwh / good_count` | |
| Microparadas | conteo y duración donde `es_microparada` | indicador de apoyo |

**Casos borde:** división por cero ⇒ `NULL`/0 documentado; turno sin producción se excluye de los
promedios ponderados; máquina sin fallas ⇒ MTBF no definido (se reporta como `NULL`, no como 0).

---

## Reglas de clasificación

| Regla | Definición |
|---|---|
| Microparada | duración < 5 min **y** sin orden CMMS asociada |
| Falla | con orden CMMS **o** duración ≥ 5 min |
| Parada planificada | `dim_causa.es_planificada = true` (mantenimiento preventivo, cambio de producto, setup) |

## Latencia

| Métrica | Fórmula | Uso |
|---|---|---|
| Latencia de pipeline | `ingested_at − generated_at` | **objetivo < 10 min** |
| Desfase de evento | `ingested_at − event_time` | puede ser negativa con reloj simulado |

Las definiciones son idénticas en SQL, Python y DAX. La vista es el contrato único; DAX solo agrega.
