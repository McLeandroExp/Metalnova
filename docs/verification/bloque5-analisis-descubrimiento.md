# Verificación del Bloque 5 — Análisis y descubrimiento

> **Todos los datos son sintéticos.** La verificación se ejecutó el **2026-10-24**
> sobre el histórico calibrado de 180 días (`2026-04-22` → `2026-10-18`) de la
> base local `metalinova`.

- **Alcance:** Loss Tree, confiabilidad, calidad descriptiva y priorización.
- **Método:** consultas a `v_loss_tree`, `v_kpi_mantenimiento_*`,
  `v_kpi_confiabilidad_apoyo_maquina_dia`, `v_kpi_calidad_*` y revisión de
  `docs/PLAN_MEJORA.md`.
- **Documentos relacionados:** `bloque2-modelado-dimensional.md`,
  `bloque3-aplicativo-bi.md`, `bloque4-kpi-obligatorios.md`.

## Resumen de veredictos

| # | Punto | Veredicto |
|---|---|---|
| 1 | Loss Tree: componente dominante y descomposición por activo/turno/producto | **Cumple** |
| 2 | Confiabilidad: alto downtime y fallas cortas frecuentes fuera del promedio | **Cumple** |
| 3 | Calidad: scrap vs producto, turno y condiciones, sin afirmar causalidad | **Cumple con matiz** (cambios de producto y temperatura con consultas ad-hoc, no visuales dedicados) |
| 4 | Priorización: ranking por impacto económico y criticidad | **Cumple** (ranking cuantitativo + criticidad; no es un score formal) |

---

## 1. Loss Tree

### 1.1 Componente dominante

| Componente | Minutos equivalentes | Participación |
|---|---:|---:|
| Disponibilidad | 151.831 | 4,30 % |
| **Rendimiento** | **2.911.218** | **82,51 %** |
| Calidad | 465.420 | 13,19 % |
| **Total** | **3.528.469** | **100 %** |

**Lectura:** la mayor pérdida del OEE es **rendimiento**, no disponibilidad. La
pérdida de rendimiento es 19,2 veces la de disponibilidad. Esto es coherente con
la caída del OEE descrita en la pregunta principal.

### 1.2 Descomposición por activo

| Máquina | Planta | Pérdida total (min) | Rendimiento | Calidad | Disponibilidad |
|---|---|---|---:|---:|---:|
| **M-047** | P-SUR | **116.356** | 101.039 | 8.844 | 6.473 |
| M-049 | P-SUR | 95.739 | 82.733 | 9.486 | 3.520 |
| M-040 | P-SUR | 95.497 | 82.854 | 9.514 | 3.129 |
| M-024 | P-CENTRO | 89.922 | 78.084 | 8.207 | 3.630 |
| M-015 | P-NORTE | 82.627 | 71.793 | 7.742 | 3.092 |
| M-032 | P-CENTRO | 80.157 | 59.455 | 17.639 | 3.063 |
| M-051 | P-SUR | 72.619 | 59.352 | 10.065 | 3.202 |
| M-052 | P-SUR | 72.615 | 59.421 | 10.073 | 3.121 |

En M-047, el 86,8 % de su pérdida es rendimiento. Es el activo con mayor pérdida
total y el peor OEE del histórico (51,81 %).

### 1.3 Descomposición por turno

| Turno | Pérdida total (min) | Rendimiento | Calidad | Disponibilidad |
|---|---:|---:|---:|---:|
| **C** | **1.313.877** | 1.092.438 | 159.484 | 61.955 |
| B | 1.164.829 | 959.735 | 155.041 | 50.054 |
| A | 1.049.763 | 859.046 | 150.896 | 39.822 |

El turno C concentra la mayor pérdida (37,2 % del total) y el mayor componente de
rendimiento. Es consistente con que sea el peor turno en P-SUR y M-047.

### 1.4 Descomposición por producto

