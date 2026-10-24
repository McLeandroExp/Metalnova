# Respuesta a la pregunta principal de Business Understanding

> **Todos los datos son sintéticos.** Esta respuesta se apoya en el escenario
> `calibracion` (semilla 42, 180 días, `2026-04-22` → `2026-10-18`) y en las vistas
> KPI del prototipo. No es una medición de una fábrica real ni un ahorro realizado.

- **Pregunta:** ¿Qué activos, turnos, productos y causas de parada explican la caída
  del OEE y cuál es su impacto en throughput, scrap y costo?
- **Fecha de análisis:** 2026-10-24.
- **Documento de verificación asociado:** [`bloque1-negocio-modelo.md`](./bloque1-negocio-modelo.md).

---

## 1. Respuesta ejecutiva

La caída del OEE en el escenario calibrado (**78,02 % → 66,00 %** en ventanas de
30 días) se explica **principalmente por pérdida de rendimiento**, no por paradas.
La disponibilidad se mantiene alta (98,55 % al cierre) y la calidad cae menos que el
rendimiento. En términos de minutos equivalentes, la pérdida de rendimiento
(2.911.218 min) es **19 veces** la pérdida de disponibilidad (151.831 min).

Los focos concretos son:

| Dimensión | Hallazgo |
|---|---|
| **Activos** | **P-SUR** es la planta con peor OEE (62,04 % en los últimos 30 días; 67,73 % en 180 días). **L3-2** es la peor línea (60,98 %) y **M-047** la peor máquina (47,47 % en 30 días; 51,81 % en 180 días). |
| **Turnos** | El **turno C** es el peor en P-SUR (59,24 %) y en M-047 (45,33 %). |
| **Productos** | **PRD-009 (Eje cardán, familia FAM-TRA)** es el peor producto en los últimos 30 días (OEE 61,06 %, scrap 7,01 %). En 180 días el peor es **PRD-012 (Horquilla, FAM-TRA)** (OEE 67,07 %, scrap 5,82 %). |
| **Causas de parada** | La microparada es la causa no planificada más frecuente y acumulada: **43.692 eventos y 109.020 min**. La falla mecánica **F-MEC** es la principal falla “formal”: **867 eventos y 15.356 min**. |
| **Impacto en throughput** | **4.269.957 unidades potenciales no producidas** y **3.528.469 min equivalentes perdidos** en 180 días. El 82,5 % de esa pérdida es rendimiento. |
| **Impacto en scrap** | **684.643 unidades scrap** (4,84 % global); P-SUR concentra **203.466** (5,72 %). |
| **Impacto en costo** | Valorizando toda la pérdida con los supuestos declarados: **USD 10,67 M** por rendimiento, **USD 0,56 M** por disponibilidad y **USD 12,32 M** por scrap en 180 días. Es una magnitud hipotética, no un ahorro realizado. |

**Matiz importante:** aunque la pregunta pide causas de parada, el Loss Tree muestra
que las paradas no son el driver principal de la caída. La pérdida de velocidad
(rendimiento) domina; las microparadas y fallas explican una parte menor del OEE.
La respuesta honesta es: **“la caída es principalmente rendimiento; las paradas
relevantes son microparadas y F-MEC, pero no alcanzan a explicar la mayor parte de
la pérdida”**.

---

## 2. Evidencia de la caída

### 2.1 OEE y sus componentes en ventanas de 30 días

| Componente | Inicio | Cierre | Cambio |
|---|---:|---:|---:|
| Disponibilidad (A) | 99,02 % | 98,55 % | −0,47 pp |
| Rendimiento (P) | 81,78 % | 71,31 % | **−10,47 pp** |
| Calidad (Q) | 96,34 % | 93,92 % | −2,42 pp |
| **OEE** | **78,02 %** | **66,00 %** | **−12,02 pp** |

Fuente: `specs/006-powerbi/verification.md`, medición SQL de ventanas de 30 días.
El OEE de los 180 días completos es **71,96 %** (A 98,79 % · P 76,55 % · Q 95,16 %).

**Lectura:** el rendimiento cae 10,47 pp y explica la mayor parte del deterioro. La
calidad cae 2,42 pp y la disponibilidad apenas 0,47 pp.

