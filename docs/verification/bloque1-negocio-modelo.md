# Verificación del Bloque 1 — Comprensión del negocio y modelo de datos

> **Todos los datos son sintéticos.** Este documento no presenta telemetría real ni
> resultados de una fábrica. Las cifras corresponden a la base local `metalinova`
> consultada el **2026-10-24**; si se ejecuta una nueva ingesta simulada, los totales
> pueden variar.

- **Alcance:** preguntas de verificación del Bloque 1 (comprensión del negocio,
  modelo de datos y metodología de planificación/alcance).
- **Fuente de verdad:** `specs/CONSTITUTION.md`.
- **Método:** consultas directas a PostgreSQL, revisión del modelo TMDL/PBIR y de
  `specs/003`, `specs/004`, `specs/005`, `specs/006` y `specs/007`.
- **Entorno:** PostgreSQL 16.4 en Docker, base `metalinova`, usuario de consulta
  `metalinova`; Power BI Desktop con conexión DirectQuery.
- **Directorio de verificación:** `docs/verification/`. La respuesta formal a la
  pregunta principal está en
  [`pregunta-principal-business-understanding.md`](./pregunta-principal-business-understanding.md).
  La implementación de solapes está en [`solapes-paradas.md`](./solapes-paradas.md).

## Resumen de veredictos

| # | Pregunta | Veredicto | Evidencia principal |
|---|---|---|---|
| 1 | Volumen y alcance (3 plantas, 52 máquinas, ≥ 90 días, ≥ 200.000 eventos) | **Cumple** | 3 plantas, 6 líneas, 52 máquinas, 180 días y 401.838 eventos; 343.050 son eventos de máquina (IoT/SCADA) |
| 2 | Drill-down Planta → Línea → Máquina → Turno sin duplicar KPIs | **Cumple con matiz** | Jerarquía `Ubicación` en el modelo; 540 comparaciones planta-día y 1.080 línea-día con 0 discrepancias |
| 3 | Solape de dos paradas IoT para la misma máquina | **Cumple con matiz** | `v_parada_consolidada` une solapes estrictos: la prueba 10+15 dio 1 episodio de 20 min y 5 min solapados; el OEE sigue usando `fact_produccion` |
| 4 | Diferenciar microparada de falla real | **Cumple** | Regla G6 (`< 5 min` y sin CMMS = microparada); 43.692 microparadas y 2.417 fallas; ejemplo M-002 vs M-049 |
| 5 | Pregunta principal de Business Understanding | **Cumple en este paquete** | Respuesta formal en [`pregunta-principal-business-understanding.md`](./pregunta-principal-business-understanding.md); los documentos originales no la formalizaban |
| 6 | Fuentes mínimas (IoT/SCADA, MES, CMMS, ERP, calidad, turnos) | **Parcial** | 5 fuentes trazadas; ERP no tiene `source_system='erp'` ni evidencia de eventos ERP |
| 7 | ≥ 200.000 eventos, órdenes, paradas, mantenimientos y calidad en ≥ 90 días | **Cumple** | 401.838 eventos, 28.080 órdenes/producciones, 76.045 paradas, 2.628 mantenimientos, 28.080 inspecciones, 180 días |
| 8 | Latencia de visualización < 10 min | **Cumple** | Latencia de pipeline 0,7–54,9 ms; frescura DirectQuery 0,35 s; intervalo del simulador 60 s |

---

## 1. Volumen y alcance

### Respuesta

**Sí.** El prototipo tiene datos para las 3 plantas, las 6 líneas y las 52 máquinas
del alcance, con 180 días de historia y 401.838 eventos de origen. De ellos,
**343.050 son eventos de máquina** (IoT + SCADA), por encima del mínimo de 200.000.

### Evidencia observada

