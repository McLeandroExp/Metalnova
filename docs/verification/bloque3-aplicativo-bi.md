# Verificación del Bloque 3 — Desarrollo del aplicativo / prototipo BI

> **Todos los datos son sintéticos.** La verificación estructural se ejecutó el
> **2026-10-24** sobre `powerbi/final/MetalNova.pbip` y la base local `metalinova`.
> La verificación visual en Power BI Desktop fue la del **2026-10-23**, registrada
> en `specs/006-powerbi/verification.md` y en `docs/capturas/`.

- **Alcance:** 4 páginas, interactividad, visualización operativa y alerta de
  máquina crítica.
- **Método:** lectura de PBIR/TMDL, validadores `validate_model.py` y
  `validate_report.py`, consultas SQL y evidencia visual existente.
- **Documentos relacionados:** `bloque1-negocio-modelo.md`,
  `bloque2-modelado-dimensional.md`, `solapes-paradas.md`.

## Resumen de veredictos

| # | Punto | Veredicto |
|---|---|---|
| 1 | 4 páginas: Executive, OEE & Loss Tree, Maintenance, Quality/Energy | **Cumple** |
| 2 | Filtros por planta, línea, máquina, producto y turno | **Cumple**: 6 slicers sincronizados por página |
| 3 | Drill-through a historial de una máquina | **Cumple**: `pageBinding` Drillthrough por `maquina_codigo` |
| 4 | Tooltip con última intervención, MTBF y MTTR | **Cumple**: página Tooltip asignada a tablas |
| 5 | Navegación desde pérdida de OEE hacia causa | **Cumple**: drill-through por `dim_causa[categoria]` |
| 6 | Serie temporal con límites/umbrales | **Cumple**: OEE mensual con referencia 85 % |
| 7 | Pareto de downtime | **Cumple con matiz**: barras ordenadas por downtime; sin línea acumulada |
| 8 | Matriz máquina-turno con formato condicional | **Cumple**: gradiente 55 % / 70 % / 85 % |
| 9 | Regla de excepción de máquina crítica y accionabilidad | **Cumple con matiz**: 4 condiciones, acción, responsable y KPI; temperatura estimada por lecturas discretas |

---

## 1. Páginas del informe

El informe tiene **8 páginas**: 4 principales y 4 de apoyo.

| Página | Tipo | Contenido principal | Evidencia |
|---|---|---|---|
| 01 Executive Plant Performance | Principal | 6 tarjetas, tendencia y ranking por planta, tabla de alertas del último turno, 6 slicers | PBIR `page_executive_01`; captura `01-executive.png` |
| 02 OEE & Loss Tree | Principal | A/P/Q, pérdida total, brecha meta, Pareto de causas, pérdida por producto, matriz máquina-turno y Loss Tree por planta | PBIR `page_oee_02`; captura `02-oee-loss-tree.png` |
| 03 Maintenance Reliability | Principal | MTBF, MTTR, fallas, downtime, intervenciones, costo, tendencia mensual, dispersión de fallas cortas y tabla por máquina | PBIR `page_maintenance_03`; captura `03-maintenance.png` |
| 04 Quality & Energy | Principal | FPY, scrap, defectos, retrabajo, energía por unidad buena, energía total, scrap por planta/turno/producto y dispersión energía-scrap | PBIR `page_quality_04`; captura `04-quality-energy.png` |
| Detalle máquina | Drillthrough | Historial mensual de OEE, paradas, intervenciones y calidad de una máquina | PBIR `page_detalle_maquina`; captura `detalle-maquina.png` |
| Detalle causa | Drillthrough | Máquinas, turnos y pérdidas asociadas a una causa del Pareto | PBIR `page_detalle_causa`; captura `detalle-causa.png` |
| Tooltip máquina | Tooltip | MTBF, MTTR y última intervención | PBIR `page_tooltip_maquina`; captura `tooltip-maquina.png` |
| Modelo validado (T-604) | Apoyo oculta | Validación de las tarjetas del modelo | PBIR `0bf126b4ec1041db`; captura `modelo-validado-t604.png` |

**9 KPIs obligatorios cubiertos:** OEE, disponibilidad, rendimiento, calidad,
scrap rate, FPY, MTBF, MTTR y energía por unidad buena. Se reparten entre las
tarjetas de las cuatro páginas.

Validación estructural:

```text
python tools/validate_report.py
Páginas: 8 · Visuales: 105
Resultado: OK · todas las referencias y páginas son coherentes
```

## 2. Interactividad

### 2.1 Filtros por planta, línea, máquina, producto y turno

Cada una de las 4 páginas principales tiene **6 slicers**:

| Slicer | Campo |
|---|---|
| Fecha | `dim_tiempo.fecha` |
| Planta | `v_dim_maquina.planta_nombre` |
| Línea | `v_dim_maquina.linea_nombre` |
| Máquina | `v_dim_maquina.maquina_codigo` |
| Producto | `v_dim_producto.producto_nombre` |
| Turno | `dim_turno.codigo` |

Los slicers están sincronizados entre páginas con los grupos `sync_fecha`,
`sync_planta`, `sync_linea`, `sync_maquina`, `sync_producto` y `sync_turno`. La
configuración incluye `fieldChanges = true`, `filterChanges = true` y
`drillFilterOtherVisuals = true`.

**Evidencia:** los 4 grupos de slicers existen en las 4 páginas; el usuario
verificó la sincronización el 2026-10-23 (`specs/006-powerbi/verification.md`,
AC-603).

### 2.2 Drill-through a historial de una máquina

La página `Detalle máquina` está oculta y tiene:

- `pageBinding.type = Drillthrough`;
- filtro `drill_maquina` por `v_dim_maquina.maquina_codigo`;
- `chart_oee_historial` (línea mensual de OEE);
- `table_paradas`, `table_intervenciones` y `table_calidad_maquina`.

El usuario probó «Obtener detalles» desde la tabla de confiabilidad el 2026-10-23
(AC-604). La captura `detalle-maquina.png` muestra la página.

### 2.3 Tooltip con última intervención, MTBF y MTTR

La página `Tooltip máquina` es de tipo `Tooltip`, con filtro por
`v_dim_maquina.maquina_codigo` y tres tarjetas:

| Tarjeta | Medida |
|---|---|
| `tooltip_mtbf` | `v_kpi_mantenimiento_maquina_turno.MTBF (h)` |
| `tooltip_mttr` | `v_kpi_mantenimiento_maquina_turno.MTTR (min)` |
| `tooltip_ultima` | `v_kpi_mantenimiento.Ultima Intervención` |

Está asignada como `visualTooltip` a `table_confiabilidad` (página 03) y a
`table_maquinas_causa` (Detalle causa). El usuario confirmó el hover el
2026-10-23; captura `tooltip-maquina.png`.

**Ejemplo de valores para M-047:** última intervención `2026-10-18 08:04 UTC`,
MTTR 27,89 min, MTBF 27,78 h.

### 2.4 Navegación desde pérdida de OEE hacia causa

La página `Detalle causa` está oculta y tiene:

- `pageBinding.type = Drillthrough`;
- filtro `drill_causa` por `dim_causa.categoria`;
- tarjetas de paradas, downtime, máquinas afectadas y participación;
- `chart_causa_turno` (downtime por turno);
- `table_maquinas_causa` con máquina, planta, MTBF, MTTR y downtime.

El `chart_pareto_causas` de la página 02 usa `dim_causa.categoria` como categoría
y `Downtime por Causa (min)` como medida, por lo que el drill-through por causa
está alineado con el Pareto. El usuario lo probó el 2026-10-23 (AC-604); captura
`detalle-causa.png`.

## 3. Visualización operativa

### 3.1 Serie temporal con umbral

`chart_oee_planta` es un `lineChart` de OEE mensual por planta. Tiene una
`y1AxisReferenceLine` visible, discontinua, en **0,85 (85 %)**. Es la serie
temporal con límite/umbral que pide el caso.

### 3.2 Pareto de downtime

`chart_pareto_causas` es un `barChart`:

- categoría: `dim_causa.categoria`;
- medida: `v_kpi_parada.Downtime por Causa (min)`;
- ordenado por la medida de downtime;
- título: «Pareto de downtime no planificado por causa».

**Matiz:** es un Pareto de barras ordenadas, sin línea de porcentaje acumulado.
El contrato del proyecto lo acepta así (`docs/CUMPLIMIENTO.md`, requisito 19). Si
la rúbrica exige la línea acumulada, habría que añadirla.

### 3.3 Matriz máquina-turno con formato condicional