| Producto | Familia | Pérdida total (min) | Rendimiento | Calidad | Disponibilidad |
|---|---|---|---:|---:|---:|
| **PRD-012** | FAM-TRA | **331.591** | 275.893 | 41.773 | 13.924 |
| PRD-009 | FAM-TRA | 330.278 | 274.597 | 42.186 | 13.495 |
| PRD-007 | FAM-SUS | 319.966 | 263.646 | 42.703 | 13.617 |
| PRD-006 | FAM-SUS | 305.832 | 251.569 | 41.146 | 13.116 |
| PRD-011 | FAM-TRA | 299.741 | 248.648 | 38.968 | 12.125 |
| PRD-005 | FAM-SUS | 297.627 | 245.276 | 39.767 | 12.584 |
| PRD-008 | FAM-SUS | 295.437 | 243.496 | 39.326 | 12.615 |
| PRD-010 | FAM-TRA | 286.056 | 238.319 | 35.891 | 11.846 |

**Cautela:** en el escenario calibrado cada planta produce una sola familia
(P-SUR → FAM-TRA, P-CENTRO → FAM-SUS, P-NORTE → FAM-FRE). El efecto producto
está confundido con el efecto planta. No se puede atribuir la pérdida a un
producto separándolo de su planta.

### 1.5 Dónde se ve en el informe

- Página 02: `matrix_maquina_turno` (activo × turno), `matrix_perdida_planta`
  (Loss Tree por planta), `chart_perdida_producto` (pérdida por producto).
- El detalle de máquina y el detalle de causa permiten bajar a la máquina y a la
  causa.

---

## 2. Confiabilidad

### 2.1 Método

Se usan dos capas:

- `v_kpi_mantenimiento_maquina_turno`: downtime, fallas, fallas cortas, MTBF.
- `v_kpi_confiabilidad_apoyo_maquina_dia`: microparadas y fallas cortas por 100 h,
  normalizadas por horas operativas.

Las tasas se agregan ponderando por runtime, no promediando tasas diarias.

### 2.2 Perfiles de máquina

| Máquina | Planta | Downtime (min) | Fallas | Fallas cortas | Fallas cortas/100 h | Microparadas/100 h | MTBF (h) | Rank downtime | Rank fallas cortas | Rank microparadas |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **M-047** | P-SUR | **6.473** | 141 | 103 | **2,63** | **30,08** | 27,78 | 1 | 1 | 1 |
| M-051 | P-SUR | 3.202 | 73 | 67 | 1,69 | 20,74 | 54,44 | 8 | 2 | 26 |
| M-041 | P-SUR | 3.434 | 78 | 67 | 1,69 | 20,03 | 50,95 | 5 | 2 | 43 |
| M-024 | P-CENTRO | 3.634 | 58 | 48 | 1,21 | 25,48 | 68,40 | 2 | 16 | 2 |
| **M-015** | P-NORTE | 3.095 | 30 | 25 | 0,63 | **24,33** | **132,60** | 13 | 45 | 3 |
| **M-025** | P-CENTRO | 2.609 | 25 | 22 | 0,55 | **22,17** | **159,51** | 40 | 49 | 6 |

**Lectura:**

- **M-047** es el caso más grave: alto downtime, muchas fallas cortas y muchas
  microparadas. Aparece en todos los promedios.
- **M-051 y M-041** tienen una tasa alta de fallas cortas (rank 2) pero no están
  en el top 3 de downtime (rank 8 y 5). El promedio de downtime no las destaca.
- **M-015 y M-025** tienen MTBF alto (132,6 h y 159,5 h), lo que las hace parecer
  confiables en el promedio, pero su tasa de microparadas es alta (rank 3 y 6) y
  su downtime no está en el top 10 (ranks 13 y 40). Son el ejemplo de “fallas
  breves frecuentes que no aparecen en el promedio”.
- **M-024** combina alto downtime (rank 2) y altas microparadas (rank 2), pero su
  tasa de fallas cortas es media (rank 16): el perfil de pérdida es distinto.

### 2.3 Por qué el promedio oculta

Un MTBF alto puede convivir con muchas microparadas porque el MTBF solo cuenta
fallas “formales” (no planificadas y no microparadas). Las microparadas y fallas
cortas se miden por 100 h operativas. Por eso el informe incluye
`Microparadas por 100 h`, `Fallas cortas por 100 h` y `MTBF corto`.

