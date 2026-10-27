# Tabla maestra de cifras — MetalNova Smart Factory BI

> **Corte único:** 2026-10-24. **Base:** `metalinova` (PostgreSQL 16.4, Docker).
> **Ventana histórica:** 2026-04-22 → 2026-10-18 (180 días).
> **Datos sintéticos.** Esta tabla es la única fuente de cifras para el informe.
> Las diferencias con documentos anteriores se explican al final.

## 1. Alcance y volumen

| Indicador | Valor | Unidad | Fuente |
|---|---:|---|---|
| Plantas | 3 | plantas | `dim_planta` |
| Líneas | 6 | líneas | `dim_linea` |
| Máquinas | 52 | máquinas | `dim_maquina` |
| Familias | 3 | familias | `dim_familia` |
| Productos | 12 | productos | `dim_producto` |
| Turnos | 3 | turnos | `dim_turno` |
| Causas | 13 | causas | `dim_causa` |
| Técnicos | 12 | técnicos | `dim_tecnico` |
| Días de calendario | 1.095 | días | `dim_tiempo` |
| Días con producción | 180 | días | `fact_produccion` + `dim_tiempo` |
| Órdenes | 28.080 | filas | `dim_orden` |
| Producciones | 28.080 | filas | `fact_produccion` |
| Paradas | 76.045 | filas | `fact_parada` |
| Mantenimientos | 2.628 | filas | `fact_mantenimiento` |
| Inspecciones de calidad | 28.080 | filas | `fact_calidad` |
| Eventos de origen | 401.838 | filas | `fact_evento` |
| Eventos de máquina (IoT/SCADA) | 343.050 | filas | `fact_evento` |
| Eventos simulados `sim-*` | 51 | filas | `fact_evento` |
| Eventos en cuarentena | 2 | filas | `fact_evento_rechazado` |

**Composición de eventos:**

| Fuente | Tipo | Filas |
|---|---|---:|
| `iot` | `transicion_estado` | 208.229 |
| `iot` | `parada` | 76.045 |
| `scada` | `lectura_proceso` | 58.776 |
| `mes` | `orden_produccion` | 28.080 |
| `calidad` | `inspeccion` | 28.080 |
| `cmms` | `mantenimiento` | 2.628 |
| **Total** | | **401.838** |

## 2. OEE global

| Indicador | Valor | Unidad | Fuente |
|---|---:|---|---|
| Disponibilidad (180 d) | 98,7918 | % | `v_kpi_oee_planta_dia` |
| Rendimiento (180 d) | 76,5505 | % | `v_kpi_oee_planta_dia` |
| Calidad (180 d) | 95,1589 | % | `v_kpi_oee_planta_dia` |
| **OEE (180 d)** | **71,9645** | **%** | `v_kpi_oee_planta_dia` |
| Tiempo planificado | 12.566.679 | min | `v_kpi_oee_planta_dia` |
| Tiempo operativo | 12.414.848 | min | `v_kpi_oee_planta_dia` |
| Total count | 14.142.393 | unidades | `v_kpi_oee_planta_dia` |
| Good count | 13.457.750 | unidades | `v_kpi_oee_planta_dia` |
| Scrap | 684.643 | unidades | `v_kpi_oee_planta_dia` |
| Energía por unidad buena | 0,340312 | kWh/unidad | `v_kpi_oee_planta_dia` |

**Ventanas de 30 días:**

