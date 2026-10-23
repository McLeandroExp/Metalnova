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
| `perfil_rendimiento` | `text` | CHECK | `estandar`, `desgastada`, `critica`, `calidad`, `energia`; solo lo aplica el escenario `calibracion` |

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
| `categoria` | `text` | | Falla, Cambio, Ajuste, Logística, Microparada, Mantenimiento, Calidad, Descanso, Otro |
| `es_planificada` | `boolean` | | `true` = parada planificada (incluye `DESCANSO`, causa 13) |

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
| `causa_detalle` | `text` | | descripción; `Ingesta 004: …` identifica paradas simuladas |

**Unicidad:** `(id_maquina, inicio_at)`.

**Regla de clasificación:** una parada es microparada si dura `< 5 min` y no tiene orden CMMS;
es falla si tiene orden CMMS o dura `>= 5 min`. Los descansos de turno se registran como parada
planificada con causa `DESCANSO`, de modo que el downtime planificado del turno queda trazado.

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
| `run_id` | `text` | | `hist-<hash>` (003) o `sim-<timestamp>-<sufijo>` (004) |
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

## Ingesta continua simulada (incremento 004)

El simulador inserta eventos **por transición** desde `source_system = 'iot'`:

| `tipo_evento` | Cuándo | `estado` | `payload` |
|---|---|---|---|
| `transicion_estado` | arranque de una parada, fin de una parada o cambio de estado | `DOWN` / `RUNNING` | `transicion`, `causa`, `origen` |
| `parada` | inicio de un episodio | `DOWN` | `causa`, `duracion_min`, `planificada`, `microparada`, `origen` |

- `source_event_id` es estable: `sim-<down|parada|up|sc-down|sc-parada>-<máquina>-<epoch>`.
  La clave única `(source_system, source_event_id)` y `ON CONFLICT DO NOTHING` hacen la ingesta
  idempotente.
- `event_time` es el inicio del slot simulado; `generated_at` es el instante real de generación e
  `ingested_at` el de persistencia. La latencia de pipeline es `ingested_at − generated_at`.
- Las paradas se escriben en `fact_parada` con `causa_detalle = 'Ingesta 004: …'` (microparada
  simulada, falla simulada o escenario). El escenario `stop` usa 20 min y causa `F-MEC`.
- No se añadió `run_id` a `fact_parada`: el marcador en `causa_detalle` es suficiente para
  trazabilidad y evita cambiar el esquema del 002.

---

## Vistas base

| Vista | Contenido |
|---|---|
| `v_produccion_detalle` | `fact_produccion` + todas las dimensiones conformadas |
| `v_parada_detalle` | `fact_parada` + máquina, línea, planta, turno, tiempo, causa |
| `v_mantenimiento_detalle` | `fact_mantenimiento` + máquina, técnico, causa, turno, tiempo |
| `v_calidad_detalle` | `fact_calidad` + máquina, producto, familia, turno, tiempo, causa |

---

## Vistas KPI (incremento 005)

Las vistas KPI son el **contrato analítico** para Power BI. Se aplican con
`sql/apply_all.sql` y viven en `sql/views/02_kpi_base.sql` a
`08_alerta_maquina_critica.sql`. Todas son idempotentes (`CREATE OR REPLACE VIEW`).

**Regla de agregación:** los porcentajes nunca se promedian. Cada vista agrega
sumando numeradores y denominadores y recién divide al final. Por eso el OEE de
una planta no es el promedio de los OEE de sus máquinas.

### Parámetros de reglas (`v_kpi_parametros`)

| Parámetro | Valor | Uso |
|---|---:|---|
| `microparada_min` | 5 | duración máxima de una microparada |
| `falla_corta_min` | 30 | duración máxima de una falla corta |
| `mtbf_umbral_h` | 20 | umbral de alerta de MTBF |
| `oee_umbral` | 0.55 | umbral de alerta de OEE (55 %) |
| `downtime_umbral_min` | 120 | umbral de downtime no planificado por turno |
| `temperatura_umbral_c` | 85 | temperatura máxima admisible |
| `temperatura_ventana_min` | 15 | ventana de referencia para la regla de temperatura |
| `temperatura_lecturas_min` | 2 | lecturas altas consecutivas para 15 min |
| `senal_lecturas_turno_min` | 2 | lecturas de proceso mínimas por turno en el feed sintético |

### Vistas base de hechos