**Evidencia en el informe:** página 03, tabla `table_confiabilidad` y dispersión
`scatter_fallas_cortas`; vista `v_kpi_confiabilidad_apoyo_maquina_dia`.

---

## 3. Calidad: scrap y condiciones

### 3.1 Scrap por turno

| Turno | Scrap % | Scrap (unidades) | Unidades producidas |
|---|---:|---:|---:|
| **C** | **5,20 %** | 234.717 | 4.512.316 |
| B | 4,82 % | 228.032 | 4.731.532 |
| A | 4,53 % | 221.894 | 4.898.545 |

El turno C tiene el mayor scrap relativo. Es una asociación descriptiva; no se
afirma que el turno sea la causa.

### 3.2 Scrap por producto

| Producto | Familia | Scrap % | Scrap (unidades) |
|---|---|---:|---:|
| PRD-012 | FAM-TRA | **5,82 %** | 45.571 |
| PRD-010 | FAM-TRA | 5,78 % | 47.854 |
| PRD-009 | FAM-TRA | 5,75 % | 63.279 |
| PRD-011 | FAM-TRA | 5,52 % | 46.762 |
| PRD-005 | FAM-SUS | 5,05 % | 47.720 |
| PRD-008 | FAM-SUS | 5,00 % | 67.416 |
| PRD-007 | FAM-SUS | 4,91 % | 85.406 |
| PRD-006 | FAM-SUS | 4,83 % | 44.887 |

Los productos de FAM-TRA tienen mayor scrap, pero FAM-TRA es también la familia
de P-SUR. **Producto y planta están confundidos**; no se puede separar el efecto.

### 3.3 Cambios de producto

Se compararon los turnos-máquina con una parada `CAM-PROD` frente a los que no la
tienen:

| Grupo | Turnos-máquina | Unidades | Scrap | Scrap % |
|---|---:|---:|---:|---:|
| Con cambio de producto | 1.629 | 762.928 | 37.168 | **4,87 %** |
| Sin cambio de producto | 26.451 | 13.379.465 | 647.475 | **4,84 %** |

La diferencia es de **0,03 pp** en el escenario sintético; no hay una asociación
material entre cambio de producto y scrap. Es un resultado descriptivo, no una
prueba causal.

### 3.4 Condiciones de operación

| Asociación descriptiva | Coeficiente / comparación |
|---|---|
| Scrap vs energía por unidad buena | `corr = 0,4035` |
| Scrap vs temperatura promedio del día | `corr = 0,5138` |
| Scrap vs temperatura máxima del día | `corr = 0,4282` |
| Scrap en días con temperatura máxima > 85 °C | **5,43 %** (1.072 días-máquina) |
| Scrap en días con temperatura máxima ≤ 85 °C | **4,77 %** (8.288 días-máquina) |

**Lectura:** hay una asociación positiva moderada entre scrap y energía/temperatura
en los datos sintéticos. No se afirma causalidad: puede haber confusión con
planta, producto, turno o perfil de máquina. La página 04 muestra la dispersión
**energía-scrap**; la temperatura se verificó con consultas ad-hoc y no tiene un
visual dedicado.

### 3.5 Qué muestra el informe

- Página 04: scrap por planta, producto y turno; FPY, defectos, retrabajo y
  energía; dispersión energía-scrap.
- `PLAN_MEJORA.md` declara explícitamente que la relación es descriptiva y que no
  se afirma causalidad.
- Cambios de producto y temperatura no tienen visual dedicado; se documentan aquí
  como análisis ad-hoc.

---

## 4. Priorización

**Base observada:** P-SUR tiene OEE 67,73 %, scrap 5,72 %, MTBF 66,86 h y
0,4400 kWh/unidad buena; M-047 tiene OEE 51,81 % y el mayor Loss Tree del
histórico.

`docs/PLAN_MEJORA.md` propone cinco intervenciones con impacto económico
hipotético y criticidad operacional:

