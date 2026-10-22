# Guía de construcción — Informe final 006

> Esta guía se conserva como **fallback manual** de la generación automática.
> El modelo semántico y las páginas ya se generan con `tools/generate_tmdl.py` y
> `tools/generate_pbir.py`; `tools/validate_report.py` comprueba las referencias.
> Úsala solo si un visual no renderiza y hay que reconstruirlo en Desktop.
> Todos los datos son **sintéticos**.

## 0. Antes de empezar

1. Cerrar Power BI Desktop sin guardar si estaba abierto.
2. Reabrir `powerbi/final/MetalNova.pbip`.
3. Pulsar **Actualizar ahora** y confirmar que `OEE último mes` muestra ≈65,51 %.
4. Guardar una copia del `.pbip` antes de empezar las páginas.
5. Mantener la página `Modelo validado (T-604)` hasta terminar la verificación; no se borra.

La conexión es DirectQuery a `127.0.0.1`, base `metalinova`, usuario `metalinova`. La contraseña
está en `.env` y no se versiona.

## 1. Controles comunes

Estos filtros deben repetirse en las cuatro páginas y sincronizarse:

| Control | Tabla | Campo |
|---|---|---|
| Fecha | `dim_tiempo` | `fecha` (intervalo) |
| Planta | `v_dim_maquina` | `planta_nombre` |
| Línea | `v_dim_maquina` | `linea_nombre` |
| Máquina | `v_dim_maquina` | `maquina_codigo` |
| Familia | `v_dim_producto` | `familia_nombre` |
| Turno | `dim_turno` | `turno_codigo` |

Pasos:

1. Insertar una segmentación por cada fila de la tabla.
2. En **Ver → Sincronizar segmentaciones**, marcar las cuatro páginas para cada segmentación.
3. Ocultar los controles que no se usen en una página concreta, pero no eliminarlos.
4. Añadir un botón **Restablecer filtros** con `Inicio → Botones → Restablecer`.

## 2. Página 1 — Executive Plant Performance

Nombre de página: `01 Executive Plant Performance`.

### Tarjetas superiores

| Tarjeta | Medida | Formato |
|---|---|---|
| OEE global | `OEE KPI` | 0,00 % |
| OEE último mes | `OEE Último Mes` | 0,00 % |
| Disponibilidad | `Disponibilidad KPI` | 0,00 % |
| Rendimiento | `Rendimiento KPI` | 0,00 % |
| Calidad | `Calidad KPI` | 0,00 % |
| Alertas activas | `Alertas Activas` | entero |

Disposición sugerida: seis tarjetas en una fila, 300×150 px cada una.

### Tendencia y comparación

1. **Gráfico de líneas**
   - Eje X: `dim_tiempo[fecha]` (jerarquía `Calendario` → `Año/Mes`).
   - Eje Y: `OEE KPI`.
   - Leyenda: `v_dim_maquina[planta_codigo]`.
   - Línea de referencia: 85 % (`OEE Meta`), discontinua.
2. **Gráfico de barras**
   - Eje Y: `v_dim_maquina[planta_codigo]`.
   - Eje X: `OEE KPI`.
   - Etiquetas de datos y línea de referencia en 85 %.
3. **Tarjeta de contexto**
   - `MTBF (h)` y `MTTR (min)`.

### Alertas del último turno

Insertar una tabla con:

- `v_alerta_maquina_critica[maquina_codigo]`
- `v_alerta_maquina_critica[severidad]`
- `v_alerta_maquina_critica[oee]`
- `v_alerta_maquina_critica[mtbf_h]`
- `v_alerta_maquina_critica[max_temperatura_c]`
- `v_alerta_maquina_critica[acciones_sugeridas]`

Filtros de la tabla:

```text
es_ultimo_turno_maquina = true
tiene_alerta = true
```

Ordenar por `severidad` (crítica primero) y luego por `oee` ascendente. Añadir formato
condicional rojo a `severidad = "critica"`.

## 3. Página 2 — OEE & Loss Tree

Nombre de página: `02 OEE & Loss Tree`.

### Tarjetas

- `OEE KPI`
- `Disponibilidad KPI`
- `Rendimiento KPI`
- `Calidad KPI`
- `Pérdida Total (min)`
- `Brecha Meta (pp)`

### Pérdidas

1. **Tarjetas de pérdidas**: `Pérdida Disponibilidad (min)`, `Pérdida Rendimiento (min)`,
   `Pérdida Calidad (min)`.
2. **Pareto de downtime**
   - Eje Y: `v_kpi_parada[causa_categoria]`.
   - Eje X: `Downtime por Causa (min)`.
   - Línea secundaria: `Pareto %` (eje derecho, 0–100 %).
   - Ordenar de mayor a menor.
