# Verificación del Bloque 4 — Dashboard e indicadores KPI obligatorios

> **Todos los datos son sintéticos.** La verificación se ejecutó el **2026-10-24**
> contra la base local `metalinova`. Las cifras corresponden al histórico
> calibrado de 180 días (`2026-04-22` → `2026-10-18`).

- **Alcance:** las 10 fórmulas KPI obligatorias y su implementación en SQL/DAX.
- **Método:** lectura de vistas y medidas, validación SQL específica y regresión
  `validate_data.py`.
- **Documento de validación:** `sql/validation/07_kpi_formulas.sql`.
- **Documentos relacionados:** `bloque3-aplicativo-bi.md`,
  `docs/DATA_DICTIONARY.md` y `specs/CONSTITUTION.md` §6.

## Resumen de veredictos

| # | KPI | Veredicto |
|---|---|---|
| 1 | OEE | **Cumple** |
| 2 | Disponibilidad | **Cumple** |
| 3 | Rendimiento | **Cumple** |
| 4 | Calidad | **Cumple** |
| 5 | MTBF | **Cumple** |
| 6 | MTTR | **Cumple**; alcance: correctivo cerrado |
| 7 | Downtime no planificado | **Cumple con matiz**: ratio en SQL; el informe muestra horas, no % |
| 8 | Scrap Rate | **Cumple** |
| 9 | First Pass Yield | **Cumple con matiz semántico**: implementa “sin retrabajo / procesadas”; no excluye el scrap no retrabajado |
| 10 | Energía por Unidad Buena | **Cumple** |

## 1. Fórmulas y valores globales

| KPI | Fórmula del caso | Implementación SQL | Valor global observado |
|---|---|---|---:|
| OEE | A × P × Q | `ROUND(disponibilidad*rendimiento*calidad, 6)` en `v_kpi_oee_*` | **71,9645 %** |
| Disponibilidad | runtime / tiempo planificado | `tiempo_operativo_min / tiempo_planificado_min` | **98,7918 %** |
| Rendimiento | (ideal cycle time × total count) / runtime | `minutos_ideales / tiempo_operativo_min`, con `minutos_ideales = ciclo_ideal_segundos × total_count / 60` | **76,5505 %** |
| Calidad | good count / total count | `good_count / total_count` | **95,1589 %** |
| MTBF | tiempo operativo / número de fallas | `(tiempo_operativo_min / 60) / fallas` | **85,6078 h** |
| MTTR | tiempo total de reparación / reparaciones | `minutos_reparacion / reparaciones` | **17,8392 min** |
| Downtime no planificado | minutos no planificados / tiempo planificado | `downtime_no_planificado_min / tiempo_planificado_min` | **1,2082 %** |
| Scrap Rate | unidades rechazadas / unidades producidas | `scrap_count / total_count` | **4,8411 %** |
| FPY | unidades sin retrabajo / unidades procesadas | `(unidades_inspeccionadas − unidades_retrabajo) / unidades_inspeccionadas` | **97,6295 %** |
| Energía por Unidad Buena | kWh / unidades buenas | `energia_kwh / good_count` | **0,340312 kWh** |

Comprobación aritmética del OEE global:
`0,987918 × 0,765505 × 0,951589 = 0,719645`.

**Regla de agregación:** los porcentajes nunca se promedian. Se suman numeradores
y denominadores y se divide al final. El OEE de una planta no es el promedio de
los OEE de sus máquinas.

## 2. Ejemplo por fila

**P-NORTE, M-001, turno A, PRD-001, 2026-04-22:**

| Dato | Valor |
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
| Downtime % | 0,000000 |
| Scrap Rate | 0,021924 (2,19 %) |
| Energía por Unidad Buena | 0,164437 kWh |
| FPY | 0,989038 (98,90 %) |

Comprobaciones:

