# Verificación del Bloque 6 — Producto esperado y criterios mínimos de aceptación

> **Todos los datos son sintéticos.** La verificación se ejecutó el **2026-10-24**
> sobre el prototipo local. La evidencia visual es la del **2026-10-23**, registrada
> en `specs/006-powerbi/verification.md` y `docs/capturas/`.

- **Alcance:** cierre del producto esperado y de los cinco criterios mínimos de
  aceptación.
- **Método:** regresión de KPI, validación SQL, validación de modelo/informe y
  revisión de la documentación de cada bloque.
- **Documentos base:** `bloque1` a `bloque5`, `solapes-paradas.md` y
  `pregunta-principal-business-understanding.md`.

## Matriz de aceptación

| # | Criterio mínimo | Evidencia principal | Veredicto |
|---|---|---|---|
| 1 | Fórmulas de OEE y componentes reconciliadas con los datos base | `sql/validation/07_kpi_formulas.sql` 12/12; `validate_data.py` 49/49; OEE 71,9645 % | **Cumple** |
| 2 | Modelo con múltiples hechos y dimensiones conformadas correctamente relacionadas | 4 hechos analíticos + 2 capas crudas; 10 dimensiones; 27 relaciones hecho→dimensión; 0 duplicados de grano | **Cumple con matiz** (técnico denormalizado en Power BI) |
| 3 | Prototipo con mínimo 4 vistas, 9 KPIs y navegación máquina → detalle | 4 páginas principales; 9 KPIs; 8 páginas/105 visuales; drill-through, tooltip y navegación a causa | **Cumple** |
| 4 | Manejo explícito de calidad y temporalidad de eventos IoT | `event_quality.py`, cuarentena, tardío/reordenado, `v_calidad_senal_iot`; `validate_iot.py` 11/11 | **Cumple con matiz** (`unknown` no se emite) |
| 5 | Plan de mejora priorizado y cuantificado | `PLAN_MEJORA.md`: 5 acciones, impacto observado/hipotético, supuestos, confianza y limitaciones | **Cumple** |

**Resultado global:** el producto esperado se cumple. Los matices están declarados
y no bloquean la entrega; son decisiones de presentación o de definición que
conviene mencionar en la defensa.

---

## 1. OEE y componentes reconciliados

### Evidencia

- `sql/validation/07_kpi_formulas.sql`: **12/12 comprobaciones OK**.
- `python src/validate_data.py`: **49/49 comprobaciones OK**.
- OEE global: **71,9645 %**.
- Componentes: A **98,7918 %** · P **76,5505 %** · Q **95,1589 %**.
- `0,987918 × 0,765505 × 0,951589 = 0,719645`.

| KPI | Fórmula | Valor |
|---|---|---:|
| OEE | A × P × Q | 71,9645 % |
| Disponibilidad | runtime / planificado | 98,7918 % |
| Rendimiento | minutos ideales / runtime | 76,5505 % |
| Calidad | good / total | 95,1589 % |
| MTBF | runtime / fallas | 85,6078 h |
| MTTR | minutos reparación / reparaciones | 17,8392 min |
| Downtime | downtime / planificado | 1,2082 % |
| Scrap Rate | scrap / total | 4,8411 % |
| FPY | (inspeccionadas − retrabajo) / inspeccionadas | 97,6295 % |
| Energía por Unidad Buena | kWh / good | 0,340312 kWh |

**Verificación:** las vistas KPI se recalculan desde los hechos con tolerancia
1e-9 (OEE con 1e-6 por el redondeo a 6 decimales documentado). No hay promedios
de porcentajes: se suman numeradores y denominadores.

**Matiz conocido:** la definición de FPY es literal (“sin retrabajo”), no la
lectura clásica de “buenas de primera pasada”. Está documentado en
`bloque4-kpi-obligatorios.md`.

---

## 2. Modelo multidimensional

### Hechos

| Tabla | Grano | Filas | Duplicados de grano |
|---|---|---:|---:|
| `fact_produccion` | orden + máquina + turno + día | 28.080 | 0 |
| `fact_parada` | episodio de parada | 76.045 | 0 |
| `fact_mantenimiento` | orden de trabajo | 2.628 | 0 |
| `fact_calidad` | inspección / lote | 28.080 | 0 |
| `fact_evento` | evento crudo de origen | 401.838 | 0 |
| `fact_evento_rechazado` | evento en cuarentena | 2 | — |

