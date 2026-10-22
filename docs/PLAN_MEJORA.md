# Plan de mejora — MetalNova Smart Factory BI

> **Todos los datos son sintéticos.** Este plan distingue tres niveles:
> **observado** (calculado en las vistas), **hipotético** (ahorro estimado con
> supuestos de coste) y **cifras del caso** (enunciado académico, no recalculadas).
> No se presenta ningún ahorro como realizado.

## 1. Metodología

1. Se parte de las vistas KPI (`v_loss_tree`, `v_kpi_mantenimiento_*`,
   `v_kpi_calidad_*`, `v_alerta_maquina_critica`).
2. Se rankean las pérdidas observadas en minutos equivalentes y su traducción a
   unidades, kWh y fallas.
3. Cada acción declara: problema, evidencia, acción, responsable, KPI de
   seguimiento, impacto observado, impacto hipotético, método de cálculo,
   supuesto, confianza y limitación.
4. Los costes son supuestos explícitos del prototipo, no datos de la fábrica.

## 2. Supuestos de coste (sintéticos y declarados)

| Supuesto | Valor | Uso |
|---|---:|---|
| Hora-máquina de throughput perdido | USD 220/h | valorar minutos de pérdida |
| Unidad rechazada | USD 18/unidad | valorar scrap evitable |
| Energía eléctrica | USD 0,12/kWh | valorar ahorro energético |
| Coste de intervención | dato CMMS sintético | ya registrado en `fact_mantenimiento` |

Estos valores **no** provienen del caso ni de una empresa real. Cambiarlos cambia
el ranking económico; la prioridad operacional se mantiene.

## 3. Pérdida observada (180 días)

| Ámbito | OEE | Pérdida rendimiento | Pérdida calidad | Pérdida disponibilidad | Scrap | kWh/unidad buena | MTBF |
|---|---:|---:|---:|---:|---:|---:|---:|
| Global | 71,96 % | 2.911.218 min | 465.420 min | 151.831 min | 4,84 % | 0,3403 | 85,7 h |
| P-NORTE | 75,58 % | 869.773 min | 143.660 min | 48.509 min | 4,19 % | 0,2923 | 111,7 h |
| P-CENTRO | 71,98 % | 1.003.987 min | 162.942 min | 51.932 min | 4,95 % | 0,3242 | 87,3 h |
| **P-SUR** | **67,73 %** | **1.037.458 min** | **158.818 min** | **51.390 min** | **5,72 %** | **0,4400** | **66,9 h** |

Lectura: en las tres plantas la **pérdida de rendimiento es dominante** (20 veces
la de disponibilidad en P-SUR). El problema no es solo “parar”, sino perder
velocidad y unidades. P-SUR concentra el peor OEE, el mayor scrap, la mayor
energía por unidad buena y el menor MTBF.

## 4. Acciones priorizadas

### A1 · Reducir el scrap en P-SUR (prioridad 1)

| Campo | Contenido |
|---|---|
| Problema | P-SUR tiene scrap 5,72 % (6,98 % en los últimos 30 días) frente a 4,19 % de P-NORTE. |
| Evidencia | `v_kpi_calidad_maquina_dia` y `v_kpi_oee_planta_dia`; 203.466 unidades scrap en 180 días. |
| Acción | Analizar los productos y turnos con mayor scrap, revisar parámetros de proceso y retrabajo. |
| Responsable | Calidad + Producción. |
| KPI de seguimiento | Scrap Rate, FPY, Tasa de Retrabajo. |
| Impacto observado | 203.466 unidades scrap sobre 3.557.875 unidades producidas en P-SUR. |
| Impacto hipotético | Reducir 10 % relativo el scrap evita ~20.347 unidades × USD 18 = **USD 366.240/180 d** (~USD 61.040/mes). |
| Método | `scrap_actual × 10 % × coste_unitario`. |
| Supuesto | El coste unitario y la reducción del 10 % son supuestos; no se ha probado la causa. |
| Confianza | Media. |
| Limitación | No se afirma causalidad entre producto/turno y scrap; el caso pide relacionar, no demostrar causalidad. |

