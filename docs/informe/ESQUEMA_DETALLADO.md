# Esquema detallado del informe — Caso MetalNova de BI

> **Documento de trabajo.** Acompaña al borrador `MetalNova_Informe_Caso_Practico_v0.1.docx`.
> **Corte de cifras:** 2026-10-24. **Datos sintéticos.**
> **Extensión objetivo:** 50–55 páginas. **Entrega:** 26/10/2026.

## 1. Datos generales

| Campo | Valor |
|---|---|
| Autor | Leandro Arguello |
| Universidad | Universidad Central del Ecuador |
| Facultad | Ciencias Aplicadas |
| Carrera | Sistemas de la Información |
| Asignatura | Inteligencia de Negocios |
| Período | 2026-2026 |
| Modalidad | Informe de caso práctico — Examen Complexivo |
| Ciudad, año | Quito, 2026 |
| Tutor/docente | No aplica |
| Título | Caso MetalNova de BI: diseño y evaluación de un prototipo de inteligencia de negocio para medir el OEE y priorizar pérdidas en una fábrica de componentes automotrices |

## 2. Estructura y paginación

| Parte | Sección | Págs. | Figuras | Tablas |
|---|---|---:|---|---|
| Preliminares | Portada, TOC, listas, resumen, abstract | 5 | — | — |
| Cuerpo | 1. Introducción | 3 | F1 | T1 |
| | 2. Marco teórico | 5 | F2 | T2, T3 |
| | 3. Metodología experimental | 7 | F3, F4, F5 | T4–T8 |
| | 4. Análisis y resultados | 10 | F6–F10 | T9–T17 |
| | 5. Discusión | 5 | — | T18, T19 |
| | 6. Conclusiones | 2 | — | — |
| | 7. Recomendaciones | 2 | — | T20 |
| | 8. Referencias | 2 | — | — |
| Anexos | A-G (+ guion aparte) | 10 | D1-D8 | B1-B5 |
| **Total** | | **~55** | **10 + 8** | **20 + 5** |

## 3. Contenido por sección

### 1. Introducción (3 páginas)

1.1 **Contexto y problema.** MetalNova, 3 plantas, 6 líneas, 52 máquinas; caída del OEE de 78,02 % a 66,00 % en ventanas de 30 días; pérdida de rendimiento de 2,91 millones de minutos; 4,27 millones de unidades no producidas; 684.643 unidades scrap; valorización hipotética de USD 10,67 M + 0,56 M + 12,32 M en 180 días. Énfasis: los datos están fragmentados y no existe una definición única de KPI.
1.2 **Pregunta principal y preguntas específicas.** Pregunta del caso; subpreguntas sobre componente dominante, activos/turnos/productos, causas de parada, calidad/energía y priorización.
1.3 **Objetivos.** General: diseñar y evaluar un prototipo BI que mida el OEE y priorice pérdidas. Específicos: modelo dimensional; pipeline histórico y continuo; KPIs validados; tablero con navegación; análisis de pérdidas; plan de mejora.
1.4 **Justificación.** Académica (aplicación de BI, modelado dimensional y análisis), práctica (decisiones de mantenimiento/producción) y metodológica (reproducibilidad y trazabilidad).
1.5 **Alcance y limitaciones.** Prototipo local, sin nube, escenario calibrado, 180 días; no es telemetría real ni una implantación. Tabla T1 con requisitos del caso vs. alcance.
1.6 **Estructura del informe.** Breve guía de lectura.

**Figura F1.** Árbol del problema. **Tabla T1.** Requisitos del caso vs. alcance del prototipo.

### 2. Marco teórico (5 páginas)