- Rendimiento: `30 × 821 / 60 = 410,5 min`; `410,5 / 450 = 0,912222`.
- Calidad: `803 / 821 = 0,978076`.
- OEE: `1,000000 × 0,912222 × 0,978076 = 0,892222`.
- Scrap: `18 / 821 = 0,021924`.
- Energía: `132,0429 / 803 = 0,164437`.
- FPY: `(821 − 9) / 821 = 0,989038`.

**Ejemplo de MTBF/MTTR — M-039, turno C, 2026-04-22:**

| Dato | Valor |
|---|---:|
| Runtime | 426 min |
| Fallas | 1 |
| MTBF | 7,1000 h |
| Minutos de reparación | 16 |
| Reparaciones | 1 |
| MTTR | 16,0000 min |
| Downtime % | 5,3333 % |

Comprobación: `426 / 60 / 1 = 7,10 h`; `16 / 1 = 16 min`;
`24 / 450 = 5,3333 %`.

## 3. Detalle de implementación

### OEE y componentes

`v_kpi_produccion` calcula por fila:

```text
disponibilidad = tiempo_operativo_min / tiempo_planificado_min
rendimiento    = minutos_ideales / tiempo_operativo_min
calidad        = good_count / total_count
oee            = disponibilidad × rendimiento × calidad
```

Las vistas `v_kpi_oee_*` agregan con `SUM` de numeradores y denominadores y
redondean el OEE a 6 decimales. El redondeo es necesario para que DirectQuery
convierta el `numeric` a `Double` sin devolver `NULL`.

### MTBF

```text
mtbf_h = (tiempo_operativo_min / 60) / fallas
```

`fallas` es el conteo de paradas no planificadas que no son microparadas (regla
G6). Si no hay runtime o fallas, `mtbf_h` es `NULL` de forma intencional.

### MTTR

```text
mttr_min = minutos_reparacion / reparaciones
```

`minutos_reparacion` y `reparaciones` incluyen únicamente órdenes CMMS de tipo
**correctivo** y estado **cerrada**. Las preventivas no se cuentan como
reparación. En el histórico: 2.401 reparaciones correctivas cerradas y 227
preventivas.

### Downtime no planificado

```text
downtime_no_planificado_pct = downtime_no_planificado_min / tiempo_planificado_min
```

En `v_kpi_mantenimiento_maquina_turno`, si no hay fila de producción, se usa la
suma de paradas no planificadas de `fact_parada` como respaldo. En el informe, la
tarjeta de la página 03 muestra el downtime en **horas**, no el porcentaje; el
ratio está en la vista y en `v_kpi_oee_*`.

### Scrap Rate

```text
scrap_rate = scrap_count / total_count
```

El denominador es **unidades producidas**, no inspeccionadas.

### First Pass Yield

```text
fpy = (unidades_inspeccionadas − unidades_retrabajo) / unidades_inspeccionadas
```

El denominador es **unidades procesadas/inspeccionadas**. En este dataset,
`fact_calidad.unidades_inspeccionadas` coincide exactamente con
`fact_produccion.total_count` para las 28.080 combinaciones máquina-turno-día
(0 diferencias).

**Matiz semántico:** el numerador es “inspeccionadas − retrabajo”, no “unidades
buenas”. Por eso una unidad defectuosa que no pasó por retrabajo **sí** entra en
el numerador. El resultado es **97,6295 %**, superior a la calidad
(**95,1589 %**), porque el scrap no retrabajado no se descuenta. La definición
normativa del proyecto (G3) usa literalmente “unidades sin retrabajo”; si la
rúbrica interpreta “pasan sin retrabajo” como **buenas de primera pasada**, el
valor de referencia sería `good_count / total_count = 95,1589 %` (o un cálculo
más estricto si se distingue el retrabajo que termina en unidad buena). Es una
decisión de definición pendiente, no un error de cálculo de la vista actual.

### Energía por Unidad Buena

```text
energia_por_unidad_buena = energia_kwh / good_count
```

El denominador son **unidades buenas**, no unidades totales ni inspeccionadas.

## 4. Verificación ejecutada