| Vista | Grano | Contenido |
|---|---|---|
| `v_kpi_produccion` | fila de `fact_produccion` | dimensiones + A/P/Q/OEE, scrap, energía/unidad buena, downtime |
| `v_kpi_calidad` | inspección | dimensiones + tasa de defectos, retrabajo y FPY |
| `v_kpi_parada` | parada | dimensiones + regla G6 (`es_falla`, `es_microparada_regla`, `es_falla_corta`) |
| `v_kpi_mantenimiento` | orden de trabajo | dimensiones + tipo/estado + `es_correctivo_cerrado` |

### OEE

| Vista | Grano |
|---|---|
| `v_kpi_oee_planta_dia` | fecha × planta |
| `v_kpi_oee_linea_dia` | fecha × línea |
| `v_kpi_oee_maquina_dia` | fecha × máquina |
| `v_kpi_oee_maquina_turno` | fecha × máquina × turno |
| `v_kpi_oee_producto_dia` | fecha × producto |

Todas exponen `tiempo_planificado_min`, `tiempo_operativo_min`,
`downtime_no_planificado_min`, `total_count`, `good_count`, `scrap_count`,
`minutos_ideales`, `disponibilidad`, `rendimiento`, `calidad`, `oee`,
`scrap_rate`, `energia_por_unidad_buena` y
`downtime_no_planificado_pct`.

### Mantenimiento y confiabilidad

| Vista | Grano | Contenido |
|---|---|---|
| `v_kpi_mantenimiento_maquina_turno` | fecha × máquina × turno | MTBF, MTTR, downtime, fallas, microparadas, fallas cortas |
| `v_kpi_mantenimiento_maquina_dia` | fecha × máquina | agregado diario |
| `v_kpi_mantenimiento_maquina_mes` | mes × máquina | agregado mensual |
| `v_kpi_mantenimiento_planta_dia` | fecha × planta | vista ejecutiva |
| `v_kpi_confiabilidad_apoyo_maquina_dia` | fecha × máquina | microparadas y fallas cortas por 100 h |

`v_kpi_mantenimiento_maquina_turno` incluye claves con producción, parada o
mantenimiento. Así, una parada de la ingesta 004 sin fila de producción aparece
con `tiempo_operativo_min = 0`, `mtbf_h = NULL` y el downtime medido desde
`fact_parada`.

### Calidad y energía

| Vista | Grano | Contenido |
|---|---|---|
| `v_kpi_calidad_maquina_dia` | fecha × máquina | scrap, FPY, defectos, retrabajo, energía/unidad buena |
| `v_kpi_calidad_producto_dia` | fecha × producto | ídem por producto/familia |

### Loss Tree

| Vista | Grano | Contenido |
|---|---|---|
| `v_loss_tree` | fila de producción | pérdidas de disponibilidad, rendimiento y calidad en minutos equivalentes |
| `v_loss_tree_maquina_mes` | mes × máquina | agregado para Pareto y drill-down |

### Alerta de máquina crítica

| Vista | Grano | Contenido |
|---|---|---|
| `v_alerta_maquina_critica` | fecha × máquina × turno | cuatro condiciones, severidad, acciones, responsables y `es_ultimo_turno_maquina` |
| `v_alerta_ultimo_turno` | fecha × máquina × turno | subconjunto `es_ultimo_turno_maquina = true` y `tiene_alerta = true` |
| `v_calidad_senal_iot` | fecha × máquina | lecturas, esperadas, faltantes, huecos y estado `ok`/`incompleta`/`sin_datos` |

La vista de alertas evalúa el turno completo. El informe usa
`v_alerta_ultimo_turno` para la tabla de alertas, de modo que la regla no dependa
de filtros visuales.

---

## Volumen del histórico sintético (incremento 003)

Ejecución canónica del 003: semilla 42, 180 días (2026-04-22 → 2026-10-18), escenario
`degradado` (405.995 eventos; OEE 84,47 % global). Se conserva como referencia histórica.

La ejecución **calibrada del 006** usa la misma semilla y rango, escenario `calibracion`,
`run_id = hist-h3a58b2b659`:

| Tabla | Filas |
|---|---:|
| `dim_orden` | 28.080 |
| `fact_produccion` | 28.080 |
| `fact_parada` | 76.021 |
| `fact_mantenimiento` | 2.628 |
| `fact_calidad` | 28.080 |
| `fact_evento` | 401.787 |

El escenario calibrado añade 43 eventos y 21 paradas de la ingesta simulada 004; los KPI
históricos se calculan solo sobre los 180 días. El detalle de ambas ejecuciones está en
`specs/003-generador-historico/verification.md` y `specs/006-powerbi/verification.md`.

### Factores de calibración