### A2 · Recuperar pérdida de rendimiento en P-SUR (prioridad 2)

| Campo | Contenido |
|---|---|
| Problema | Pérdida de rendimiento de 1.037.458 min en P-SUR, la mayor del Loss Tree. |
| Evidencia | `v_loss_tree` (participación de rendimiento) y matriz máquina-turno. |
| Acción | Revisar ciclos ideales, cambios de producto, microparadas y pérdidas de velocidad; priorizar las máquinas del cuadro de mando. |
| Responsable | Producción + Ingeniería de proceso. |
| KPI de seguimiento | Rendimiento, OEE, microparadas/100 h, fallas cortas/100 h. |
| Impacto observado | 1.037.458 min equivalentes perdidos (≈ 27 % del tiempo planificado de P-SUR). |
| Impacto hipotético | Recuperar 5 % de esa pérdida = 51.873 min ≈ 864 h × USD 220 = **USD 190.195/180 d** (~USD 31.699/mes). |
| Método | `pérdida_rendimiento × 5 % × coste_hora`. |
| Supuesto | El 5 % es una meta de mejora, no un resultado; el coste/hora es sintético. |
| Confianza | Baja-media. |
| Limitación | El Loss Tree mide minutos equivalentes; no identifica por sí solo la causa raíz de la pérdida de velocidad. |

### A3 · Intervención prioritaria en M-047 (prioridad 3)

| Campo | Contenido |
|---|---|
| Problema | M-047 (P-SUR, perfil `critica`) tiene OEE 51,81 %, 6.473 min de downtime, 11.326 unidades scrap y 0,6937 kWh/unidad buena. |
| Evidencia | `v_kpi_oee_maquina_dia`, `v_kpi_mantenimiento_maquina_turno`, `v_alerta_maquina_critica` (alerta crítica). |
| Acción | Inspección mecánica/energética y revisión de parámetros; plan de recuperación con seguimiento semanal. |
| Responsable | Mantenimiento + Producción. |
| KPI de seguimiento | OEE de M-047, MTBF, kWh/unidad buena, scrap. |
| Impacto observado | Es la única máquina por debajo de 55 % y la de mayor consumo específico. |
| Impacto hipotético | Bajar 20 % el downtime (1.295 min ≈ 21,6 h × USD 220 = USD 4.747) y llevar el scrap a la media de P-SUR (evita ~1.514 unidades × USD 18 = USD 27.252): **~USD 32.000/180 d** (~USD 5.333/mes), además del valor de criticidad. |
| Método | `downtime × 20 % × coste_hora` + `scrap evitable × coste_unitario`. |
| Supuesto | Los porcentajes de mejora son metas; la criticidad A justifica la acción aunque el impacto monetario sea menor que A1/A2. |
| Confianza | Media. |
| Limitación | El coste de la intervención no se descuenta; el CMMS sintético registra ~USD 17 min de MTTR y coste estimado, pero no el coste de parada inducida. |

### A4 · Elevar el MTBF de P-SUR (prioridad 4)

| Campo | Contenido |
|---|---|
| Problema | MTBF 66,9 h frente a 85,7 h global y 111,7 h de P-NORTE; 951 fallas en 180 días. |
| Evidencia | `v_kpi_mantenimiento_planta_dia`; 824 fallas cortas y 13.650 microparadas. |
| Acción | Mantenimiento preventivo basado en condición; revisar las máquinas con más fallas cortas/100 h. |
| Responsable | Mantenimiento. |
| KPI de seguimiento | MTBF, fallas/100 h, fallas cortas/100 h, MTTR. |
| Impacto observado | 951 fallas; 66,9 h de MTBF; 824 fallas cortas. |
| Impacto hipotético | Llevar el MTBF a 85,7 h reduce ~209 fallas × 54 min ≈ 11.286 min = 188 h × USD 220 = **USD 41.382/180 d** (~USD 6.897/mes). |
| Método | `fallas_evitadas × duración_media_falla × coste_hora`. |
| Supuesto | La duración media por falla se mantiene; el MTBF objetivo es el global, no una promesa. |
| Confianza | Media. |
| Limitación | El MTBF agregado puede ocultar máquinas con muchas fallas breves; por eso se acompaña de fallas cortas/100 h. |

