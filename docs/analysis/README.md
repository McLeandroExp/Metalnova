# Análisis estadístico — figuras y tablas

> **Todos los datos son sintéticos.** Estas figuras describen el histórico generado para el
> prototipo académico (ventana 2026-04-22 → 2026-10-18), no telemetría de una fábrica real.
> El escenario `calibracion` fue diseñado para mostrar señal. Las correlaciones no implican
> causalidad.

El informe completo está en [`docs/ANALISIS_DATOS.md`](../ANALISIS_DATOS.md). Esta carpeta
contiene las figuras versionadas, el manifiesto de la corrida y este índice.

## Reproducción

```powershell
docker compose build ingestor
docker compose --profile tools run --rm ingestor python src/analyze_data.py --seed 42
docker compose --profile tools run --rm ingestor python src/validate_analysis.py
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/08_analisis.sql
```

Las tablas completas y el `manifest.json` canónico se escriben en
`data/analysis/<run_id>/` (no versionado). La copia versionada del manifiesto está en
[`manifest.json`](./manifest.json).

## Figuras

| Figura | Archivo | Qué muestra | Fuente | Nivel |
|---|---|---|---|---|
| F01 | `F01_histograma_oee.png` | Distribución del OEE, mediana y cercas IQR 1,5× | `v_kpi_oee_maquina_dia` | máquina-día |
| F02 | `F02_oee_por_planta.png` | OEE por planta con puntos | `v_kpi_oee_maquina_dia` | máquina-día |
| F03 | `F03_componentes_por_planta.png` | A, P y Q por planta | `v_kpi_oee_maquina_dia` | máquina-día |
| F04 | `F04_serie_oee.png` | Serie diaria, media móvil 7 d y tendencia; por planta | `v_kpi_oee_planta_dia` | planta-día |
| F05 | `F05_correlaciones.png` | Matriz de Pearson entre KPI | vistas OEE + mantenimiento | máquina-turno |
| F06 | `F06_dispersion_oee.png` | OEE frente a P, Q, scrap y kWh/unidad buena | `v_kpi_oee_maquina_dia` | máquina-día |
| F07 | `F07_qq_oee.png` | QQ-plot del OEE frente a una normal | `v_kpi_oee_maquina_dia` | máquina-día |
| F08 | `F08_paradas_por_causa.png` | Duración de paradas no planificadas por causa (log) | `v_parada_consolidada` | episodio |
| F09 | `F09_estabilidad_maquinas.png` | OEE medio vs CV por máquina | `v_kpi_oee_maquina_dia` | máquina |
| F10 | `F10_turno_dia_semana.png` | OEE ponderado por turno y día de la semana | `v_kpi_oee_maquina_turno` | máquina-turno |
| F11 | `F11_scrap_producto.png` | Scrap rate por producto con IC de Wilson | `v_kpi_calidad_producto_dia` | producto |
| F12 | `F12_temperatura.png` | Temperatura de proceso y umbral de 85 °C | `fact_evento` | lectura |
| F13 | `F13_mantenimiento.png` | Duración por tipo y coste vs duración | `fact_mantenimiento` | orden de trabajo |
| F14 | `F14_atipicos.png` | % de atípicos por variable y distancia de Mahalanobis | `v_kpi_oee_maquina_dia` | máquina-día |
| F15 | `F15_latencia_senal.png` | Latencia de pipeline y lecturas IoT por máquina-día | `fact_evento`, `v_calidad_senal_iot` | evento / máquina-día |
| F16 | `F16_pareto_causas.png` | Pareto de minutos de downtime no planificado | `v_parada_consolidada` | episodio |
| F17 | `F17_energia_perfil.png` | kWh/unidad buena por perfil de máquina | `v_kpi_oee_maquina_dia` + `dim_maquina` | máquina-día |
| F18 | `F18_ventanas_30d.png` | Medias móviles de 30 d de OEE, scrap y downtime | `v_kpi_oee_planta_dia` | planta-día |

## Tablas del informe

| Tabla | Contenido | Archivo de datos |
|---|---|---|
| T01 | Inventario de fuentes y recuentos | `inventario.csv` |
| T02 | Controles de integridad y duplicados | `controles.csv` |
| T03 | Nulos por variable clave | `nulos.csv` |
| T04 | Cobertura de señal IoT | `senal_iot.csv` |
| T05 | Descriptivos globales por nivel y variable | `descriptivos_global.csv` |
| T06 | OEE y componentes por planta con IC bootstrap | `descriptivos_planta.csv` |
| T07 | Pruebas de normalidad | `normalidad.csv` |
| T08 | Atípicos por variable y método | `outliers.csv` |
| T09 | Casos atípicos extremos con contexto | `outliers_top.csv` |
| T10 | Correlación del OEE con el resto de KPI | `correlaciones.csv` |
| T11 | Comparaciones por grupo | `pruebas_grupo.csv` |
| T12 | Asociaciones categóricas | `asociaciones.csv` |
| T13 | Tendencia y Mann–Kendall | `tendencia.csv` |
| T14 | Ventanas de 30 días | `ventanas_30d.csv` |
| T15 | Paradas por categoría de causa | `categorias_parada.csv` |
| T16 | Scrap por producto con IC de Wilson | `scrap_producto.csv` |
| T17 | Mantenimiento por tipo | `mantenimiento_tipo.csv` |

Archivos auxiliares: `autocorrelacion.csv`, `correlaciones_maquina.csv`,
`mahalanobis_top.csv`, `inventario_maquinas.csv`, `latencia.csv`, `resumen.json` y
`manifest.json`.

## Criterios de lectura

- Los KPI de porcentaje se agregan con `SUM(numerador) / SUM(denominador)`; la media y la
  mediana de la tabla T05 describen filas, no el KPI ponderado.
- El MTBF de máquina-turno es de corto plazo. El MTBF agregado de 180 días se calcula con
  `SUM(runtime) / SUM(fallas)`.
- Las correlaciones disponibilidad–downtime % y calidad–scrap son identidades contables, no
  hallazgos empíricos.
- Un valor atípico es una observación a revisar, no un error: los casos de M-047
  (`perfil_rendimiento = 'critica'`) son comportamiento diseñado.