### 2.2 Pérdidas en minutos equivalentes (180 días)

| Pérdida | Minutos | Participación |
|---|---:|---:|
| Disponibilidad | 151.831 | 4,3 % |
| Rendimiento | 2.911.218 | **82,5 %** |
| Calidad | 465.420 | 13,2 % |
| **Total** | **3.528.469** | **100 %** |

Fuente: `v_loss_tree`, suma de `minutos_perdidos_*`.

### 2.3 Activos, turnos y productos

**Planta (últimos 30 días):**

| Planta | OEE |
|---|---:|
| P-SUR | **62,04 %** |
| P-CENTRO | 66,07 % |
| P-NORTE | 69,32 % |

**P-SUR (últimos 30 días):**

| Nivel | Valor | OEE |
|---|---|---:|
| Línea | L3-2 | **60,98 %** |
| Línea | L3-1 | 63,11 % |
| Máquina | M-047 (L3-2) | **47,47 %** |
| Turno de M-047 | A | 49,44 % |
| Turno de M-047 | B | 47,62 % |
| Turno de M-047 | C | **45,33 %** |

En 180 días, M-047 tiene OEE **51,81 %** y es la única máquina por debajo de 55 %.
Le siguen M-049 (60,37 %), M-040 (60,51 %) y M-024 (62,78 %).

**Producto (últimos 30 días):**

| Producto | Familia | OEE | Scrap |
|---|---|---:|---:|
| PRD-009 · Eje cardán | FAM-TRA | **61,06 %** | **7,01 %** |
| PRD-011 · Sincronizador | FAM-TRA | 61,37 % | 7,06 % |
| PRD-010 · Engranaje de transmisión | FAM-TRA | 62,36 % | 6,95 % |
| PRD-012 · Horquilla de cambio | FAM-TRA | 63,03 % | 6,93 % |
| PRD-008 · Buje de barra estabilizadora | FAM-SUS | 65,90 % | 5,97 % |

**Cautela:** en el escenario calibrado, cada planta produce una sola familia
(P-NORTE → FAM-FRE, P-CENTRO → FAM-SUS, P-SUR → FAM-TRA). Por eso **el efecto
producto/familia está confundido con el efecto planta**; no se puede atribuir la
caída a un producto separándolo de P-SUR. Los productos de FAM-TRA son los peores
porque son los de P-SUR, no porque el producto sea independientemente el causante.

### 2.4 Causas de parada

**Paradas no planificadas (180 días):**

| Causa | Categoría | Eventos | Minutos |
|---|---|---:|---:|
| MICRO | Microparada | **43.692** | **109.020** |
| F-MEC | Falla mecánica | 867 | 15.356 |
| F-ELE | Falla eléctrica | 582 | 10.546 |
| F-NEU | Falla neumática | 388 | 6.803 |
| F-HID | Falla hidráulica | 339 | 6.242 |
| AJUSTE | Ajuste | 241 | 4.260 |

**Paradas planificadas (excluidas de disponibilidad):**

| Causa | Eventos | Minutos |
|---|---:|---:|
| DESCANSO | 28.080 | 842.400 |
| CAM-PROD | 1.629 | 49.150 |
| MANT-PREV | 227 | 20.171 |

La microparada es la causa no planificada dominante por frecuencia y por tiempo
acumulado. Sin embargo, su aporte directo al OEE es de disponibilidad, y la
disponibilidad solo perdió 151.831 min en total; la mayor pérdida sigue siendo
rendimiento.

---

## 3. Impacto en throughput, scrap y costo

### 3.1 Throughput

| Indicador | Valor |
|---|---:|
| Unidades potenciales (según ciclo ideal) | 18.412.350 |
| Unidades no producidas | **4.269.957** |
| Minutos equivalentes perdidos | **3.528.469** |
| Pérdida de rendimiento | 2.911.218 min (82,5 %) |
| Pérdida de disponibilidad | 151.831 min (4,3 %) |
| Pérdida de calidad | 465.420 min (13,2 %) |

**Por planta:**

| Planta | Unidades no producidas | Scrap |
|---|---:|---:|
| P-CENTRO | 1.513.484 | 245.429 |
| P-NORTE | 1.427.466 | 235.748 |
| P-SUR | 1.329.007 | **203.466** |