| Comprobación | Resultado |
|---|---:|
| Plantas | 3 (`P-NORTE`, `P-CENTRO`, `P-SUR`) |
| Líneas | 6 (2 por planta) |
| Máquinas en `dim_maquina` | 52 (22 criticidad A, 20 B, 10 C; todas activas) |
| Máquinas con producción | 52 |
| Máquinas con eventos IoT/SCADA | 52 |
| Días con producción | 180 (`2026-04-22` → `2026-10-18`) |
| Eventos en `fact_evento` | 401.838 |
| Eventos de máquina (IoT/SCADA) | 343.050 |
| Órdenes de producción | 28.080 |
| Paradas | 76.045 |
| Mantenimientos | 2.628 |
| Inspecciones de calidad | 28.080 |

**Composición de los 401.838 eventos:**

| `source_system` | `tipo_evento` | Filas |
|---|---|---:|
| `iot` | `transicion_estado` | 208.229 |
| `iot` | `parada` | 76.045 |
| `scada` | `lectura_proceso` | 58.776 |
| `mes` | `orden_produccion` | 28.080 |
| `calidad` | `inspeccion` | 28.080 |
| `cmms` | `mantenimiento` | 2.628 |
| **Total** | | **401.838** |

El total incluye 401.787 eventos históricos del `run_id hist-h3a58b2b659` y 51
eventos de las ejecuciones simuladas `sim-*`. La ingesta histórica cubre 180 días;
los eventos simulados son posteriores y no alteran la ventana histórica.

**Distribución por planta:**

| Planta | Líneas | Máquinas | Máquinas con producción |
|---|---:|---:|---:|
| P-NORTE | 2 | 18 | 18 |
| P-CENTRO | 2 | 18 | 18 |
| P-SUR | 2 | 16 | 16 |

### Ejemplo para la exposición

> “El prototipo cubre las 3 plantas, 6 líneas y 52 máquinas. La ventana histórica
> es de 180 días, no de 90. Hay 401.838 eventos de origen y 343.050 eventos de
> máquina, muy por encima del mínimo de 200.000. Las 52 máquinas tienen producción
> y eventos.”

### Cómo responderlo en la demo

1. Abrir pgAdmin o ejecutar la consulta del **Anexo A.1**.
2. Mostrar la tabla de recuentos por planta y el total de `fact_evento`.
3. Contrastar con `docs/CUMPLIMIENTO.md` (requisito 6) y
   `specs/003-generador-historico/verification.md`.
4. Si se quiere una captura, usar la salida de la consulta o una vista de pgAdmin.

---

## 2. Trazabilidad de jerarquías

### Respuesta

**Sí, con un matiz de implementación.** El modelo contiene las jerarquías
`Planta → Línea → Máquina` y `Familia → Producto`; las medidas se definen una sola
vez y se agregan sumando numeradores y denominadores, no promediando porcentajes.
El informe permite navegar de planta a línea, máquina y turno mediante los slicers
sincronizados, la matriz máquina-turno y el drill-through.

El matiz: **no hay un único visual con una jerarquía expandible de cuatro niveles**
(Planta → Línea → Máquina → Turno). La jerarquía `Ubicación` existe en el modelo
TMDL (niveles Planta, Línea y Máquina) y el turno se resuelve con `dim_turno` y la
matriz máquina-turno de la página 02. Funcionalmente se puede hacer el recorrido
completo; si la rúbrica exige la flecha de *drill-down* en un solo visual, habría
que añadir ese visual (no está implementado así).

### Evidencia observada

| Comprobación | Resultado |
|---|---|
| Jerarquía `Ubicación` | `v_dim_maquina`: Planta → Línea → Máquina |
| Jerarquía `Producto` | `v_dim_producto`: Familia → Producto |
| Jerarquía `Causa` | `dim_causa`: Categoría → Detalle |
| Jerarquía de tiempo | `dim_tiempo`: Año → Trimestre → Mes → Día |
| Relaciones del modelo | 27 relaciones en `powerbi/final/.../relationships.tmdl`, todas hecho → dimensión |
| Medidas | Definidas una vez en `powerbi/final/measures.dax`; OEE = A × P × Q con `SUM` de numeradores y denominadores |
| Consistencia planta-día vs suma máquina-turno | 540 filas comparadas, **0 discrepancias** (planificado, operativo, total, bueno, minutos ideales y downtime) |
| Consistencia línea-día vs suma máquina-turno | 1.080 filas comparadas, **0 discrepancias** |