2.1 **Business Intelligence.** Concepto, arquitectura, ciclo de valor y factores de éxito (Curto Díaz, 2010; Howson, 2008). Del dato al indicador y a la decisión.
2.2 **OEE y las seis grandes pérdidas.** Definición, fórmula, componentes, limitaciones y críticas (Nakajima, 1988; Muchiri & Pintelon, 2008; Jonsson & Lesshammar, 1999; Dal et al., 2000). Tabla T2 con fórmulas.
2.3 **TPM, mantenimiento y confiabilidad.** Estrategias de mantenimiento, MTBF, MTTR, fallas cortas y microparadas (Ahuja & Khamba, 2008; Swanson, 2001; Mobley, 2002; ISO 14224:2016).
2.4 **Calidad, rendimiento y energía.** Scrap, FPY, kWh por unidad buena; diferencia entre calidad y FPY; riesgo de promediar porcentajes.
2.5 **Modelado dimensional y KPIs.** Hechos, dimensiones conformadas, jerarquías, modelo estrella y gobierno de indicadores (Kimball & Ross, 2013; Parmenter, 2015; ISO 22400-2:2014).
2.6 **Analítica descriptiva, diagnóstica y predictiva.** Alcance del prototipo; por qué no se entrena un modelo predictivo; trabajo futuro (Witten & Frank, 2005).
2.7 **IoT, Industria 4.0 y calidad de datos.** CPS, sensores, latencia, duplicados, eventos tardíos, cuarentena (Lee et al., 2015; Batini et al., 2009).
2.8 **Business Analysis y CRISP-DM.** Business Understanding, requisitos, stakeholders y evaluación de soluciones (IIBA, 2015; Wirth & Hipp, 2000).
2.9 **Síntesis y marco conceptual.** Vacíos identificados y marco propio del informe. Tabla T3 y Figura F2.

**Tabla T2.** Fórmulas y definiciones de KPI. **Tabla T3.** Síntesis de literatura y vacíos. **Figura F2.** Marco conceptual.

### 3. Metodología experimental (7 páginas)

3.1 **Diseño.** Investigación aplicada, cuantitativa, longitudinal, no experimental; estudio de caso con unidades embebidas; fases CRISP-DM + SDD. Figura F3.
3.2 **Caso y unidad de análisis.** 3 plantas, 6 líneas, 52 máquinas, 180 días, 28.080 combinaciones máquina-turno-día. Censo sintético, no muestra.
3.3 **Fuentes y generación.** IoT/SCADA, MES, CMMS, calidad, turnos; ERP parcial. Fuente de verdad para paradas, conteos, energía/temperatura y calidad. Semilla 42, escenario `calibracion`, 7 perfiles outlier. Tabla T4.
3.4 **Modelo dimensional.** Hechos, dimensiones, granularidad, jerarquías y reglas de integridad. Figura F4 y Tabla T5.
3.5 **Arquitectura y decisiones tecnológicas.** PostgreSQL 16.4, Docker Compose, Python 3.13, Power BI Desktop, DirectQuery, CSV, TMDL/PBIR, pgAdmin. Alternativas descartadas y motivos. Figura F5.
3.6 **Calidad y temporalidad IoT.** Duplicados, tardíos, reordenados, faltantes, fuera de rango, solapes; cuarentena; `unknown` no emitido. Tabla T6.
3.7 **Operacionalización de KPIs.** Fórmulas, agregación ponderada, `NULL`, casos borde; FPY literal vs. FPY clásico.
3.8 **Tablero y alerta.** Cuatro páginas, seis slicers, drill-through, tooltip; regla multicriterio de máquina crítica. Tabla T7.
3.9 **Validación y reproducibilidad.** 49/49, 12/12, 11/11, 5/5, 17/17, 7/7; SHA-256; validadores TMDL/PBIR. Tabla T8.
3.10 **Ética.** Datos sintéticos, sin datos personales, sin secretos, límites de causalidad.

**Figura F3.** Fases metodológicas. **Figura F4.** Modelo estrella. **Figura F5.** Arquitectura.
**Tablas T4–T8.** Fuentes, modelo, IoT, alerta, validación.

### 4. Análisis y resultados (10 páginas)

