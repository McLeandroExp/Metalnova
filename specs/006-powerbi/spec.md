# Incremento 006 — Informe Power BI (4 páginas)

Estado: en curso · Depende de: 004, 005 · Habilita: 007

## Contexto

Construye la capa de visualización: 4 páginas, 9 KPIs, filtros consistentes, drill-through,
tooltips y alertas. Enfoque híbrido: el modelo semántico (TMDL/medidas DAX) se genera por
código; los visuales se montan en Power BI Desktop siguiendo una guía verificable.

El histórico previo era homogéneo entre plantas (rango 0,05 pp), así que el 006 incluye una
calibración declarada (FR-615): factores por planta, perfiles persistentes de máquina y outliers.
Sigue siendo sintético y reproducible con semilla 42; no se presenta como telemetría real.

## Requisitos funcionales

| ID | Requisito |
|---|---|
| FR-601 | Conexión de Power BI Desktop a PostgreSQL local; decisión DirectQuery vs Import **medida y documentada**. |
| FR-602 | Página **Executive Plant Performance**: KPI de planta, tendencias, comparación entre plantas, alertas. |
| FR-603 | Página **OEE & Loss Tree**: OEE, A/P/Q, Pareto de pérdidas y matriz máquina-turno con formato condicional. |
| FR-604 | Página **Maintenance Reliability**: paradas, MTBF, MTTR, recurrencia de averías. |
| FR-605 | Página **Quality & Energy**: scrap, defectos, FPY, consumo energético y energía por unidad buena. |
| FR-606 | Filtros por planta, línea, máquina, producto y turno, coherentes entre páginas. |
| FR-607 | Drill-through al historial de una máquina. |
| FR-608 | Tooltips con última intervención, MTBF y MTTR. |
| FR-609 | Al menos una serie temporal con líneas de umbral. |
| FR-610 | Pareto de downtime. |
| FR-611 | Matriz máquina-turno con formato condicional. |
| FR-612 | Navegación desde una pérdida de OEE hacia su causa. |
| FR-613 | Visual de alerta de máquina crítica basado en la vista `v_alerta_maquina_critica`. |
| FR-614 | Modelo semántico en `powerbi/` (proyecto `.pbip` + TMDL) y medidas DAX documentadas. |
| FR-615 | Escenario `calibracion` reproducible: factores por planta y perfiles persistentes por máquina, para que el informe muestre diferencias visibles y outliers sin abandonar la semilla 42. |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-601 | Existen las 4 páginas y al menos 9 KPIs operativos. |
| AC-602 | Los KPI del informe coinciden con los de las vistas SQL. |
| AC-603 | Los filtros no se rompen entre páginas ni producen visuales vacíos inesperados. |
| AC-604 | Drill-through navega a una página de detalle de máquina. |
| AC-605 | No hay visuales críticos rotos. |
| AC-606 | El modo de conexión elegido está justificado con mediciones reales. |
| AC-607 | Se guarda `powerbi/MetalNova.pbix` (o `.pbip`) en el repositorio. |
| AC-608 | El escenario calibrado apunta a OEE ≈78 → 66 %, muestra 5–10 pp de dispersión entre plantas y al menos una máquina outlier <55 %; `validate_data.py` sigue en 49/49. |

## Fuera de alcance

Publicación en Power BI Service; actualización automática programada.

## Dependencias

004 (datos nuevos), 005 (vistas KPI).

## Notas de viabilidad

Power BI Desktop es una aplicación GUI: el agente no hace clic en ella. La parte de modelo y DAX
se genera por código; la disposición de visuales se guía paso a paso y se verifica en conjunto.