**Ejemplo con la planta de peor desempeño (últimos 30 días: 2026-09-19 → 2026-10-18):**

| Nivel | Valor | OEE |
|---|---|---:|
| Planta | P-SUR | 62,04 % |
| Línea | L3-2 | 60,98 % |
| Línea | L3-1 | 63,11 % |
| Máquina | M-047 (L3-2) | 47,47 % |
| Turno de M-047 | A | 49,44 % |
| Turno de M-047 | B | 47,62 % |
| Turno de M-047 | C | 45,33 % |

El OEE de la planta (62,04 %) es el ponderado de sus máquinas y turnos, no el
promedio simple de los OEE. Al filtrar por línea, máquina o turno, la fórmula no
cambia: solo cambia el conjunto de filas que se suma.

### Ejemplo para la exposición

> “Selecciono P-SUR, la planta con peor OEE. Bajo a la línea L3-2, luego a la
> máquina M-047 y al turno C. El OEE de la planta es 62,04 %, el de M-047 es
> 47,47 % y el del turno C es 45,33 %. Los números no se duplican: el KPI se
> calcula sumando los mismos numeradores y denominadores en cada nivel.”

### Cómo responderlo en la demo

1. Abrir la página 01 (Executive) y seleccionar `P-SUR` en el slicer de planta.
2. Ir a la página 02 (OEE & Loss Tree); seleccionar `L3-2` y `M-047`; usar el
   slicer de turno o la matriz máquina-turno.
3. Mostrar que el OEE cambia con el filtro pero la fórmula es la misma.
4. Si se quiere mostrar la jerarquía del modelo, abrir el panel de campos y
   expandir `v_dim_maquina → Ubicación` (Planta, Línea, Máquina).
5. Opcional: ejecutar la consulta de consistencia del **Anexo A.2** y mostrar
   `discrepancias = 0`.

---

## 3. Gestión de fallas IoT: solapes de paradas

### Respuesta

**Cumple con matiz.** El proyecto trata varios problemas de datos sucios y, tras
la implementación D-023, **consolida los solapes en la capa analítica**. La tabla
cruda `fact_parada` conserva los dos episodios para trazabilidad, pero
`v_parada_consolidada` los une y `v_kpi_parada` / `v_kpi_mantenimiento_*` leen de
ella. El matiz: el OEE sigue usando `fact_produccion` y no refleja la
consolidación; si se exige consistencia total, hay que reconciliar
`fact_produccion` en una segunda fase.

### Lo que sí está implementado

| Problema | Regla implementada | Evidencia |
|---|---|---|
| Duplicados exactos | `ON CONFLICT (source_system, source_event_id)` | `fact_evento` sin duplicados; `validate_iot.py` |
| Timestamps fuera de rango | Rechazo a `fact_evento_rechazado` con motivo | 2 rechazos: `timestamp_anterior_al_rango` y `timestamp_futuro` |
| Evento tardío | Se acepta y se marca `payload.calidad.tardio = true` | 1 evento marcado |
| Evento reordenado | Se acepta y se marca `payload.calidad.reordenado = true` | 1 evento marcado |
| Lecturas faltantes | `v_calidad_senal_iot` declara el hueco; no se inventan lecturas | Vista de señal y D-022 |
| Duplicado de una parada con el mismo inicio | Restricción única `(id_maquina, inicio_at)` | `fact_parada` |
| **Solape con inicios distintos** | **Unión de intervalos estrictamente solapados por máquina** | `v_parada_consolidada`; D-023; `sql/validation/05_...sql` |

### Regla de consolidación

- Se unen solo solapes **estrictos**: `a.inicio < b.fin` y `b.inicio < a.fin`.
- **No** se unen intervalos adyacentes (`fin = siguiente inicio`), porque pueden
  tener causas distintas y deben seguir contando para MTBF/fallas.
