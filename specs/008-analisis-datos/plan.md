# Plan técnico — Incremento 008

## 1. Principios de diseño

1. **Una sola fuente de verdad por variable.** Los KPI y ratios se leen de las vistas (`v_kpi_*`);
   las distribuciones de episodios y eventos se leen de los hechos; las dimensiones solo agrupan.
   No se recalcula un KPI en pandas si ya existe una vista validada.
2. **Niveles de análisis explícitos.** Fila de producción (28.080), máquina-día (9.360),
   máquina-turno (28.080), planta-día (540) y máquina (52). Cada tabla declara su nivel.
3. **Ratios ponderados y distribuciones separadas.** El agregado usa `SUM(numerador) / SUM(denominador)`;
   la distribución usa media/mediana de las filas. Nunca se presenta el promedio de porcentajes como KPI.
4. **Inferencia honesta.** Con n grande se reportan tamaños de efecto e intervalos de confianza,
   no solo p-valores; se corrige por comparaciones múltiples.
5. **Reproducibilidad.** Semilla fija, versión fijada de paquetes, manifiesto con SHA-256 y
   metadatos de fecha desactivados en los PNG.

## 2. Fuentes y filtros

| Bloque | Fuente |
|---|---|
| OEE, A, P, Q, scrap, energía/unidad, downtime % | `v_kpi_oee_maquina_dia`, `v_kpi_oee_maquina_turno`, `v_kpi_oee_planta_dia`, `v_kpi_produccion` |
| MTBF, MTTR, fallas, microparadas, fallas cortas | `v_kpi_mantenimiento_maquina_turno` |
| Paradas | `v_parada_consolidada` (KPI) y `v_parada_detalle` (recuento crudo) |
| Mantenimiento | `fact_mantenimiento` + dimensiones |
| Calidad | `fact_calidad`, `v_kpi_calidad_maquina_dia`, `v_kpi_calidad_producto_dia` |
| Temperatura, energía por evento, latencia | `fact_evento`, `v_calidad_senal_iot` |
| Estratificación | `dim_planta`, `dim_linea`, `dim_maquina`, `dim_turno`, `dim_causa`, `dim_producto`, `dim_familia`, `dim_tiempo`, `dim_tecnico` |

Ventana: `2026-04-22 → 2026-10-18` (180 días, definida por `id_tiempo`/`fecha`).

Exclusiones del análisis principal, documentadas y cuantificadas:

- paradas con `causa_detalle LIKE 'Ingesta 004:%'` (24, del 2026-10-22, fuera de ventana);
- eventos `run_id LIKE 'sim-%'` (51); se usan solo en latencia y calidad IoT;
- `fact_evento_rechazado` (2, artefactos de la prueba G5).

## 3. Estructura de archivos

```text
specs/008-analisis-datos/{spec,plan,tasks,verification}.md
python/requirements-analysis.txt      pandas, numpy, scipy, matplotlib (versiones fijas)
python/src/analyze_data.py            motor de análisis y generación del informe
python/src/validate_analysis.py       validación SQL vs Python
sql/validation/08_analisis.sql        controles estructurales del análisis
docs/ANALISIS_DATOS.md                informe final
docs/analysis/figures/F01..F18.png    figuras versionadas
docs/analysis/README.md               índice de figuras y tablas
docs/analysis/manifest.json           copia versionada del manifiesto de la corrida
data/analysis/<run_id>/*.csv|json     salidas completas (no versionadas)
logs/analyze_data_<run_id>.log        log de la corrida
```

Cambios de infraestructura:

- `python/Dockerfile`: instala `requirements-analysis.txt` en la misma imagen del ingestor.
- `compose.yaml`: monta `./docs:/app/docs` para que el contenedor escriba el informe y las figuras.

## 4. Cálculos

### 4.1 Descriptiva

Por variable: `n`, nulos, `%` nulos, media, mediana, desviación estándar muestral, coeficiente
de variación, mínimo, Q1, Q3, IQR, máximo, asimetría y curtosis (Fisher). Global y por planta.
Intervalos de confianza al 95 % de la mediana por bootstrap percentil (2.000 réplicas, semilla fija).

### 4.2 Distribuciones y normalidad