| Planta | Rendimiento | Fallas | Calidad | Energía |
|---|---:|---:|---:|---:|
| P-NORTE | 0,934 | 0,90 | 1,000 | 1,00 |
| P-CENTRO | 0,898 | 1,00 | 0,995 | 1,05 |
| P-SUR | 0,873 | 1,15 | 0,985 | 1,10 |

Perfiles persistentes: `desgastada` (rendimiento 0,87; fallas 1,45; reparación 1,10;
microparadas 1,20), `critica` (0,76; 2,20; 1,40; 1,50), `calidad` (calidad 0,94),
`energia` (energía 1,70) y `estandar` (neutro). La configuración completa se registra en
`data/processed/manifest.json` y en `docs/DECISIONS.md` (D-020).

---

## Definiciones de KPI

| KPI | Fórmula | Notas |
|---|---|---|
| OEE | Disponibilidad × Rendimiento × Calidad | ponderado por denominador; nunca promedio de porcentajes |
| Disponibilidad | `tiempo_operativo_min / tiempo_planificado_min` | excluye descansos y paradas planificadas |
| Rendimiento | `(ciclo_ideal_segundos × total_count / 60) / tiempo_operativo_min` | ciclo en segundos, tiempo en minutos |
| Calidad | `good_count / total_count` | |
| MTBF | `(tiempo_operativo_min / 60) / fallas` | fallas = paradas no planificadas según regla G6; `NULL` si no hay runtime o fallas |
| MTTR | `SUM(duracion_min de correctivo cerrado) / nº reparaciones` | `NULL` si no hay reparaciones |
| Downtime no planificado | `downtime_no_planificado_min / tiempo_planificado_min` | desde `fact_produccion`; si no hay producción, la vista de mantenimiento usa los minutos de `fact_parada` |
| Scrap Rate | `scrap_count / total_count` | |
| FPY | `(unidades_inspeccionadas − unidades_retrabajo) / unidades_inspeccionadas` | `NULL` si no hay inspecciones |
| Energía por Unidad Buena | `energia_kwh / good_count` | `NULL` si no hay unidades buenas |
| Microparadas | conteo y `SUM(duracion_min)` de paradas no planificadas con duración < 5 min y sin CMMS | indicador de apoyo |
| Microparadas por 100 h | `100 × microparadas / (tiempo_operativo_min / 60)` | normaliza por horas operativas |
| Fallas cortas | fallas con `duracion_min < 30` | frecuencia de fallas breves |
| MTBF corto | `(tiempo_operativo_min / 60) / fallas_cortas` | `NULL` si no hay fallas cortas |
| Fallas cortas por 100 h | `100 × fallas_cortas / (tiempo_operativo_min / 60)` | frecuencia normalizada |
| Loss Tree — disponibilidad | `downtime_no_planificado_min` | minutos equivalentes perdidos |
| Loss Tree — rendimiento | `GREATEST(tiempo_operativo_min − minutos_ideales, 0)` | minutos equivalentes perdidos |
| Loss Tree — calidad | `scrap_count × ciclo_ideal_segundos / 60` | minutos equivalentes perdidos |
| Loss Tree — participación | `pérdida_categoría / minutos_perdidos_total` | `NULL` si el total es 0 |
| Alerta de máquina crítica | OEE < 55 % **o** MTBF < 20 h **o** temperatura > 85 °C durante ≥ 15 min **o** downtime > 120 min/turno | severidad `critica` si se cumplen ≥ 2 condiciones; el OEE se compara redondeado a 6 decimales para estabilizar el borde exacto de 55 % |

**Ventana de la alerta:** un turno (máquina × turno × fecha). El feed sintético
emite **dos lecturas de proceso por turno** (minutos 90 y 300) y cinco cuando hay
excursión térmica (minutos 300–360). Se exigen al menos dos lecturas > 85 °C en
el turno; la vista expone `minutos_temp_alta_estimados = lecturas × 15` como
aproximación, no como una medición continua. La cadencia ideal de 15 min se
informa en `v_calidad_senal_iot.cumple_cadencia_15min` y no se oculta: el feed
sintético no la cumple.

**Unidades en el informe:** las fórmulas no exigen una unidad de presentación
concreta. Las tarjetas muestran tiempos en **horas** (MTBF, MTTR, downtime y
pérdida) y las tablas/matrices conservan **minutos** para el detalle operativo.
Los conteos se muestran enteros, los porcentajes con 2 decimales, el costo con 2
decimales y la energía por unidad buena con 4 decimales. Power BI no debe usar
unidades automáticas de miles/millones (`labelDisplayUnits = 1D`).