### 3.2 Scrap

| Ámbito | Unidades producidas | Scrap | Scrap % |
|---|---:|---:|---:|
| Global | 14.142.393 | **684.643** | **4,84 %** |
| P-SUR | 3.557.875 | **203.466** | **5,72 %** |

P-SUR tiene el mayor scrap relativo y absoluto, coherente con su peor OEE y su
mayor consumo energético por unidad buena.

### 3.3 Costo (hipotético, con supuestos declarados)

Supuestos de `docs/PLAN_MEJORA.md`: **USD 220/hora-máquina** de throughput perdido
y **USD 18/unidad** rechazada. No son datos de una empresa real.

| Concepto | Valorización de toda la pérdida (180 días) |
|---|---:|
| Pérdida de rendimiento | **USD 10.674.466** |
| Pérdida de disponibilidad | **USD 556.714** |
| Scrap | **USD 12.323.574** |

**Cómo leerlo:** son magnitudes de la pérdida observada si se valorizara completa,
no ahorros realizados. El plan de mejora usa metas parciales y más conservadoras:

- reducir 10 % relativo el scrap de P-SUR ⇒ **USD 366.240/180 d**;
- recuperar 5 % de la pérdida de rendimiento de P-SUR ⇒ **USD 190.195/180 d**;
- subir el MTBF de P-SUR al global ⇒ **USD 41.382/180 d**;
- intervenir M-047 ⇒ **USD 31.999/180 d**;
- reducir 5 % el consumo energético de P-SUR ⇒ **USD 8.856/180 d**.

No se suman: las acciones se solapan. El detalle y los supuestos están en
`docs/PLAN_MEJORA.md`.

---

## 4. Respuesta corta para la exposición

> “La caída de OEE de 78 % a 66 % no es principalmente un problema de paradas: la
> disponibilidad se mantiene en 98,5 % y la mayor pérdida es rendimiento (2,91 M
> de minutos equivalentes, 82,5 % del total). Los focos son P-SUR, la línea L3-2,
> la máquina M-047 y el turno C; el producto PRD-009 es el peor del último mes,
> aunque en este escenario cada planta produce una sola familia y el efecto
> producto está confundido con la planta. Las paradas no planificadas más
> relevantes son las microparadas (43.692 eventos, 109.020 min) y la falla mecánica
> F-MEC (867 eventos, 15.356 min). El impacto es 4,27 M de unidades potenciales no
> producidas, 684.643 unidades scrap y, valorizando toda la pérdida con supuestos
> declarados, USD 10,67 M por rendimiento, USD 0,56 M por disponibilidad y
> USD 12,32 M por scrap en 180 días.”

---

## 5. Supuestos y limitaciones

1. **Datos sintéticos y escenario calibrado:** la caída 78 → 66 % se diseñó para
   que el informe tenga señal; no es una medición real.
2. **Costo hipotético:** USD 220/h y USD 18/unidad son supuestos del prototipo,
   no costos de la fábrica. Cambiarlos cambia la valorización.
3. **Producto confundido con planta:** cada planta produce una sola familia; no se
   puede separar el efecto producto del efecto planta.
4. **Loss Tree en minutos equivalentes:** no sustituye un estudio de tiempos.
5. **Sin causalidad:** la relación scrap ↔ producto/turno/condición es descriptiva.
6. **Cifras mutables:** si se ejecuta nueva ingesta simulada, los totales cambian.

---

## 6. Trazabilidad

| Tema | Archivo |
|---|---|
| Caída de OEE y outliers | `specs/006-powerbi/verification.md` |
| Pérdidas y costo | `docs/PLAN_MEJORA.md`; `v_loss_tree` |
| OEE por planta/línea/máquina/turno | `v_kpi_oee_*`, `v_loss_tree` |
| Scrap y calidad | `v_kpi_calidad_*`, `v_kpi_oee_*` |
| Paradas y causas | `v_kpi_parada`, `fact_parada`, `dim_causa` |
| Definiciones de KPI | `docs/DATA_DICTIONARY.md`; `specs/CONSTITUTION.md` §6 |