`matrix_maquina_turno` es un `pivotTable` con:

- filas: `v_dim_maquina.maquina_codigo` y `dim_turno.codigo`;
- valores: `OEE KPI` y `Pérdida Total (min)`;
- formato condicional `linearGradient3` sobre OEE:
  - rojo `#F8696B` en 0,55;
  - ámbar `#FFEB84` en 0,70;
  - verde `#63BE7B` en 0,85;
  - `nullColoringStrategy = noColor`.

El usuario confirmó la matriz con formato condicional el 2026-10-23 (AC-605).

## 4. Alerta de máquina crítica

### 4.1 Regla

La regla vive en `v_alerta_maquina_critica` y se evalúa por **máquina × turno ×
día**. Se emite alerta si se cumple **al menos una** condición; la severidad es
**crítica** si se cumplen **dos o más**.

| Condición | Umbral | Acción | Responsable |
|---|---:|---|---|
| OEE bajo | < 55 % | Revisar pérdida dominante con ciclo PDCA | Producción |
| MTBF bajo | < 20 h | Inspección preventiva anticipada | Mantenimiento |
| Temperatura alta | > 85 °C durante ≥ 15 min | Verificar refrigeración/lubricación | Mantenimiento |
| Downtime acumulado | > 120 min/turno | Reasignar capacidad o intervenir | Producción |

Los umbrales están centralizados en `v_kpi_parametros`:
`oee_umbral=0.55`, `mtbf_umbral_h=20`, `temperatura_umbral_c=85`,
`temperatura_ventana_min=15`, `temperatura_lecturas_min=2`,
`downtime_umbral_min=120`.

La regla expone `acciones_sugeridas`, `responsables`, `kpis_seguimiento`,
`condiciones`, `condiciones_cumplidas`, `severidad` y `tiene_alerta`. El informe
usa `v_alerta_ultimo_turno` para la tabla de alertas, de modo que la regla no
depende de filtros visuales.

### 4.2 Ejemplo accionable

**M-015, turno C, 2026-10-18:**

| Campo | Valor |
|---|---|
| OEE | 52,63 % → cumple OEE bajo |
| MTBF | 7,00 h → cumple MTBF bajo |
| Temperatura máxima | 79,29 °C → no cumple |
| Downtime | 30 min → no cumple |
| Condiciones | `OEE bajo | MTBF bajo` |
| Severidad | **crítica** (2 condiciones) |
| Acciones | revisar pérdida dominante con PDCA; inspección preventiva anticipada |
| Responsables | Producción | Mantenimiento |
| KPIs de seguimiento | OEE | MTBF |

**Otro ejemplo:** M-028, turno C, cumple MTBF bajo y temperatura alta (88,19 °C);
severidad crítica; acciones de inspección preventiva y revisión de refrigeración.

**Distribución observada:**

| Ámbito | Alerta | Crítica | Sin alerta | Total |
|---|---:|---:|---:|---:|
| Toda la historia (`v_alerta_maquina_critica`) | 3.284 | 248 | 24.572 | 28.104 |
| Último turno por máquina (`v_alerta_ultimo_turno`) | 12 | 1 | — | 13 con alerta |

### 4.3 Por qué es accionable

1. Cada condición tiene un **umbral numérico** y una **acción concreta**.
2. Cada acción tiene un **responsable** (Producción o Mantenimiento).
3. Cada alerta enlaza a un **KPI de seguimiento** (OEE, MTBF, temperatura o
   downtime).
4. Se evalúa por **máquina y turno**, que es la unidad donde se puede intervenir.
5. La tabla de alertas del informe muestra severidad, OEE, MTBF, temperatura y
   acción sugerida; la vista conserva además responsable y KPI.

**Matiz:** la tabla visual `table_alertas` muestra `acciones_sugeridas` y
`severidad`, pero no las columnas `responsables` y `kpis_seguimiento`. Están en la
vista SQL y en esta documentación. Si se quiere que el visual muestre el
responsable, habría que añadir esa columna.

**Matiz de temperatura:** el feed sintético emite 2–5 lecturas por turno, no una
cada 15 min. La regla exige ≥ 2 lecturas > 85 °C y estima
`minutos_temp_alta_estimados = lecturas × 15`; es una aproximación declarada
(D-022), no una medición continua.

## 5. Verificaciones ejecutadas