3. **Matriz máquina-turno**
   - Filas: `v_dim_maquina[maquina_codigo]` y `dim_turno[turno_codigo]`.
   - Valores: `OEE KPI`, `Pérdida Total (min)`.
   - Formato condicional de fondo en `OEE KPI`: rojo <55 %, ámbar 55–70 %, verde >70 %.
   - Filtro de fecha: últimos 30 días mediante la segmentación común.

### Drill-through

1. Crear una página oculta `Detalle máquina` con:
   - `v_dim_maquina[maquina_codigo]`, `planta_codigo`, `perfil_rendimiento`.
   - Tarjetas `OEE KPI`, `MTBF (h)`, `MTTR (min)`, `Scrap Rate (Calidad)`.
   - Tendencia de `OEE KPI` por fecha.
2. En la página 2, configurar **Drill-through** por `v_dim_maquina[maquina_codigo]`.
3. Agregar botón **Volver** en la página de detalle.

La página oculta no cuenta como una de las cuatro páginas principales.

## 4. Página 3 — Maintenance Reliability

Nombre de página: `03 Maintenance Reliability`.

### Tarjetas

- `MTBF (h)`
- `MTTR (min)`
- `Fallas (conteo)`
- `Downtime Mantenimiento (min)`
- `Intervenciones`
- `Costo Mantenimiento (USD)`

### Visuales

1. **Barras de downtime por causa**
   - Eje Y: `v_kpi_parada[causa_categoria]`.
   - Eje X: `Downtime por Causa (min)`.
   - Resaltar la causa principal.
2. **Línea de MTBF mensual**
   - Eje X: `dim_tiempo[anio_mes]`.
   - Eje Y: `MTBF (h)`.
   - Leyenda: `v_dim_maquina[planta_codigo]`.
3. **Tabla de máquinas**
   - `v_dim_maquina[maquina_codigo]`
   - `MTBF (h)`
   - `MTTR (min)`
   - `Fallas (conteo)`
   - `Última Intervención`
   - `perfil_rendimiento`
   - Ordenar por MTBF ascendente.
4. **Tooltips**
   - En la tabla, configurar un tooltip con `MTBF (h)`, `MTTR (min)` y `Última Intervención`.
   - En las barras, mostrar `Paradas No Planificadas` y `Downtime por Causa (min)`.

## 5. Página 4 — Quality & Energy

Nombre de página: `04 Quality & Energy`.

### Tarjetas

- `FPY KPI`
- `Scrap Rate (Calidad)`
- `Tasa Defectos`
- `Tasa Retrabajo`
- `Energía por Unidad Buena`
- `Energía (kWh)`

### Visuales

1. **Tendencia mensual**
   - Eje X: `dim_tiempo[anio_mes]`.
   - Eje Y: `Scrap Rate (Calidad)` y `FPY KPI` en líneas separadas.
2. **Scrap por planta**
   - Eje Y: `v_dim_maquina[planta_codigo]`.
   - Eje X: `Scrap Rate (Calidad)`.
   - Etiquetas y referencia al objetivo de scrap (6,1 %).
3. **Energía por máquina**
   - Eje Y: `v_dim_maquina[maquina_codigo]`.
   - Eje X: `Energía por Unidad Buena`.
   - Resaltar M-005 (`perfil_rendimiento = "energia"`).
4. **Dispersión energía vs scrap**
   - Eje X: `Energía por Unidad Buena`.
   - Eje Y: `Scrap Rate (Calidad)`.
   - Detalles: `maquina_codigo`.
   - Tamaño: `Unidades Totales`.
5. **Tabla de calidad**
   - `maquina_codigo`, `FPY KPI`, `Tasa Defectos`, `Tasa Retrabajo`, `Energía por Unidad Buena`.

## 6. Navegación y acabado

1. Insertar botones de navegación a las cuatro páginas en la parte superior.
2. Ocultar la página de validación al terminar; no borrarla.
3. Aplicar un tema coherente (fondo claro, acentos azul/verde).
4. Revisar que no haya visuales con error o campos vacíos.
5. Guardar como `powerbi/final/MetalNova.pbip` y hacer una captura por página.

## 7. Verificación mínima por página

| Página | Debe mostrar |
|---|---|
| Executive | 6 KPIs, tendencia por planta, comparación entre plantas y alertas del último turno |
| OEE & Loss Tree | A/P/Q, pérdidas, Pareto de causas y matriz máquina-turno |
| Maintenance | MTBF, MTTR, fallas, downtime, costo y última intervención |
| Quality & Energy | FPY, scrap, defectos, retrabajo, energía total y energía por unidad buena |

Registrar los valores observados en `specs/006-powerbi/verification.md`; no marcar una página como
terminada sin la captura y la comprobación de sus filtros.