| Ventana | A % | P % | Q % | OEE % | Scrap % | kWh/unidad | Downtime (h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Inicio (2026-04-22 → 2026-05-21) | 99,0250 | 81,7800 | 96,3448 | **78,0226** | 3,6552 | 0,321720 | 340,48 |
| Cierre (2026-09-19 → 2026-10-18) | 98,5455 | 71,3074 | 93,9177 | **65,9961** | 6,0823 | 0,360882 | 507,65 |
| Cambio | −0,48 pp | −10,47 pp | −2,43 pp | **−12,03 pp** | +2,43 pp | **+12,2 %** | **+49,1 %** |

## 3. Plantas

| Planta | OEE 180 d | OEE 30 d | Scrap 180 d | Scrap 30 d | kWh/unidad 180 d | MTBF (h) |
|---|---:|---:|---:|---:|---:|---:|
| P-NORTE | 75,5827 | 69,3195 | 4,1918 | 5,4639 | 0,292339 | 111,4929 |
| P-CENTRO | 71,9802 | 66,0654 | 4,9476 | 6,1421 | 0,324209 | 87,0441 |
| P-SUR | **67,7313** | **62,0448** | **5,7188** | **6,9805** | **0,440006** | **66,8632** |

## 4. Líneas, máquinas y turnos

**Líneas con peor OEE en los últimos 30 días:**

| Planta | Línea | OEE % |
|---|---|---:|
| P-SUR | L3-2 | 60,9798 |
| P-SUR | L3-1 | 63,1112 |
| P-CENTRO | L2-1 | 65,8183 |
| P-CENTRO | L2-2 | 66,3131 |
| P-NORTE | L1-2 | 68,8914 |
| P-NORTE | L1-1 | 69,7476 |

**Máquinas con peor OEE:**

| Máquina | Planta | OEE 180 d | OEE 30 d | Downtime 180 d (min) | Scrap 180 d % |
|---|---|---:|---:|---:|---:|
| M-047 | P-SUR | **51,8141** | **47,4667** | 6.473 | 6,6029 |
| M-049 | P-SUR | 60,3708 | 55,3780 | 3.520 | 6,1170 |
| M-040 | P-SUR | 60,5102 | 55,5534 | 3.129 | 6,0989 |
| M-024 | P-CENTRO | 62,7826 | 57,8176 | 3.630 | 5,1411 |
| M-015 | P-NORTE | 65,8102 | 60,2172 | 3.092 | 4,6596 |
| M-032 | P-CENTRO | 66,7853 | 61,7639 | 3.063 | 9,8570 |

**M-047 por turno (últimos 30 días):**

| Turno | OEE % |
|---|---:|
| A | 49,4377 |
| B | 47,6161 |
| C | **45,3271** |

**Turnos (global):**

| Turno | OEE 180 d | OEE 30 d | Scrap 180 d % |
|---|---:|---:|---:|
| A | 74,9829 | 68,8050 | 4,5298 |
| B | 72,2442 | 66,2068 | 4,8194 |
| C | **68,6653** | **62,9757** | **5,2017** |

**Productos:**

| Producto | Familia | OEE 30 d | Scrap 30 d % | OEE 180 d | Scrap 180 d % |
|---|---|---|---:|---:|---:|---:|
| PRD-009 | FAM-TRA | **61,0558** | **7,0122** | 67,6671 | 5,7521 |
| PRD-011 | FAM-TRA | 61,3715 | 7,0577 | 69,0000 | 5,5185 |
| PRD-010 | FAM-TRA | 62,3577 | 6,9528 | 67,1626 | 5,7798 |
| PRD-012 | FAM-TRA | 63,0343 | 6,9334 | **67,0739** | **5,8240** |
| PRD-008 | FAM-SUS | 65,9037 | 5,9669 | 71,6850 | 4,9952 |

> **Cautela:** en el escenario calibrado cada planta produce una sola familia
> (P-SUR → FAM-TRA, P-CENTRO → FAM-SUS, P-NORTE → FAM-FRE). El efecto producto
> está confundido con el efecto planta.

## 5. Loss Tree

| Componente | Minutos equivalentes | Participación |
|---|---:|---:|
| Disponibilidad | 151.831 | 4,30 % |
| **Rendimiento** | **2.911.218,08** | **82,51 %** |
| Calidad | 465.420,00 | 13,19 % |
| **Total** | **3.528.469,08** | **100 %** |

| Indicador | Valor |
|---|---:|
| Unidades potenciales | 18.412.350 |
| Unidades no producidas | 4.269.957 |
| Unidades scrap | 684.643 |

**Por planta:**

| Planta | Pérdida total (min) | Rendimiento | Calidad | Disponibilidad | Unidades no producidas | Scrap |
|---|---:|---:|---:|---:|---:|---:|
| P-SUR | 1.247.666,08 | 1.037.457,83 | 158.818,25 | 51.390 | 1.329.007 | 203.466 |
| P-CENTRO | 1.218.861,08 | 1.003.987,00 | 162.942,08 | 51.932 | 1.513.484 | 245.429 |
| P-NORTE | 1.061.941,92 | 869.773,25 | 143.659,67 | 48.509 | 1.427.466 | 235.748 |

**Máquinas con mayor pérdida total:**

| Máquina | Planta | Pérdida total (min) | Rendimiento | Calidad | Disponibilidad |
|---|---|---:|---:|---:|---:|
| M-047 | P-SUR | 116.356,08 | 101.039,33 | 8.843,75 | 6.473 |
| M-049 | P-SUR | 95.739,08 | 82.733,08 | 9.486,00 | 3.520 |
| M-040 | P-SUR | 95.497,25 | 82.853,92 | 9.514,33 | 3.129 |
| M-024 | P-CENTRO | 89.921,75 | 78.084,42 | 8.207,33 | 3.630 |
| M-015 | P-NORTE | 82.627,50 | 71.793,42 | 7.742,08 | 3.092 |
| M-032 | P-CENTRO | 80.156,75 | 59.454,83 | 17.638,92 | 3.063 |

## 6. Mantenimiento y confiabilidad

| Indicador | Valor | Unidad |
|---|---:|---|
| MTBF global | 85,6078 | h |
| MTTR global | 17,8392 | min |
| Fallas | 2.417 | eventos |
| Reparaciones correctivas cerradas | 2.401 | órdenes |
| Microparadas | 43.692 | eventos |
| Minutos de microparadas | 109.020 | min |
| Fallas cortas | 2.115 | eventos |
| Minutos de fallas cortas | 30.155 | min |
| Downtime no planificado | 152.227 | min |
| Downtime no planificado | 1,2114 | % |
| Intervenciones | 2.628 | órdenes |
| Costo de mantenimiento | 1.487.567,81 | USD |

**Por planta:**

| Planta | MTBF (h) | MTTR (min) | Fallas | Microparadas | Fallas cortas | Downtime (min) | Fallas cortas/100 h | Microparadas/100 h |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P-NORTE | 111,4929 | 17,8950 | 643 | 14.867 | 560 | 48.622 | 78,11 | 2.073,79 |
| P-CENTRO | 87,0441 | 17,2088 | 823 | 15.175 | 731 | 52.144 | 102,04 | 2.118,31 |
| P-SUR | **66,8632** | 18,3425 | 951 | 13.650 | 824 | 51.461 | **129,59** | 2.146,67 |

**Perfiles de confiabilidad:**

| Máquina | Planta | Downtime (min) | Fallas | Fallas cortas | Microparadas | MTBF (h) | Fallas cortas/100 h | Microparadas/100 h | MTTR (min) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M-047 | P-SUR | 6.473 | 141 | 103 | 1.178 | 27,78 | 262,97 | 3.007,61 | 25,11 |
| M-024 | P-CENTRO | 3.634 | 58 | 48 | 1.011 | 68,40 | 121,00 | 2.548,49 | 18,83 |
| M-049 | P-SUR | 3.520 | 72 | 60 | 905 | 55,12 | 151,19 | 2.280,42 | 18,18 |
| M-041 | P-SUR | 3.434 | 78 | 67 | 796 | 50,95 | 168,58 | 2.002,79 | 17,78 |
| M-015 | P-NORTE | 3.095 | 30 | 25 | 968 | 132,60 | 62,85 | 2.433,37 | — |
| M-025 | P-CENTRO | 2.609 | 25 | 22 | 884 | 159,51 | 55,17 | 2.216,78 | — |

## 7. Causas de parada

| Categoría | Código | Planificada | Eventos | Minutos |
|---|---|---|---:|---:|
| Microparada | MICRO | No | 43.692 | 109.020 |
| Falla | F-MEC | No | 867 | 15.356 |
| Falla | F-ELE | No | 582 | 10.546 |
| Falla | F-NEU | No | 388 | 6.803 |
| Falla | F-HID | No | 339 | 6.242 |
| Ajuste | AJUSTE | No | 241 | 4.260 |
| Descanso | DESCANSO | Sí | 28.080 | 842.400 |
| Cambio | CAM-PROD | Sí | 1.629 | 49.150 |
| Mantenimiento | MANT-PREV | Sí | 227 | 20.171 |

## 8. Calidad y energía

| Indicador | Valor | Unidad |
|---|---:|---|
| Unidades producidas | 14.142.393 | unidades |
| Unidades buenas | 13.457.750 | unidades |
| Scrap | 684.643 | unidades |
| Scrap Rate | 4,8411 | % |
| Energía total | 4.579.830,0233 | kWh |
| Energía por unidad buena | 0,340312 | kWh/unidad |
| Inspeccionadas | 14.142.393 | unidades |
| Retrabajo | 335.248 | unidades |
| FPY | 97,6295 | % |
| Tasa de defectos | 4,8411 | % |
| Tasa de retrabajo | 2,3705 | % |

**Scrap por turno:**

| Turno | Total | Scrap | Scrap % |
|---|---:|---:|---:|
| A | 4.898.545 | 221.894 | 4,5298 |
| B | 4.731.532 | 228.032 | 4,8194 |
| C | 4.512.316 | 234.717 | 5,2017 |

**Scrap por producto (180 días):**

| Producto | Familia | Scrap % |
|---|---|---:|
| PRD-012 | FAM-TRA | 5,8240 |
| PRD-010 | FAM-TRA | 5,7798 |
| PRD-009 | FAM-TRA | 5,7521 |
| PRD-011 | FAM-TRA | 5,5185 |
| PRD-005 | FAM-SUS | 5,0549 |
| PRD-008 | FAM-SUS | 4,9952 |
| PRD-007 | FAM-SUS | 4,9128 |
| PRD-006 | FAM-SUS | 4,8347 |

## 9. Alertas de máquina crítica

| Severidad | Filas |
|---|---:|
| Alerta | 3.284 |
| Crítica | 248 |
| Sin alerta | 24.572 |
| **Total** | **28.104** |

- Alertas en el último turno por máquina: **13**.
- Ejemplo crítico: **M-015, turno C, 2026-10-18**; OEE 52,63 %, MTBF 7,00 h, temperatura máxima 79,29 °C, downtime 30 min; condiciones OEE bajo + MTBF bajo; acciones: revisión PDCA e inspección preventiva.
- Ejemplo crítico: **M-028, turno C, 2026-10-18**; OEE 61,57 %, MTBF 7,32 h, temperatura máxima 88,19 °C, downtime 11 min; condiciones MTBF bajo + temperatura alta.

## 10. Calidad de datos IoT

| Indicador | Valor |
|---|---:|
| Eventos rechazados | 2 |
| Motivo `timestamp_anterior_al_rango` | 1 |
| Motivo `timestamp_futuro` | 1 |
| Eventos tardíos marcados | 1 |
| Eventos reordenados marcados | 1 |
| Duplicados `(source_system, source_event_id)` | 0 |
| Filas de señal IoT | 9.360 |
| Máquinas con señal | 52 |
| `max_gap_min` | 210 |
| Estado `ok` | 9.360 |
| Estado `incompleta` | 0 |
| Estado `sin_datos` | 0 |
| Latencia mínima | 0,7 ms |
| Latencia media | 28,2 ms |
| Latencia máxima | 54,9 ms |
| Solapes de paradas | 0 |

## 11. Validación y desempeño

| Prueba | Resultado |
|---|---|
| `validate_data.py` | 49/49 OK |
| `sql/validation/07_kpi_formulas.sql` | 12/12 OK |
| `validate_iot.py` | 11/11 OK |
| `sql/validation/04_iot.sql` | 5/5 OK |
| `verify_history.py` | 17/17 OK |
| `sql/validation/03_calibracion.sql` | 7/7 OK |
| `validate_model.py` | 70 medidas, 27 relaciones, 15 tablas; OK |
| `validate_report.py` | 8 páginas, 105 visuales, 0 errores |
| Apertura DirectQuery | 35,46 s (mediana) |
| Cambio de filtro | 0,5 s tarjeta/línea; 2,64 s ventana completa |
| Frescura DirectQuery | 0,35 s |
| Consulta de alerta | 335–464 ms |
| Vista de paradas consolidadas | ~245 ms |

## 12. Comparación con el caso

| Indicador | Caso (orientativo) | Prototipo (observado) | Comentario |
|---|---:|---:|---|
| OEE | 78 % → 66 % | 78,02 % → 66,00 % | Coincide por diseño del escenario `calibracion`. |
| Scrap | 3,8 % → 6,1 % | 3,66 % → 6,08 % | Muy cerca. |
| Downtime no planificado | +31 % | +49,1 % | Brecha documentada; no se forzó. |
| Energía por unidad | +14 % | +12,2 % | Cerca. |
| Pérdida mensual | USD 540.000 | No recalculada | El caso no se usa como resultado del prototipo. |

## 13. Reconciliación documental

| Dato | Documentos anteriores | Corte 2026-10-24 | Decisión |
|---|---:|---:|---|
| Eventos | 401.832 / 401.838 | **401.838** | Usar 401.838. |
| Paradas | 76.042 / 76.045 | **76.045** | Usar 76.045. |
| MTBF | 85,71 h / 85,61 h | **85,6078 h** | Usar 85,6078 h. |
| Filas de alerta | 28.101 / 28.104 | **28.104** | Usar 28.104. |
| Alertas último turno | 13 | **13** | Sin cambio. |

**Motivo:** las cifras menores corresponden a cortes previos a los 51 eventos
`sim-*` y a la última ingesta. El corte 2026-10-24 es el más reciente y coincide
con `docs/verification/bloque6-producto-criterios.md`.

## 14. Fuente de cada bloque

| Bloque | Fuente principal |
|---|---|
| Volumen | `fact_*`, `dim_*`; `docs/verification/bloque1` |
| OEE | `v_kpi_oee_planta_dia`, `v_kpi_oee_maquina_dia`, `v_kpi_oee_maquina_turno` |
| Loss Tree | `v_loss_tree`; `docs/verification/bloque5` |
| Mantenimiento | `v_kpi_mantenimiento_planta_dia`, `v_kpi_mantenimiento_maquina_dia` |
| Calidad/energía | `v_kpi_calidad_maquina_dia`, `v_kpi_calidad_producto_dia` |
| Alertas | `v_alerta_maquina_critica`, `v_alerta_ultimo_turno` |
| IoT | `fact_evento`, `fact_evento_rechazado`, `v_calidad_senal_iot` |
| Validación | `docs/TEST_PLAN.md`, `docs/verification/bloque6` |
| Desempeño | `docs/DECISIONS.md` D-019, `specs/006-powerbi/verification.md` |