Comando:

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -v ON_ERROR_STOP=1 -f /sql/validation/07_kpi_formulas.sql
```

Resultado observado (2026-10-24):

| Chequeo | Filas | Incidencias | Estado |
|---|---:|---:|---|
| OEE = A × P × Q | 540 | 0 | OK |
| Disponibilidad = runtime / planificado | 540 | 0 | OK |
| Rendimiento = minutos ideales / runtime | 540 | 0 | OK |
| Calidad = good / total | 540 | 0 | OK |
| Scrap Rate = scrap / total | 540 | 0 | OK |
| Downtime = downtime / planificado | 540 | 0 | OK |
| Energía por Unidad Buena = kWh / good | 540 | 0 | OK |
| OEE por fila = A × P × Q | 28.080 | 0 | OK |
| MTBF = horas operativas / fallas | 28.104 | 0 | OK |
| MTTR = minutos reparación / reparaciones | 28.104 | 0 | OK |
| Downtime % mantenimiento = downtime / planificado | 28.104 | 0 | OK |
| FPY = (inspeccionadas − retrabajo) / inspeccionadas | 9.360 | 0 | OK |

**Total: 12/12 comprobaciones OK.**

La comprobación de FPY valida que la vista aplica su fórmula declarada
(`inspeccionadas − retrabajo`), no que esa fórmula sea la lectura clásica de
First Pass Yield. La diferencia semántica está declarada en el §3.

También se ejecutó `python src/validate_data.py`: **49/49 comprobaciones OK**,
con recálculo independiente desde los hechos.

## 5. Cómo responder en la demo

1. **OEE:** mostrar la tarjeta 71,96 % y explicar A × P × Q.
2. **A/P/Q:** mostrar 98,79 % / 76,55 % / 95,16 % y la tendencia mensual.
3. **MTBF/MTTR:** mostrar 85,61 h / 17,84 min en la página 03 y el tooltip por
   máquina.
4. **Downtime:** mostrar la tarjeta de horas y aclarar que el ratio está en la
   vista (`1,21 %` global).
5. **Scrap/FPY:** mostrar 4,84 % y 97,63 % en la página 04.
6. **Energía:** mostrar 0,3403 kWh/unidad buena y la dispersión energía-scrap.
7. **Agregación:** aclarar que los porcentajes se ponderan, no se promedian.

## 6. Limitaciones y observaciones

1. **Downtime % sin tarjeta propia.** El ratio está calculado en SQL y se usa en
   el modelo, pero el informe muestra downtime en horas; no hay una tarjeta
   específica con el porcentaje.
2. **MTTR acotado a correctivo cerrado.** Es una decisión documentada; las
   preventivas no se consideran reparaciones.
3. **FPY con denominador inspeccionado y numerador “sin retrabajo”.** En este
   dataset el denominador coincide con las unidades producidas; si se inspecciona
   una muestra parcial, podría diferir de `total_count`. Además, el numerador no
   descuenta el scrap no retrabajado: el 97,63 % no equivale a la calidad del
   95,16 %. Hay que decidir si se mantiene la definición literal del proyecto o se
   adopta la lectura clásica de FPY.
4. **OEE redondeado a 6 decimales en las vistas KPI.** `v_kpi_produccion.oee`
   queda sin redondear; las diferencias son del orden de 1e-7 y se validan con
   tolerancia 1e-6.
5. **Datos sintéticos.** Los valores no son telemetría real.

## 7. Trazabilidad

| Tema | Archivo |
|---|---|
| Fórmulas OEE | `sql/views/03_kpi_oee.sql`; `v_kpi_produccion` |
| MTBF/MTTR/downtime | `sql/views/04_kpi_mantenimiento.sql` |
| Scrap/FPY/energía | `sql/views/05_kpi_calidad_energia.sql` |
| Definiciones | `docs/DATA_DICTIONARY.md` §Definiciones de KPI |
| Medidas DAX | `powerbi/final/measures.dax` |
| Validación de fórmulas | `sql/validation/07_kpi_formulas.sql` |
| Validación independiente | `python/src/validate_data.py` |
