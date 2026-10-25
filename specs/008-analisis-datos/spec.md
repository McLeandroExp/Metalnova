# Incremento 008 — Análisis estadístico exploratorio

Estado: hecho · Depende de: 003, 005 · Habilita: —

## Contexto

El caso práctico no exige explícitamente un análisis estadístico, pero el proyecto ya dispone
de 180 días de hechos sintéticos validados y de 20 vistas KPI. Este incremento añade una capa
de análisis descriptivo e inferencial reproducible sobre esos datos: medidas de tendencia
central y dispersión, forma de las distribuciones, valores atípicos, correlación, comparaciones
entre grupos, evolución temporal y asociaciones categóricas.

El análisis **no redefine KPI ni modifica el modelo dimensional**: consume las vistas KPI como
contrato analítico y los hechos como fuente de distribuciones y casos individuales. Todos los
datos son sintéticos y el escenario `calibracion` fue diseñado para mostrar señal; el informe
lo declara en cada sección.

## Requisitos funcionales

| ID | Requisito |
|---|---|
| FR-801 | Inventariar tablas, vistas y dimensiones usadas, con recuentos, granularidad y ventana temporal. |
| FR-802 | Auditar la calidad de los datos: nulos, duplicados, rangos, invariantes de producción y cobertura de señal IoT. |
| FR-803 | Calcular estadística descriptiva (n, media, mediana, desviación estándar, CV, mínimo, Q1, Q3, IQR, máximo, asimetría y curtosis) de las variables numéricas de los hechos y de las vistas KPI, en global y por planta. |
| FR-804 | Analizar la forma de las distribuciones (histogramas, boxplots, QQ-plot) y aplicar pruebas de normalidad adecuadas al tamaño de muestra. |
| FR-805 | Detectar valores atípicos con al menos tres métodos univariantes (IQR 1,5× y 3×, z-score y z-score modificado/MAD) y uno multivariante (distancia de Mahalanobis), reportando recuentos, porcentajes y casos relevantes con contexto. |
| FR-806 | Calcular matrices de correlación de Pearson y Spearman entre los KPI, con n por par, p-valores, intervalos de confianza y corrección por comparaciones múltiples (Benjamini–Hochberg). |
| FR-807 | Comparar grupos (planta, turno, tipo de máquina, perfil) con ANOVA/Kruskal–Wallis, prueba de Levene, post-hoc corregido y tamaños de efecto; aplicar chi-cuadrado y V de Cramér a tablas de contingencia. |
| FR-808 | Analizar la evolución temporal: serie diaria, media móvil de 7 días, tendencia lineal, Mann–Kendall, autocorrelación y comparación de ventanas de 30 días. |
| FR-809 | Analizar variables categóricas: causas de parada, tipos de mantenimiento, productos y turnos, con frecuencias, Pareto y asociaciones. |
| FR-810 | Generar al menos 15 figuras PNG y un informe Markdown con tablas trazables a su tabla/vista de origen y a su n. |
| FR-811 | Registrar un manifiesto reproducible con versión, semilla, ventana, filtros, recuentos, versiones de paquetes y SHA-256 de las salidas. |
| FR-812 | Validar de forma independiente en SQL los recuentos, medias, medianas, desviaciones y correlaciones calculadas en Python. |
| FR-813 | Documentar el incremento en `specs/`, `README.md`, `docs/DATA_DICTIONARY.md`, `docs/DECISIONS.md` y `docs/TEST_PLAN.md`. |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-801 | `analyze_data.py` se ejecuta en el contenedor, termina con código 0 y produce todas las salidas declaradas. |
| AC-802 | Dos ejecuciones con la misma semilla y datos producen SHA-256 idénticos en CSV y PNG. |
| AC-803 | Los estadísticos recalculados en SQL coinciden con los de Python con tolerancia `1e-9`. |
| AC-804 | Toda variable numérica de los hechos y de las vistas KPI tiene descriptivos, cuartiles y recuento de atípicos. |
| AC-805 | Cada figura y tabla del informe declara su fuente y su n. |
| AC-806 | El informe advierte que los datos son sintéticos, que el escenario está calibrado y que la correlación no implica causalidad. |
| AC-807 | El incremento queda documentado y `verification.md` contiene comandos, salidas observadas y fecha. |
| AC-808 | Las validaciones existentes (`validate_data.py` 49/49 y `sql/validation/02..07`) siguen pasando. |

## Fuera de alcance

- Inferencia causal, experimentos o modelos predictivos.
- Nuevas páginas de Power BI o cambios al modelo semántico.
- Modificación del informe académico `docs/informe/`.
- Cambios en definiciones de KPI, esquema o reglas de negocio.
- Análisis de datos reales: todo el insumo es sintético.

## Dependencias

- 003: histórico de 180 días cargado.
- 005: vistas KPI y validación independiente.
- 004: solo para latencia y calidad IoT (los eventos `sim-*` se analizan aparte).