4.1 **Volumen y calidad.** 401.838 eventos; 343.050 de máquina; 180 días; 0 duplicados; 2 rechazos; 1 tardío; 1 reordenado; 9.360 filas de señal; `max_gap_min = 210`. Tabla T9.
4.2 **OEE global y ventanas.** 71,9645 % global; 78,0226 → 65,9961; A/P/Q; scrap 3,6552 → 6,0823; kWh 0,321720 → 0,360882; downtime 340,48 → 507,65 h. Tablas T10, T11 y Figura F6.
4.3 **Loss Tree.** Rendimiento 2.911.218,08 min (82,51 %); calidad 465.420 min (13,19 %); disponibilidad 151.831 min (4,30 %); 4.269.957 unidades no producidas. Tabla T12 y Figura F7.
4.4 **Focos.** P-SUR 62,0448 % (30 d); L3-2 60,9798 %; M-047 47,4667 % (30 d) y 51,8141 % (180 d); turno C 45,3271 % en M-047; PRD-009 61,0558 % y scrap 7,0122 %. Tabla T13.
4.5 **Causas.** Microparadas 43.692 eventos / 109.020 min; F-MEC 867 / 15.356; F-ELE 582 / 10.546; Pareto con curva acumulada. Tabla T14 y Figura F8.
4.6 **Confiabilidad.** MTBF 85,6078 h; MTTR 17,8392 min; 2.417 fallas; 43.692 microparadas; 2.115 fallas cortas; M-047, M-015 y M-025 como perfiles distintos. Tabla T15 y Figura F9.
4.7 **Calidad y energía.** Scrap 4,8411 %; FPY 97,6295 %; kWh/unidad 0,340312; turno C 5,2017 %; PRD-012 5,8240 %. Tabla T16.
4.8 **Alertas.** 3.284 alertas, 248 críticas, 24.572 sin alerta; 13 en el último turno; ejemplos M-015 y M-028. Tabla T17.
4.9 **Tablero.** Cuatro páginas, filtros, drill-through y tooltip; capturas en Anexo D; Figura F10.
4.10 **Validación y desempeño.** 49/49, 12/12, 11/11, 5/5, 17/17, 7/7; DirectQuery 35,46 s; filtro 0,5 s; frescura 0,35 s. Tabla T17.
4.11 **Priorización económica.** A1–A5; impacto observado vs. hipotético; no sumar ahorros.

**Figuras F6–F10.** OEE, Loss Tree, Pareto, confiabilidad, panel integrado. **Tablas T9–T17.**

### 5. Discusión (5 páginas)

5.1 **Rendimiento vs. disponibilidad.** La caída no es principalmente un problema de paradas; la disponibilidad se mantiene en 98,55 % al cierre y el rendimiento cae 10,47 pp. Contraste con la atribución inicial del caso.
5.2 **Microparadas y fallas cortas.** M-047 concentra el problema; M-015 y M-025 tienen MTBF alto pero microparadas frecuentes; el promedio oculta.
5.3 **Calidad y causalidad.** Scrap vs. producto/turno/energía/temperatura es descriptivo; confusión producto-planta; no se afirma causalidad.
5.4 **Del dato al dinero.** USD 220/h, USD 18/unidad, USD 0,12/kWh son supuestos; la pérdida observada no es un ahorro; sensibilidad del ranking.
5.5 **Contraste con el caso y la literatura.** Coincidencia de OEE y scrap; brecha en downtime; límites del OEE; factores de éxito de BI (Howson); modelado dimensional (Kimball); calidad de datos (Batini).
5.6 **Aportes metodológicos.** Contrato único de KPI, agregación ponderada, cuarentena IoT, reproducibilidad, tablero con navegación.
5.7 **Limitaciones y validez.** Diseño académico, escenario calibrado, ERP parcial, cadencia IoT, `unknown` no emitido, FPY, Pareto sin línea en Power BI, DirectQuery, ausencia de implantación. Tabla T19.
5.8 **Implicaciones.** Qué haría MetalNova con esto; qué requiere una implantación real.

**Tabla T18.** Comparación caso vs. prototipo. **Tabla T19.** Limitaciones y amenazas a la validez.

### 6. Conclusiones (2 páginas)

6.1 Respuesta a la pregunta principal.
6.2 Cumplimiento de objetivos (tabla breve o lista).
6.3 Hallazgos principales (5–6).
6.4 Aportes.
6.5 Trabajo futuro.

### 7. Recomendaciones (2 páginas)

7.1 Acciones A1–A5 con responsable, KPI, horizonte e impacto hipotético. Tabla T20.
7.2 Mejoras de datos/BI: FPY, Pareto acumulado, temperatura, ERP, `unknown`, cadencia, materialización.
7.3 Gobernanza: revisión mensual, dueño del dato, playbook de alertas, validación de costos.
7.4 Investigación futura: datos reales, diseño causal, mantenimiento predictivo.
7.5 Hoja de ruta 0–30/31–90/91–180 días.

**Tabla T20.** Acciones priorizadas e impacto hipotético.

### 8. Referencias (2 páginas)

APA 7, sangría francesa, 28 fuentes. Ver `REFERENCIAS.md`.