Las cuatro tablas analíticas son el modelo estrella; `fact_evento` y
`fact_evento_rechazado` son la capa cruda/cuarentena.

### Dimensiones

| Dimensión | Filas |
|---|---:|
| `dim_planta` | 3 |
| `dim_linea` | 6 |
| `dim_maquina` | 52 |
| `dim_familia` | 3 |
| `dim_producto` | 12 |
| `dim_turno` | 3 |
| `dim_causa` | 13 |
| `dim_tiempo` | 1.095 |
| `dim_tecnico` | 12 |
| `dim_orden` | 28.080 |

### Relaciones y jerarquías

- **27 relaciones** en el modelo TMDL, todas **hecho → dimensión**.
- **0 relaciones hecho-hecho**.
- Jerarquías: `Planta → Línea → Máquina`, `Familia → Producto`,
  `Categoría → Detalle` (causa) y `Año → Trimestre → Mes → Día`.
- Planta y línea se resuelven a través de `dim_maquina`/`v_dim_maquina`; producto
  y familia, a través de `v_dim_producto`.
- Consistencia: 540 comparaciones planta-día y 1.080 línea-día contra la suma de
  máquina-turno, con **0 discrepancias**.

**Matiz:** `dim_tecnico` existe en SQL y `fact_mantenimiento` tiene la FK, pero en
Power BI el técnico está denormalizado en `v_kpi_mantenimiento`; no hay una tabla
de técnico separada ni un slicer. Es una decisión de exposición, no una ruptura
del modelo.

---

## 3. Prototipo, KPIs y navegación

### Páginas

| Página | Contenido |
|---|---|
| 01 Executive Plant Performance | OEE, A/P/Q, OEE último mes, alertas activas, tendencia y ranking por planta |
| 02 OEE & Loss Tree | A/P/Q, pérdida total, brecha meta, Pareto, pérdida por producto, matriz máquina-turno y Loss Tree por planta |
| 03 Maintenance Reliability | MTBF, MTTR, fallas, downtime, intervenciones, costo, tendencia y tabla por máquina |
| 04 Quality & Energy | FPY, scrap, defectos, retrabajo, energía, scrap por planta/turno/producto y dispersión energía-scrap |

Además: Detalle máquina (drill-through), Detalle causa (drill-through), Tooltip
máquina y página oculta de validación. Total: **8 páginas, 105 visuales**.

### 9 KPIs

OEE, disponibilidad, rendimiento, calidad, scrap rate, FPY, MTBF, MTTR y energía
por unidad buena. Se distribuyen en 24 tarjetas.

### Navegación

- **Filtros:** 6 slicers sincronizados por página (fecha, planta, línea, máquina,
  producto, turno).
- **Máquina → detalle:** `pageBinding` Drillthrough por `maquina_codigo`;
  historial de OEE, paradas, intervenciones y calidad.
- **Tooltip:** página Tooltip con MTBF, MTTR y última intervención; asignada a
  tablas de confiabilidad y detalle de causa.
- **Pérdida → causa:** `pageBinding` Drillthrough por `dim_causa.categoria`,
  alineado con el Pareto.

**Evidencia:** `tools/validate_report.py` 8 páginas/105 visuales, 0 errores;
capturas del 2026-10-23 en `docs/capturas/`.

---

## 4. Calidad y temporalidad de eventos IoT

### Reglas implementadas

| Problema | Tratamiento |
|---|---|
| Duplicados | `ON CONFLICT (source_system, source_event_id)` |
| Timestamps fuera de rango | Rechazo a `fact_evento_rechazado` con motivo |
| Evento tardío | Se acepta y se marca `payload.calidad.tardio = true` |
| Evento reordenado | Se acepta y se marca `payload.calidad.reordenado = true` |
| Lecturas faltantes | `v_calidad_senal_iot` declara faltantes y `max_gap_min`; no hay *carry-forward* |
| Fuente de verdad de parada | Transición IoT/SCADA para inicio/fin; CMMS explica |
| Solapes | `v_parada_consolidada` une intervalos estrictamente solapados |

### Evidencia observada