**Casos borde:** toda división por cero devuelve `NULL` de forma intencional y
documentada; no se propaga `NaN`. Un turno sin producción no genera filas en las
vistas OEE y queda excluido de los promedios ponderados. Una máquina sin fallas
tiene MTBF `NULL`; sin reparaciones, MTTR `NULL`; sin fallas cortas, MTBF corto
`NULL`; sin inspecciones, FPY `NULL`. En el Loss Tree, si no hay pérdidas, las
participaciones son `NULL`. La alerta trata una métrica indefinida como condición
no cumplida. Estos casos se ejercitan en `python/src/validate_data.py` con una
transacción de prueba que se revierte.

---

## Reglas de clasificación

| Regla | Definición |
|---|---|
| Microparada | duración < 5 min **y** sin orden CMMS asociada |
| Falla | con orden CMMS **o** duración ≥ 5 min |
| Falla corta | falla con duración < 30 min |
| Parada planificada | `dim_causa.es_planificada = true` (mantenimiento preventivo, cambio de producto, setup) |
| Temperatura alta | lectura > 85 °C; ≥ 2 lecturas en el turno para la regla de alerta |

## Calidad y temporalidad de eventos IoT (G5)

El ingestor aplica las reglas de la Constitución §7.1 antes de insertar:

| Regla | Implementación | Evidencia |
|---|---|---|
| Duplicados | `ON CONFLICT (source_system, source_event_id)` | `validate_iot.py` y 004 |
| Timestamp fuera de rango | rechazo a `fact_evento_rechazado` con `motivo` (`timestamp_futuro`, `timestamp_anterior_al_rango`, `event_time_nulo`) | `scenario invalid` + `validate_iot.py` |
| Evento tardío | se acepta y se marca `payload.calidad.tardio = true` si llega más de 5 min después | `scenario invalid` |
| Evento reordenado | se acepta y se marca `payload.calidad.reordenado = true` si su `event_time` es anterior al último evento de la máquina | `scenario invalid` |
| Lecturas faltantes | `v_calidad_senal_iot` compara lecturas recibidas con `senal_lecturas_turno_min` y expone `max_gap_min`; si falta cobertura, el estado es `incompleta` | vista + `04_iot.sql` |
| Cadencia de 15 min | se informa `cumple_cadencia_15min`; no se rellena con *carry-forward* | vista + decisión D-022 |

**No se inventan lecturas.** Cuando falta una muestra, el hueco se declara
(`incompleta`/`unknown` en el diagnóstico) en lugar de fabricar un valor por
*carry-forward*. La cuarentena conserva payload y motivo; nunca se descarta un
evento en silencio.

**Cadencia del feed sintético.** El generador histórico emite dos lecturas por
turno, no una cada 15 min. Por eso la vista de señal usa como mínimo
`senal_lecturas_turno_min = 2` y reporta la cadencia ideal por separado. Esta
diferencia está documentada en D-022 y no se presenta como telemetría real.

## Trazabilidad KPI ↔ vista (AC-505)

| KPI / regla | Vista de contrato | Fuente primaria |
|---|---|---|
| OEE, A, P, Q | `v_kpi_oee_*` | `fact_produccion` |
| Scrap Rate, energía/unidad buena | `v_kpi_oee_*`, `v_kpi_calidad_*` | `fact_produccion` |
| FPY, defectos, retrabajo | `v_kpi_calidad_*` | `fact_calidad` |
| MTBF, MTTR, downtime | `v_kpi_mantenimiento_*` | `fact_produccion`, `fact_parada`, `fact_mantenimiento` |
| Microparadas y fallas cortas | `v_kpi_confiabilidad_apoyo_maquina_dia` | `fact_parada` |
| Loss Tree | `v_loss_tree*` | `fact_produccion` |
| Alerta de máquina crítica | `v_alerta_maquina_critica` | `fact_produccion`, `fact_parada`, `fact_mantenimiento`, `fact_evento` |
| Alerta del último turno | `v_alerta_ultimo_turno` | `v_alerta_maquina_critica` |
| Calidad de señal IoT | `v_calidad_senal_iot` | `fact_evento`, `fact_produccion` |
| Calidad por producto | `v_kpi_calidad_producto_dia` | `fact_calidad`, `fact_produccion` |

La validación independiente `python src/validate_data.py` recalcula estos KPI
desde los hechos y compara con las vistas con tolerancia `1e-9` (más estricta
que el 0,1 % del spec).

## Latencia

| Métrica | Fórmula | Uso |
|---|---|---|
| Latencia de pipeline | `ingested_at − generated_at` | **objetivo < 10 min** |
| Desfase de evento | `ingested_at − event_time` | puede ser negativa con reloj simulado |

Las definiciones son idénticas en SQL, Python y DAX. La vista es el contrato único; DAX solo agrega.