- La duración es la **unión**, no la suma.
- Atribución: turno/día del inicio; causa del tramo no planificado más largo (si
  todos son planificados, el más largo); OT principal; “no planificado gana” en
  un solape mixto; microparada recalculada con la unión.

### Estado del dataset actual

| Comprobación | Resultado |
|---|---:|
| Pares de paradas solapadas por máquina (crudo) | **0** |
| Episodios crudos / consolidados | 76.045 / 76.045 |
| Minutos crudos / consolidados | 1.063.948 / 1.063.948 |
| Minutos solapados | **0** |
| Paradas abiertas (`fin_at IS NULL`) | **0** |
| Máximo de minutos de parada por máquina-día | 324 min (calendario de 1.440 min) |

El histórico y el simulador **evitan el solape por construcción**:

- `python/src/common/simulation.py` usa `_place(...)` para reservar intervalos
  dentro del turno y no colocar dos paradas en el mismo rango.
- `python/src/simulate_events.py` (líneas 301–309) excluye a las máquinas que ya
  tienen una parada abierta antes de crear una nueva.

Por eso la consolidación es un **no-op** sobre el dataset actual. La vista
empieza a cambiar los KPI cuando se ingieren eventos externos solapados.

### Prueba controlada del comportamiento

Se insertaron dos paradas ficticias para la misma máquina en una transacción
`BEGIN … ROLLBACK` (no quedaron persistidas):

| Parada | Intervalo | Duración |
|---|---|---:|
| A | 10:00 → 10:10 | 10 min |
| B | 10:05 → 10:20 | 15 min |

Resultado observado en `v_parada_consolidada`:

```text
episodios = 1
inicio/fin = 10:00 / 10:20
duracion_min = 20
episodios_origen = 2
minutos_solapados = 5
```

La suma bruta habría sido 25 min; la unión correcta es **20 min**. La prueba
también confirma que dos intervalos adyacentes (10:00–10:10 y 10:10–10:20) siguen
siendo **2 episodios**, no uno, y que en un solape mixto planificado/no
planificado se conserva la causa del tramo no planificado.

### Qué decir en la exposición

> “El dataset actual no contiene solapes: el generador y el simulador los evitan
> por construcción. Para datos externos, la capa analítica usa
> `v_parada_consolidada`: une intervalos estrictamente solapados, no adyacentes,
> y conserva el hecho crudo para trazabilidad. El OEE sigue usando
> `fact_produccion`; la consolidación cambia Pareto, MTBF, fallas y microparadas,
> no el OEE. Esa separación está documentada como matiz.”

### Limitaciones y siguiente fase

- El OEE no se reconcilia con la unión; sigue usando
  `fact_produccion.downtime_no_planificado_min`.
- En un solape mixto planificado/no planificado se aplica “no planificado gana”.
- Un episodio que cruza turno se atribuye al turno de inicio.
- Si hay varias OT, se conserva una principal.
- `fact_parada` crudo sigue admitiendo solapes; la consolidación es analítica.

La evidencia completa está en
[`solapes-paradas.md`](./solapes-paradas.md).

---

## 4. Microparadas vs fallas

### Respuesta

**Sí.** El modelo diferencia una microparada de una falla con la regla G6 de la
Constitución:

- **Microparada:** duración `< 5 min` **y** sin orden CMMS asociada.
- **Falla:** tiene orden CMMS **o** duración `>= 5 min`.
- **Falla corta:** falla con duración `< 30 min`.

La regla se materializa en `fact_parada.es_microparada` y se recalcula en
`v_kpi_parada` (`es_falla`, `es_microparada_regla`, `es_falla_corta`). El umbral
está en `v_kpi_parametros.microparada_min = 5`.

### Evidencia observada

| Indicador | Valor |
|---|---:|
| Microparadas | 43.692 |
| Minutos acumulados de microparadas | 109.020 |
| Fallas no planificadas (sin microparadas) | 2.417 |
| Minutos acumulados de fallas | 43.207 |