## 4. Anexos

| Anexo | Contenido | Págs. |
|---|---|---:|
| A | Texto completo del caso original | 1 |
| B | Diccionario de datos seleccionado | 2 |
| C | Matriz de aceptación del caso (f.1–f.5) | 1 |
| D | Capturas completas del tablero (D1–D8) | 6 |
| E | Guía de reproducción | 1 |
| F | Glosario y abreviaturas | 1 |
| G | Tabla maestra de cifras y trazabilidad | 1 |

El **guion de exposición y preguntas previsibles** se entrega aparte en
`MetalNova_Guion_Defensa_v0.1.docx` (2 páginas), para no recargar el informe.

## 5. Correspondencia con la rúbrica

| Criterio | Peso | Cómo se cubre | Evidencia |
|---|---:|---|---|
| Presentación personal y seguridad | 10 % | No es criterio del documento; el guion aparte da tiempos y mensajes clave | Guion de defensa |
| Coherencia y contenido | 10 % | Estructura única, figuras/tablas, mensajes clave | Todo el informe |
| Disertación del trabajo | 20 % | Marco teórico, decisiones tecnológicas y discusión | 2, 3.5, 5 |
| Verificación de objetivos | 20 % | Objetivos → resultados → evidencia | 6.2, T1, Anexo C |
| Aplicación práctica | 20 % | Prototipo, resultados, validación y reproducción | 3, 4, Anexo E |
| Respuestas a preguntas | 20 % | Preguntas previsibles y respuestas breves | Guion de defensa |

## 6. Convenciones de redacción

- Voz impersonal: “se diseñó”, “se observó”, “se concluye”.
- Decimales con coma y miles con punto en el texto; en tablas, coma decimal.
- Porcentajes con dos decimales; minutos y unidades con separador de miles.
- Definir siglas en el primer uso: OEE, A/P/Q, MTBF, MTTR, FPY, MES, CMMS, SCADA, IoT, BI, DAX.
- Distinguir siempre: **observado**, **hipotético** y **cifras del caso**.
- No afirmar causalidad; usar “asociación”, “coincidencia”, “los datos muestran”.
- Cada figura/tabla con nota y fecha de corte; la advertencia de datos sintéticos se concentra en 3.3.
- Citas APA 7 en texto; referencias con sangría francesa.
- No copiar párrafos del README ni de los `specs/`; sintetizar y citar.

## 7. Riesgos y controles

| Riesgo | Control |
|---|---|
| Cifras inconsistentes | Tabla maestra única; corte 2026-10-24 |
| Informe demasiado técnico | Explicar cada KPI y cada decisión en lenguaje académico |
| Afirmar causalidad | Revisión específica de §5.3 y conclusiones |
| Presentar ahorros como reales | Etiquetas “hipotético” y supuestos declarados |
| Exceder 55 páginas | Priorizar cuerpo; anexos comprimidos |
| TOC desactualizado | Actualizar campos en Word antes de entregar |
| Similitud con documentos del proyecto | Redacción original y citas a la documentación |

## 8. Estado de la entrega final

- [x] Estructura final aprobada.
- [x] Tabla maestra de cifras (corte 2026-10-24).
- [x] Portada y datos académicos (portada del usuario preservada).
- [x] Resumen y abstract.
- [x] Introducción completa.
- [x] Secciones 2–7 redactadas.
- [x] Figuras F1–F10.
- [x] Tablas T1–T20.
- [x] Referencias completas (32 entradas APA 7).
- [x] Anexos A–G.
- [x] Anexo D con las cuatro capturas principales (D1–D4).
- [x] Guion de defensa en documento aparte.
- [x] DOCX final: 57 páginas, 10.242 palabras, TOC y listas actualizados.
- [x] Títulos y TOC en Times New Roman 12; tablas/figuras en Arial 8.
- [x] Menciones a datos sintéticos solo en metodología.
- [x] Capturas D5–D8 insertadas en el Anexo D.
- [x] Paginación definitiva de las listas de tablas/figuras.
- [ ] Revisión final de la bibliografía contra los ejemplares de la asignatura.

**Archivos generados:**

- `docs/informe/MetalNova_Informe_Caso_Practico_v0.3_final.docx`
- `docs/informe/MetalNova_Guion_Defensa_v0.1.docx`