| Orden | Acción | Impacto hipotético / 180 d | Confianza | Criticidad |
|---|---|---:|---|---|
| 1 | A1 · Reducir scrap en P-SUR | USD 366.240 | Media | Alta |
| 2 | A2 · Recuperar rendimiento en P-SUR | USD 190.195 | Baja-media | Alta |
| 3 | A4 · Elevar MTBF de P-SUR | USD 41.382 | Media | Alta |
| 4 | A3 · Intervención en M-047 | USD 31.999 | Media | **Muy alta** (activo crítico) |
| 5 | A5 · Eficiencia energética en P-SUR | USD 8.856 | Media-baja | Media |

**Decisión propuesta:** ejecutar A1 y A2 como palancas principales, A3 por
criticidad del activo, A4 como sostén de confiabilidad y A5 como mejora continua.

**Por qué usa impacto y criticidad:** el orden principal es económico, pero A3
sube en prioridad por la criticidad de M-047 aunque su impacto monetario sea menor
que A1/A2. No se suman los ahorros: las acciones se solapan (menos fallas también
reduce downtime y energía).

**Supuestos:** USD 220/hora-máquina, USD 18/unidad rechazada y USD 0,12/kWh. Son
supuestos sintéticos declarados; no son costos reales. El plan distingue impacto
observado, impacto hipotético y cifras del caso.

---

## 5. Verificaciones ejecutadas

| Verificación | Resultado |
|---|---|
| `validate_data.py` | 49/49 comprobaciones OK |
| `sql/validation/07_kpi_formulas.sql` | 12/12 comprobaciones OK |
| Loss Tree global y por activo/turno/producto | Consultas ejecutadas; valores consistentes |
| Confiabilidad de corto plazo | Tasas por 100 h calculadas con runtime ponderado |
| Scrap por turno/producto/cambio/condición | Consultas descriptivas ejecutadas |
| Ranking de priorización | Revisado contra `PLAN_MEJORA.md` |

---

## 6. Cómo responder en la demo

1. **Loss Tree:** abrir la página 02 y mostrar que rendimiento es el 82,5 % de la
   pérdida; bajar a P-SUR, M-047, turno C y producto PRD-012.
2. **Confiabilidad:** abrir la página 03; mostrar M-047 como caso grave y M-015 /
   M-025 como casos de microparadas frecuentes con MTBF alto.
3. **Calidad:** abrir la página 04; mostrar scrap por turno C, productos FAM-TRA y
   dispersión energía-scrap. Aclarar que es descriptivo, no causal.
4. **Priorización:** abrir `PLAN_MEJORA.md`; explicar A1/A2 por impacto, A3 por
   criticidad de M-047 y A4/A5 como apoyo.

---

## 7. Limitaciones

1. **Datos sintéticos:** las asociaciones son del escenario calibrado, no de una
   fábrica real.
2. **Producto/planta confundidos:** cada planta produce una sola familia.
3. **Sin causalidad:** scrap vs turno, producto, energía o temperatura son
   asociaciones descriptivas.
4. **Cambios de producto y temperatura sin visual dedicado:** se analizaron con
   consultas ad-hoc; el informe expone producto, turno y energía.
5. **Ranking con supuestos de costo:** cambiar USD 220/h o USD 18/unidad cambia el
   orden económico; la criticidad operacional se mantiene.
6. **Cifras mutables:** nueva ingesta simulada cambia los totales.

---

## 8. Trazabilidad

| Tema | Archivo / vista |
|---|---|
| Loss Tree | `v_loss_tree`, `v_loss_tree_maquina_mes`; `sql/views/07_loss_tree.sql` |
| Confiabilidad | `v_kpi_confiabilidad_apoyo_maquina_dia`; `sql/views/06_kpi_confiabilidad.sql` |
| Calidad/energía | `v_kpi_calidad_maquina_dia`, `v_kpi_calidad_producto_dia`; `sql/views/05_kpi_calidad_energia.sql` |
| Priorización | `docs/PLAN_MEJORA.md` |
| Página 02 | `powerbi/final/MetalNova.Report/definition/pages/page_oee_02/` |
| Página 03 | `powerbi/final/MetalNova.Report/definition/pages/page_maintenance_03/` |
| Página 04 | `powerbi/final/MetalNova.Report/definition/pages/page_quality_04/` |