**Ejemplo de microparada (M-002, 2026-04-22 08:12):**

| Campo | Valor |
|---|---|
| `fact_parada.id_parada` | 2 |
| Máquina | M-002 |
| Inicio | 2026-04-22 08:12 UTC |
| Duración | 4 min |
| Categoría | Microparada |
| Orden CMMS | Ninguna |
| `es_microparada` | `true` |

Trazabilidad IoT: el evento `h3a58b2b659-00000012` es la transición a `DOWN`, el
`h3a58b2b659-00000013` es el evento de parada con `microparada=true` y
`duracion_min=4`, y el `h3a58b2b659-00000014` es la transición a `RUNNING` a las
08:16. El sensor lo detectó; el CMMS no generó orden.

**Ejemplo de falla real (M-049, 2026-04-22 12:45):**

| Campo | Valor |
|---|---|
| `fact_parada.id_parada` | 98 |
| Máquina | M-049 |
| Inicio | 2026-04-22 12:45 UTC |
| Duración | 19 min |
| Categoría | Falla |
| Orden CMMS | `OT-h3a58b2b659-000002` (correctivo, cerrada) |
| `es_microparada` | `false` |

En este caso hay transición `DOWN`, evento de parada, evento CMMS y transición
`RUNNING` a las 13:04. La orden CMMS explica la parada; no la redefine.

### Ejemplo para la exposición

> “Una microparada es un paro de menos de 5 minutos sin orden de mantenimiento.
> Por ejemplo, M-002 tuvo un paro de 4 minutos el 22 de abril: el IoT lo detectó,
> pero el CMMS no abrió orden. Una falla es un paro con orden CMMS o de 5 minutos
> o más. M-049 tuvo 19 minutos y una orden correctivo cerrada. En el histórico hay
> 43.692 microparadas y 2.417 fallas.”

### Cómo responderlo en la demo

1. Abrir `docs/DATA_DICTIONARY.md` y mostrar la regla G6 y los umbrales.
2. Ejecutar la consulta del **Anexo A.4** para mostrar una microparada y una falla
   con y sin orden CMMS.
3. Abrir la página 03 (Maintenance Reliability) y mostrar los contadores de
   microparadas, fallas cortas y MTBF.
4. Si se quiere, mostrar `v_kpi_confiabilidad_apoyo_maquina_dia` con
   microparadas/100 h y fallas cortas/100 h.

---

## 5. Bloque metodológico a. Planificación y alcance

### 5.1 Pregunta principal

**Cumple en este paquete de verificación.** Los documentos originales no
formalizaban la pregunta, pero este directorio la responde con cifras observadas en
[`pregunta-principal-business-understanding.md`](./pregunta-principal-business-understanding.md).

Pregunta del caso:

> ¿Qué activos, turnos, productos y causas de parada explican la caída del OEE y
> cuál es su impacto en throughput, scrap y costo?

| Componente | Dónde se responde | Evidencia |
|---|---|---|
| Activos | `v_loss_tree`, `v_kpi_oee_maquina_*`; página 02 | Pérdida por planta/máquina y matriz máquina-turno |
| Turnos | `v_kpi_oee_maquina_turno`; matriz máquina-turno | OEE y pérdidas por turno |
| Productos | `v_loss_tree` por producto; `v_kpi_calidad_producto_dia` | Pérdida por producto y scrap por producto |
| Causas de parada | `v_kpi_parada`, `dim_causa`; Pareto de la página 02 | Pareto de downtime por causa |
| Throughput | `v_loss_tree`, minutos equivalentes y unidades | Pérdidas de disponibilidad/rendimiento/calidad |
| Scrap | `v_kpi_calidad_*`, `v_kpi_oee_*` | Scrap rate y unidades |
| Costo | `docs/PLAN_MEJORA.md` | USD 220/h y USD 18/unidad, supuestos declarados; impactos hipotéticos |

**Respuesta directa (resumen):**

- La caída 78,02 % → 66,00 % es **principalmente pérdida de rendimiento**
  (−10,47 pp), no de disponibilidad (−0,47 pp).