### A5 · Eficiencia energética en P-SUR (prioridad 5)

| Campo | Contenido |
|---|---|
| Problema | 0,4400 kWh/unidad buena frente a 0,2923 de P-NORTE (+50 %). |
| Evidencia | `v_kpi_calidad_maquina_dia`; 1.475.959 kWh en 180 días. |
| Acción | Auditoría de motores, aire comprimido y horarios de marcha en vacío; revisar M-005 (perfil `energia`). |
| Responsable | Mantenimiento + Energía. |
| KPI de seguimiento | kWh/unidad buena, kWh totales. |
| Impacto observado | 1.475.959 kWh; 0,4400 kWh/unidad buena. |
| Impacto hipotético | Reducir 5 % el consumo = 73.798 kWh × USD 0,12 = **USD 8.856/180 d** (~USD 1.476/mes). |
| Método | `kWh × 5 % × tarifa`. |
| Supuesto | La tarifa y la reducción del 5 % son supuestos. |
| Confianza | Media-baja. |
| Limitación | No se ha medido el consumo por equipo ni el horario de marcha en vacío. |

## 5. Ranking y decisión

| Orden | Acción | Impacto hipotético/180 d | Confianza | Criticidad |
|---|---|---:|---|---|
| 1 | A1 Scrap P-SUR | USD 366.240 | Media | Alta |
| 2 | A2 Rendimiento P-SUR | USD 190.195 | Baja-media | Alta |
| 3 | A4 MTBF P-SUR | USD 41.382 | Media | Alta |
| 4 | A3 M-047 | USD 31.999 | Media | Muy alta (activo crítico) |
| 5 | A5 Energía P-SUR | USD 8.856 | Media-baja | Media |

**Decisión propuesta:** ejecutar A1 y A2 como palancas principales, A3 por
criticidad del activo y A4 como sostén de confiabilidad; A5 como mejora continua.
No se suman los ahorros: las acciones se solapan (por ejemplo, menos fallas
también reduce downtime y energía). El orden es una guía, no una suma lineal.

## 6. Comparación con las cifras del caso

| Indicador | Caso (orientativo) | Prototipo (observado) | Comentario |
|---|---:|---:|---|
| OEE | 78 % → 66 % | 78,02 % → 66,00 % (ventanas de 30 d) | Coincide por diseño del escenario `calibracion`. |
| Scrap | 3,8 % → 6,1 % | 3,66 % → 6,08 % | Muy cerca. |
| Downtime no planificado | +31 % | +49,4 % | Brecha documentada; no se forzó. |
| Energía por unidad | +14 % | +12,2 % | Cerca. |
| Pérdida mensual | USD 540.000 | No recalculada | El caso no se usa como resultado del prototipo. |

## 7. Limitaciones

- Los datos son sintéticos y el escenario `calibracion` está diseñado para mostrar
  señal; no es una medición de una fábrica real.
- Los ahorros son hipotéticos y dependen de supuestos de coste declarados.
- El Loss Tree mide minutos equivalentes; no sustituye un estudio de tiempos.
- La relación scrap ↔ producto/turno es descriptiva; no se afirma causalidad.
- El feed sintético emite dos lecturas de proceso por turno; la cadencia de 15 min
  se reporta como diagnóstico (D-022).
- Antes de implantar: validar costes, ampliar el muestreo IoT y definir metas con
  los responsables de planta.