| Verificación | Resultado |
|---|---|
| `python tools/validate_report.py` | 8 páginas, 105 visuales, 0 errores |
| `python tools/validate_model.py` | 70 medidas, 27 relaciones, 15 tablas; OK |
| `python src/validate_data.py` | 49/49 comprobaciones OK; distribución de alertas coherente |
| PBIR: 4 páginas principales | Nombres y visuales presentes |
| PBIR: 6 slicers por página | 4 páginas con los mismos 6 `sync_*` |
| PBIR: drill-through máquina | `pageBinding` y filtro por `maquina_codigo` |
| PBIR: drill-through causa | `pageBinding` y filtro por `causa.categoria` |
| PBIR: tooltip | Página `Tooltip`, 3 tarjetas, asignada a 2 tablas |
| PBIR: referencia OEE | `y1AxisReferenceLine = 0.85` |
| PBIR: matriz | `pivotTable` con gradiente 0,55/0,70/0,85 |
| SQL: alerta | 4 condiciones, umbrales y acciones/responsables |
| Capturas | 8 páginas capturadas el 2026-10-23, 0 fallos |

## 6. Cómo responder en la demo

1. **Páginas:** abrir las 4 páginas principales y nombrar su propósito.
2. **Filtros:** seleccionar P-SUR, L3-2 y turno C; mostrar que el filtro se
   mantiene al cambiar de página.
3. **Drill-through máquina:** desde la tabla de confiabilidad, «Obtener detalles»
   de M-047; mostrar el historial y las tablas.
4. **Tooltip:** pasar el cursor por una máquina en la tabla de confiabilidad;
   mostrar MTBF, MTTR y última intervención.
5. **Navegación a causa:** desde el Pareto, «Obtener detalles» de una causa;
   mostrar máquinas, turnos y pérdidas.
6. **Serie temporal:** mostrar la línea de OEE y la referencia 85 %.
7. **Pareto:** mostrar el orden descendente por downtime.
8. **Matriz:** mostrar el gradiente rojo-ámbar-verde de OEE por máquina-turno.
9. **Alerta:** abrir un caso como M-015 C y explicar las dos condiciones, la
   severidad crítica, la acción y el responsable.

## 7. Limitaciones y observaciones

1. **Pareto sin línea acumulada.** Es un Pareto de barras ordenadas; si la
   rúbrica exige el porcentaje acumulado, falta esa línea.
2. **Responsable/KPI fuera de la tabla de alertas.** La vista los tiene; el visual
   solo muestra la acción y la severidad.
3. **Tooltip asignado a dos tablas.** No está configurado en todos los visuales;
   cumple el requisito, pero no es global.
4. **Temperatura aproximada.** La regla usa lecturas discretas y estima minutos;
   no es una medición continua.
5. **Datos sintéticos.** Las cifras de alertas y KPIs son del escenario calibrado.
6. **Cifras mutables.** Si se ejecuta nueva ingesta simulada, los conteos cambian.

## 8. Reproducción

```powershell
# Validación estructural del informe y del modelo
python tools/validate_report.py
python tools/validate_model.py

# Validación de KPI y alertas
docker compose run --rm ingestor python src/validate_data.py

# Distribución y ejemplo de alertas
docker exec metalnova_db psql -U metalinova -d metalinova -c "select severidad, count(*) from v_alerta_maquina_critica group by 1 order by 1;"
docker exec metalnova_db psql -U metalinova -d metalinova -c "select maquina_codigo, turno_codigo, condiciones, acciones_sugeridas, responsables, kpis_seguimiento from v_alerta_maquina_critica where fecha='2026-10-18' and maquina_codigo='M-015' and turno_codigo='C';"
```

## 9. Trazabilidad

| Tema | Archivo |
|---|---|
| Páginas y visuales | `powerbi/final/MetalNova.Report/definition/pages/` |
| Medidas | `powerbi/final/measures.dax` |
| Relaciones y jerarquías | `powerbi/final/MetalNova.SemanticModel/definition/` |
| Regla de alerta | `sql/views/08_alerta_maquina_critica.sql` |
| Umbrales | `v_kpi_parametros`; `docs/DATA_DICTIONARY.md` §8 |
| Verificación visual 2026-10-23 | `specs/006-powerbi/verification.md` |
| Capturas | `docs/capturas/README.md` |
| Validación de KPI | `python/src/validate_data.py` |