- Focos: **P-SUR**, **L3-2**, **M-047**, **turno C**; producto **PRD-009** en los
  últimos 30 días (con la cautela de que producto y planta están confundidos).
- Causas no planificadas principales: **microparadas** (43.692 eventos, 109.020
  min) y **F-MEC** (867 eventos, 15.356 min).
- Impacto: **4.269.957 unidades potenciales no producidas**, **684.643 unidades
  scrap** y una valorización hipotética de **USD 10,67 M** por rendimiento,
  **USD 0,56 M** por disponibilidad y **USD 12,32 M** por scrap en 180 días.

La respuesta completa, con tablas y guion de exposición, está en
[`pregunta-principal-business-understanding.md`](./pregunta-principal-business-understanding.md).

### 5.2 Fuentes mínimas

**Parcial.** Cinco de las seis fuentes están trazadas; el ERP de producción no
tiene una fuente explícita.

| Fuente mínima | Evidencia en el prototipo | Veredicto |
|---|---|---|
| IoT/SCADA | `fact_evento`: `iot` 284.274 + `scada` 58.776; `fact_parada` | **Cumple** |
| MES | `fact_evento`: `mes` 28.080; `fact_produccion` 28.080; `dim_orden` 28.080 | **Cumple** |
| CMMS | `fact_evento`: `cmms` 2.628; `fact_mantenimiento` 2.628 | **Cumple** |
| ERP de producción | `dim_orden` y `dim_producto` existen, pero no hay `source_system='erp'` ni eventos ERP; las órdenes se registran como `mes` | **Parcial** |
| Laboratorio/calidad | `fact_evento`: `calidad` 28.080; `fact_calidad` 28.080 | **Cumple** |
| Calendario de turnos | `dim_turno` (A/B/C, 480 min) y `dim_tiempo` (1.095 días) | **Cumple** |

**Sugerencia:** documentar que `dim_orden`/`dim_producto` representan la capa ERP
o etiquetar las órdenes con `source_system='erp'`; hoy la procedencia es ambigua.
No se implementa en esta verificación.

### 5.3 Datos para el prototipo

**Sí.** El prototipo supera el mínimo de 200.000 eventos y 90 días:

| Requisito | Mínimo | Observado |
|---|---:|---:|
| Eventos de máquina | 200.000 | 343.050 (IoT/SCADA) |
| Eventos totales | — | 401.838 |
| Días de historia | 90 | 180 |
| Órdenes de producción | — | 28.080 |
| Paradas | — | 76.045 |
| Mantenimientos | — | 2.628 |
| Controles de calidad | — | 28.080 |

### 5.4 Requisito de tiempo: latencia < 10 minutos

**Sí, para el flujo simulado.** La latencia de pipeline medida sobre los eventos
`sim-*` es de milisegundos, y la frescura de DirectQuery es inferior a un segundo.
El intervalo del simulador es de 60 s, de modo que el recorrido evento → base →
informe queda muy por debajo de 10 minutos.

| Métrica | Valor observado |
|---|---:|
| Eventos `sim-*` medidos | 51 |
| Latencia mínima (`ingested_at − generated_at`) | 0,7 ms |
| Latencia media | 28,2 ms |
| Latencia máxima | 54,9 ms |
| Frescura DirectQuery | 0,35 s (D-019) |
| Intervalo del simulador | 60 s |

Evidencia documental: `specs/004-ingesta-continua/verification.md` (AC-403) y
`specs/007-integracion-demo/verification.md` (tabla de latencia). La latencia de
pipeline se mide solo con eventos `sim-*`; los eventos históricos tienen
`generated_at` de la generación y `ingested_at` de la carga, por lo que su
diferencia no es latencia de ingesta.

**Cómo responderlo:** mostrar la tabla anterior y ejecutar la consulta del
**Anexo A.6**. Aclarar que el histórico no es tiempo real: la capa cercana al
tiempo real es la simulación, y el histórico es una capa validada por lotes.

