# Verificación del proyecto — Bloques 1 a 6, y solapes de paradas

> **Todos los datos son sintéticos.** Esta carpeta contiene la verificación
> reproducible del prototipo, con consultas ejecutadas contra la base local
> `metalinova` el **2026-10-24**. No sustituye a `specs/` (fuente de verdad
> normativa); la complementa para el documento final.

## Documentos

| Documento | Contenido | Estado |
|---|---|---|
| [`bloque1-negocio-modelo.md`](./bloque1-negocio-modelo.md) | Comprensión del negocio, volumen, jerarquías, microparadas, fuentes y latencia | Verificado |
| [`bloque2-modelado-dimensional.md`](./bloque2-modelado-dimensional.md) | Hechos, dimensiones, jerarquías, transformaciones, unidades y datos IoT | Verificado |
| [`pregunta-principal-business-understanding.md`](./pregunta-principal-business-understanding.md) | Respuesta formal a la pregunta principal: activos, turnos, productos, causas e impacto | Verificado |
| [`solapes-paradas.md`](./solapes-paradas.md) | Implementación y verificación de la consolidación de paradas solapadas | Verificado |
| [`bloque3-aplicativo-bi.md`](./bloque3-aplicativo-bi.md) | Páginas, interactividad, visualización operativa y alerta de máquina crítica | Verificado |
| [`bloque4-kpi-obligatorios.md`](./bloque4-kpi-obligatorios.md) | Fórmulas de los 10 KPI obligatorios y valores observados | Verificado |
| [`bloque5-analisis-descubrimiento.md`](./bloque5-analisis-descubrimiento.md) | Loss Tree, confiabilidad, calidad descriptiva y priorización | Verificado |
| [`bloque6-producto-criterios.md`](./bloque6-producto-criterios.md) | Producto esperado y matriz de aceptación f.1–f.5 | Verificado |

## Resumen de cumplimiento

| Tema | Veredicto |
|---|---|
| Volumen y alcance (3 plantas, 52 máquinas, 180 días, ≥ 200.000 eventos) | **Cumple** |
| Modelo dimensional (4 hechos + dimensiones conformadas) | **Cumple** |
| Jerarquías y drill-down sin duplicar medidas | **Cumple con matiz** (navegación por slicers/matriz; no un visual único de 4 niveles) |
| Transformaciones y normalización de unidades | **Cumple** |
| Microparadas vs fallas | **Cumple** (regla G6) |
| Datos IoT: duplicados, desordenados y timestamps | **Cumple** |
| Lecturas faltantes | **Cumple con matiz** (se declara el hueco; el estado `unknown` no se emite) |
| Fuente de verdad de inicio/fin de parada | **Cumple** (IoT/SCADA) |
| Solapes de paradas | **Cumple con matiz** (`v_parada_consolidada`; OEE sigue usando `fact_produccion`) |
| Fuentes mínimas | **Parcial** (ERP no etiquetado como fuente) |
| Latencia < 10 min | **Cumple** |
| Pregunta principal de Business Understanding | **Cumple en este paquete** |
| 4 páginas BI (Executive, OEE & Loss Tree, Maintenance, Quality/Energy) | **Cumple** |
| Filtros por planta, línea, máquina, producto y turno | **Cumple** (6 slicers sincronizados) |
| Drill-through a máquina, tooltip y navegación a causa | **Cumple** |
| Serie temporal con umbral, Pareto y matriz condicional | **Cumple con matiz** (Pareto sin línea acumulada) |
| Alerta de máquina crítica accionable | **Cumple con matiz** (responsable/KPI en la vista, no en la tabla) |
| 10 KPI obligatorios (OEE, A, P, Q, MTBF, MTTR, downtime, scrap, FPY, energía) | **Cumple con matiz** (downtime % sin tarjeta propia; FPY literal vs. FPY clásico) |
| Loss Tree y descomposición por activo/turno/producto | **Cumple** |
| Confiabilidad de corto plazo (microparadas/fallas cortas) | **Cumple** |
| Calidad descriptiva (scrap vs producto/turno/condición) | **Cumple con matiz** (cambios de producto y temperatura ad-hoc) |
| Ranking de intervenciones por impacto y criticidad | **Cumple** |
| Criterios mínimos f.1–f.5 | **Cumple con matices documentados** (ver `bloque6-producto-criterios.md`) |

## Cómo usar estos documentos

1. Leer primero `bloque1-negocio-modelo.md` para el contexto y el volumen.
2. Usar `bloque2-modelado-dimensional.md` para el detalle técnico del modelo.
3. Usar `pregunta-principal-business-understanding.md` para la respuesta de
   negocio y el guion de exposición.
4. Usar `bloque3-aplicativo-bi.md` para páginas, interactividad, visualización y
   alerta.
5. Usar `bloque4-kpi-obligatorios.md` para las fórmulas y valores de los KPI.
6. Usar `bloque5-analisis-descubrimiento.md` para el análisis y la priorización.
7. Usar `bloque6-producto-criterios.md` para la matriz final de aceptación.
8. Cada documento incluye comandos de reproducción. Ejecutarlos desde la raíz del
   repositorio, con la base `metalinova` levantada:

```powershell
docker compose up -d
docker compose ps
```

## Convenciones

- **Cumple:** la evidencia observada satisface el punto.
- **Cumple con matiz:** satisface el fondo, pero la implementación difiere de la
  forma esperada (por ejemplo, navegación por slicers en vez de un visual
  jerárquico único).
- **Parcial:** hay una parte implementada y una brecha declarada; no se presenta
  como resuelto.
- **No cumple:** no hay evidencia; se documenta como brecha.

## Notas

- Las cifras pueden variar si se ejecuta nueva ingesta simulada.
- La prueba de solapes se ejecutó dentro de `BEGIN … ROLLBACK`; no dejó datos
  persistidos. Detalle en [`solapes-paradas.md`](./solapes-paradas.md).
- La regresión de KPI quedó en 49/49 con `validate_data.py`.
- Las capturas visuales del informe siguen en `docs/capturas/`.