| Comprobación | Resultado |
|---|---:|
| Eventos en cuarentena | 2 |
| Motivos | 1 `timestamp_futuro`, 1 `timestamp_anterior_al_rango` |
| Eventos tardíos marcados | 1 |
| Eventos reordenados marcados | 1 |
| Duplicados de `(source_system, source_event_id)` | 0 |
| Filas de señal IoT | 9.360 |
| Faltantes vs mínimo por turno | 0 |
| `max_gap_min` | 210 |
| `cumple_cadencia_15min` | `false` en 9.360/9.360 |
| `validate_iot.py` | 11/11 OK |

**Matiz:** la vista declara el hueco y la cadencia, pero **no emite el estado
`unknown`** que pide la Constitución cuando el hueco supera 15 min; usa
`ok`/`incompleta`/`sin_datos`. Está documentado en `bloque2` y D-022. El manejo es
explícito, pero el etiquetado `unknown` queda como brecha.

**Nota de solapes:** la consolidación está implementada en la capa analítica;
`fact_parada` crudo se conserva. El OEE sigue usando `fact_produccion`. Ver
`solapes-paradas.md`.

---

## 5. Plan de mejora priorizado y cuantificado

`docs/PLAN_MEJORA.md` contiene 5 acciones con:

- problema y evidencia;
- acción y responsable;
- KPI de seguimiento;
- impacto observado;
- impacto hipotético;
- método de cálculo;
- supuesto;
- confianza;
- limitación.

| Orden | Acción | Impacto hipotético/180 d | Criticidad |
|---|---|---:|---|
| 1 | A1 · Scrap en P-SUR | USD 366.240 | Alta |
| 2 | A2 · Rendimiento en P-SUR | USD 190.195 | Alta |
| 3 | A4 · MTBF de P-SUR | USD 41.382 | Alta |
| 4 | A3 · Intervención en M-047 | USD 31.999 | Muy alta |
| 5 | A5 · Energía en P-SUR | USD 8.856 | Media |

El ranking usa impacto económico y criticidad operacional; A3 sube por la
criticidad de M-047. Los ahorros no se suman porque las acciones se solapan. Los
costos son supuestos sintéticos declarados (USD 220/h, USD 18/unidad,
USD 0,12/kWh). Se distingue impacto observado, hipotético y cifras del caso.

**Evidencia complementaria:** `bloque5-analisis-descubrimiento.md`.

---

## 6. Observaciones finales

1. **No hay bloqueos de aceptación.** Los 5 criterios se cumplen; los matices son
   de definición o presentación.
2. **FPY:** la fórmula literal “sin retrabajo” da 97,63 %, no la calidad 95,16 %.
   Si la rúbrica exige FPY clásico, hay que decidir y cambiar la definición.
3. **Downtime %:** existe en SQL, pero el informe muestra horas y no una tarjeta
   de porcentaje.
4. **Pareto:** barras ordenadas, sin línea acumulada.
5. **Técnico:** dimensión en SQL, denormalizada en Power BI.
6. **`unknown` IoT:** el hueco se declara, pero no se emite ese estado.
7. **Datos sintéticos:** todas las cifras son del escenario calibrado.

## 7. Reproducción

```powershell
# Fórmulas de KPI
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/validation/07_kpi_formulas.sql

# Regresión independiente
docker compose run --rm ingestor python src/validate_data.py

# Calidad IoT
docker compose run --rm ingestor python src/validate_iot.py

# Informe y modelo (si se ejecutan, revisar que no dejen cambios en powerbi/)
python tools/validate_report.py
python tools/validate_model.py
```

## 8. Trazabilidad

| Criterio | Documento |
|---|---|
| OEE y componentes | `bloque4-kpi-obligatorios.md`; `sql/validation/07_kpi_formulas.sql` |
| Modelo multidimensional | `bloque2-modelado-dimensional.md`; `docs/ARCHITECTURE.md` |
| Prototipo y navegación | `bloque3-aplicativo-bi.md`; `docs/capturas/README.md` |
| IoT | `bloque2-modelado-dimensional.md` §4; `specs/004`; `specs/007` |
| Plan de mejora | `docs/PLAN_MEJORA.md`; `bloque5-analisis-descubrimiento.md` |
| Matriz de cumplimiento | `docs/CUMPLIMIENTO.md` |