---

## 6. Limitaciones que conviene declarar en el documento final

1. **Datos sintéticos:** el escenario `calibracion` está diseñado para mostrar
   señal (OEE ≈ 78 → 66 %); no es una medición de una fábrica real.
2. **Sin causalidad:** las relaciones scrap ↔ producto/turno son descriptivas; no
   se afirma causalidad.
3. **ERP parcial:** las órdenes existen como dimensión, pero no hay una fuente ERP
   etiquetada.
4. **Solapes:** se consolidan en `v_parada_consolidada` para Pareto, MTBF, fallas
   y microparadas; el OEE sigue usando `fact_produccion` y no refleja la unión.
   El dataset actual no contiene solapes por construcción.
5. **Drill-down:** la jerarquía existe en el modelo y la navegación se resuelve con
   slicers, matriz y drill-through; no hay un visual único de cuatro niveles.
6. **Cadencia IoT:** el feed sintético emite dos lecturas de proceso por turno, no
   una cada 15 min; la cadencia ideal se reporta como diagnóstico (D-022).
7. **Cifras mutables:** los totales pueden cambiar si se ejecuta nueva ingesta
   simulada; las cifras de este documento son las del 2026-10-24.

---

## Anexo A. Comandos de reproducción

> Ejecutar desde `C:\Users\lourd\code\Metalnova`. El usuario `metalinova` es el
> usuario de consulta de la base local; no se incluyen credenciales.

### A.1 Volumen y alcance

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select count(*) as fact_evento from fact_evento; select count(*) as maquinas from dim_maquina; select count(distinct id_planta) as plantas from v_kpi_oee_planta_dia; select min(fecha) as desde, max(fecha) as hasta, count(*) as dias from dim_tiempo t where exists (select 1 from fact_produccion p where p.id_tiempo=t.id_tiempo);"
```

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select source_system, tipo_evento, count(*) from fact_evento group by 1,2 order by 1,2;"
```

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select p.codigo as planta, count(distinct l.id_linea) as lineas, count(distinct m.id_maquina) as maquinas, count(distinct f.id_maquina) as maquinas_con_produccion from dim_planta p join dim_linea l on l.id_planta=p.id_planta join dim_maquina m on m.id_linea=l.id_linea left join fact_produccion f on f.id_maquina=m.id_maquina group by 1 order by 1;"
```

### A.2 Consistencia de la jerarquía

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "with l as (select fecha,id_planta,sum(tiempo_planificado_min) tp,sum(tiempo_operativo_min) tope,sum(total_count) tc,sum(good_count) gc,sum(minutos_ideales) mi,sum(downtime_no_planificado_min) dnp from v_kpi_oee_maquina_turno group by 1,2) select count(*) as filas, sum(case when p.tiempo_planificado_min<>l.tp or p.tiempo_operativo_min<>l.tope or p.total_count<>l.tc or p.good_count<>l.gc or p.minutos_ideales<>l.mi or p.downtime_no_planificado_min<>l.dnp then 1 else 0 end) as discrepancias from v_kpi_oee_planta_dia p join l on l.id_planta=p.id_planta and l.fecha=p.fecha;"
```

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "with m as (select fecha,id_planta,id_linea,sum(tiempo_planificado_min) tp,sum(tiempo_operativo_min) tope,sum(total_count) tc,sum(good_count) gc from v_kpi_oee_maquina_turno group by 1,2,3), l as (select fecha,id_planta,id_linea,tiempo_planificado_min tp,tiempo_operativo_min tope,total_count tc,good_count gc from v_kpi_oee_linea_dia) select count(*) as filas, sum(case when m.tp<>l.tp or m.tope<>l.tope or m.tc<>l.tc or m.gc<>l.gc then 1 else 0 end) as discrepancias from m join l using(fecha,id_planta,id_linea);"
```

### A.3 Solapes de paradas

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select count(*) as solapes from fact_parada a join fact_parada b on a.id_maquina=b.id_maquina and a.id_parada<b.id_parada and a.inicio_at < b.fin_at and b.inicio_at < a.fin_at where a.fin_at is not null and b.fin_at is not null;"
```