Histogramas, boxplots y QQ-plot. Pruebas: D'Agostino–Pearson (`normaltest`) sobre la muestra
completa y Shapiro–Wilk sobre submuestra de 5.000 (límite práctico), Levene por planta para
homocedasticidad. Se advierte que con n grande las pruebas rechazan normalidad por desviaciones
irrelevantes; por eso se complementan con asimetría, curtosis y QQ-plot.

### 4.3 Atípicos

- IQR: fuera de `[Q1 − 1,5·IQR, Q3 + 1,5·IQR]`; extremos con factor 3.
- z-score: `|z| > 3`.
- z-score modificado: `0,6745·(x − mediana) / MAD`, umbral `3,5`.
- multivariante: Mahalanobis sobre `(disponibilidad, rendimiento, calidad)` con covarianza
  pseudoinversa y umbral `χ²(0,975; 3)`; se reporta también la versión robusta por MAD.

Los atípicos no se eliminan: se clasifican y se contrastan con `perfil_rendimiento`, criticidad
y eventos de demo. Un outlier de OEE en M-047 es comportamiento diseñado, no error de dato.

### 4.4 Correlación

Pearson y Spearman por pares con `n` efectivo, p-valor bilateral, IC 95 % de Fisher para Pearson
y corrección de Benjamini–Hochberg sobre todos los pares únicos. Se calcula en dos niveles:
máquina-turno (variables operativas) y máquina agregada (52 casos), para mostrar si el signo
cambia con el nivel de agregación.

### 4.5 Comparaciones

ANOVA de una vía y Kruskal–Wallis por planta, turno y tipo de máquina; Levene; post-hoc de
Mann–Whitney con corrección de Holm; `η²` para ANOVA y `ε²` para Kruskal–Wallis. Chi-cuadrado
y V de Cramér para planta × categoría de causa y turno × scrap alto.

### 4.6 Temporal

Serie diaria ponderada (A, P, Q, OEE, scrap, energía, downtime), media móvil de 7 días,
regresión lineal (pendiente por día, R², p), Mann–Kendall, autocorrelación lag 1–14 y
comparación de las primeras y últimas 30 jornadas.

### 4.7 Categóricas

Frecuencias y minutos por categoría de causa, Pareto de downtime no planificado, tipos de
mantenimiento (n, minutos, coste), scrap por producto con IC de Wilson y mapa de calor
turno × día de la semana.

## 5. Salidas

- `descriptivos_global.csv`, `descriptivos_planta.csv`
- `normalidad.csv`, `outliers.csv`, `outliers_top.csv`, `mahalanobis_top.csv`
- `correlaciones.csv`, `correlaciones_maquina.csv`
- `pruebas_grupo.csv`, `tendencia.csv`, `autocorrelacion.csv`, `ventanas_30d.csv`
- `categorias_parada.csv`, `mantenimiento_tipo.csv`, `scrap_producto.csv`
- `senal_iot.csv`, `latencia.csv`, `calidad_datos.csv`, `inventario.csv`
- `resumen.json`, `manifest.json`
- `docs/ANALISIS_DATOS.md` con F01–F18 y tablas T01–T13

## 6. Validación

`validate_analysis.py` recalcula en SQL recuentos, medias, medianas, desviaciones y correlaciones
y las compara con los CSV de la última corrida (tolerancia `1e-9`). `sql/validation/08_analisis.sql`
comprueba estructura, invariantes, nulos y cobertura con salida `estado = OK/ERROR`.

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| p-valores inflados por n grande | tamaños de efecto, IC y FDR |
| falacia ecológica al agregar | correlación en dos niveles y declaración explícita |
| disponibilidad casi constante (techo) | se reporta su baja varianza y se evita interpretarla como palanca |
| mezclar histórico y simulación | filtros por `run_id` y `causa_detalle`, tabla de exclusiones |
| repetición no determinista | semilla fija y `metadata={"Software": None}` en PNG |
| dependencias nuevas | versión fija, una sola imagen, sin impacto en la demo |
| confundir atípico con error | clasificación con contexto y revisión del perfil de máquina |

## 8. Decisiones

- D-024: niveles de análisis y prohibición de promediar ratios.
- D-025: reglas de atípicos (IQR 1,5×/3×, z, MAD, Mahalanobis).
- D-026: correlación e inferencia (Pearson/Spearman, FDR, tamaños de efecto, no causalidad).
- D-027: dependencias de análisis dentro del contenedor y montaje de `docs/`.