Invariantes de la vista consolidada:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/validation/05_parada_consolidada.sql
```

Prueba controlada (inserta, consulta y revierte; no deja datos):

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/validation/06_parada_consolidada_prueba.sql
```

El caso 10 min + 15 min con 5 min de solape devuelve **1 episodio de 20 min**,
`episodios_origen = 2` y `minutos_solapados = 5`. Dos intervalos adyacentes
siguen siendo **2 episodios**.

### A.4 Microparadas y fallas

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select p.id_parada, m.codigo, p.inicio_at, p.duracion_min, c.categoria, p.id_mantenimiento, p.es_microparada from fact_parada p join dim_maquina m using(id_maquina) join dim_causa c using(id_causa) where p.es_microparada order by p.id_parada limit 3;"
```

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select p.id_parada, m.codigo, p.inicio_at, p.duracion_min, c.categoria, p.id_mantenimiento, p.es_microparada from fact_parada p join dim_maquina m using(id_maquina) join dim_causa c using(id_causa) where not p.es_planificada and not p.es_microparada order by p.id_parada limit 3;"
```

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select count(*) as microparadas, sum(duracion_min) as min_micro from fact_parada where es_microparada; select count(*) as fallas, sum(duracion_min) as min_fallas from fact_parada where not es_planificada and not es_microparada;"
```

### A.5 Fuentes mínimas

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select source_system, tipo_evento, count(*) from fact_evento group by 1,2 order by 1,2;"
```

### A.6 Latencia

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select count(*) as eventos_sim, round(min(extract(epoch from ingested_at-generated_at))*1000,1) as min_ms, round(avg(extract(epoch from ingested_at-generated_at))*1000,1) as avg_ms, round(max(extract(epoch from ingested_at-generated_at))*1000,1) as max_ms from fact_evento where run_id like 'sim-%';"
```

### A.7 OEE de la planta de peor desempeño (últimos 30 días)

```powershell
docker exec metalnova_db psql -U metalinova -d metalinova -c "select planta_codigo, round(100*sum(tiempo_operativo_min)/sum(tiempo_planificado_min),2) as disponibilidad_pct, round(100*sum(minutos_ideales)/sum(tiempo_operativo_min),2) as rendimiento_pct, round(100*sum(good_count)::numeric/sum(total_count),2) as calidad_pct, round(100*sum(tiempo_operativo_min)/sum(tiempo_planificado_min)*sum(minutos_ideales)/sum(tiempo_operativo_min)*sum(good_count)::numeric/sum(total_count),2) as oee_pct from v_kpi_oee_planta_dia where fecha >= (select max(fecha) from v_kpi_oee_planta_dia) - 29 group by 1 order by 5;"
```

---

## Anexo B. Trazabilidad documental

| Tema | Documento / archivo |
|---|---|
| Definición de evento y volumen | `specs/CONSTITUTION.md` §2 y §11 |
| Modelo dimensional y jerarquías | `specs/CONSTITUTION.md` §5; `docs/DATA_DICTIONARY.md` |
| Reglas IoT y fuente de verdad | `specs/CONSTITUTION.md` §7; `docs/ARCHITECTURE.md` |
| Regla G6 (microparada/falla) | `specs/CONSTITUTION.md` §7.3; `docs/DATA_DICTIONARY.md` §Reglas |
| Volumen observado | `docs/DATA_DICTIONARY.md` §Volumen; `specs/003-generador-historico/verification.md` |
| Ingesta y latencia | `specs/004-ingesta-continua/verification.md`; `specs/007-integracion-demo/verification.md` |
| Modelo Power BI y medidas | `powerbi/final/measures.dax`; `powerbi/final/MetalNova.SemanticModel/definition/relationships.tmdl` |
| Matriz de cumplimiento | `docs/CUMPLIMIENTO.md` |
| Plan de mejora y costos | `docs/PLAN_MEJORA.md` |
