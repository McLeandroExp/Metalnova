# CONSTITUCIÓN DEL PROYECTO — MetalNova Smart Factory BI

Versión: 2.0 (deriva del Documento Maestro v1.0 + enmiendas G1–G6)
Fecha: 18 de octubre de 2026
Estado: **normativo**. Este documento es la fuente de verdad del proyecto.

---

## 0. Identidad

Prototipo académico de Business Intelligence, ejecutable y demostrable de forma local, que
integra datos industriales **sintéticos** de una fábrica de componentes automotrices para medir
OEE de forma consistente, localizar pérdidas de disponibilidad/rendimiento/calidad y priorizar
acciones de mantenimiento y producción.

- 3 plantas · 6 líneas · 52 máquinas críticas.
- Histórico: 180 días.
- Ingesta continua simulada con objetivo de latencia < 10 minutos.
- Stack: PostgreSQL en Docker + Python + Power BI Desktop en Windows.
- Sin nube. La demostración no depende de internet.

---

## 1. Jerarquía de autoridad

`specs/CONSTITUTION.md` > `specs/00N-*/spec.md` > `docs/*.md` > `docs/reference/*`

`docs/reference/` contiene los insumos académicos originales. **No es normativo.** Sus
divergencias con esta constitución están enumeradas en la sección 4 (Supersesiones).

---

## 2. Definición de "evento"

Un **evento de origen** es un registro unitario, con clave estable, procedente de una fuente
simulada (IoT/SCADA, MES, CMMS, ERP, calidad, turnos). Los eventos se clasifican en:

| Tipo | Fuente | Grano |
|---|---|---|
| Transición de estado (arranque/parada) | IoT/SCADA | por transición |
| Lectura de proceso (temperatura, energía) | IoT/SCADA | por intervalo muestreado |
| Orden de producción y conteos | MES | por orden + máquina + turno |
| Parada (episodio) | IoT derivado | por episodio |
| Intervención de mantenimiento | CMMS | por orden de trabajo |
| Inspección / lote | Calidad | por inspección |
| Causa raíz | Catálogo | referencia |

**Regla de conteo (evita el error de volumen):** el simulador emite **eventos por transición**,
no *snapshots* periódicos por máquina. Un muestreo de 1 evento/máquina/minuto daría
52 × 1440 × 180 ≈ 13,4 M filas, inviable en 8 GB. Con ~32 eventos/máquina/día se alcanza el
objetivo de ~300 000 filas.

Los recuentos se informan **por tabla**, y el término "evento" se usa siempre con la definición
anterior. Nunca se equipara "número de eventos" con "filas totales del modelo".

---

## 3. Reglas de trabajo

1. Inspeccionar el directorio y resumir el estado antes de cambiar archivos.
2. No sobrescribir ni eliminar archivos del usuario sin confirmación.
3. Trabajar en etapas pequeñas y verificables. Tras cada etapa comunicar: qué cambió, comandos
   ejecutados, resultados obtenidos, qué queda pendiente y cómo comprobarlo.
4. No afirmar que una prueba pasó sin haberla ejecutado y observado su resultado.
5. No inventar credenciales, resultados de rendimiento ni métricas de fábrica.
6. Usar datos sintéticos, identificados como tales.
7. Si una decisión cambia la arquitectura, exponer ventajas/inconvenientes antes de fijarla.
8. Mantener secretos fuera del control de versiones y fuera de los logs.
9. No dependender de cuentas de nube ni de internet durante la demostración.
10. Priorizar sencillez y mantenibilidad en un equipo Windows 11 de 8 GB.
11. Comprobar disponibilidad de herramientas antes de usarlas; no instalar nada global sin autorización.
12. **No** construir aplicación web ni API REST. La v1 se apoya en PostgreSQL, Python y Power BI.
13. Usar scripts SQL idempotentes. No depender de que `docker-entrypoint-initdb.d` se re-ejecute.
14. Documentar decisiones en `docs/DECISIONS.md` y lo operativo en `README.md`.
15. No avanzar de etapa si falla una prueba esencial sin informar el bloqueo y proponer solución.

---

## 4. Supersesiones respecto al Documento Maestro

Toda divergencia con `docs/reference/MetalNova_Documento_Maestro_Agentes.md` queda fijada aquí.

| Cláusula del Documento Maestro | Decisión vigente (enmienda) | Motivo |
|---|---|---|
| §6 dimensiones compartidas (sin línea ni familia) | Se añaden `dim_linea` (Planta→Línea→Máquina) y `dim_familia` (Familia→Producto) | **G1** — el caso exige ambas jerarquías y drill-down |
| §2/§7 alertas genéricas, sin señal de temperatura | Se define señal `temperatura_c` en el evento IoT y una **regla de excepción multicriterio** (sección 8) | **G2** — el caso exige regla accionable con temperatura |
| §7 FPY "solo si los datos lo permiten" | FPY pasa a ser **KPI obligatorio**. `fact_calidad` incorpora `es_retrabajo` | **G3** — el caso lo lista como KPI obligatorio |
| §7 "energía por unidad producida" | Definición adoptada: **Energía por Unidad Buena = kWh / unidades buenas** | **G4** — el caso dice explícitamente "por unidad buena" |
| §6/§8 IoT (solo duplicados e idempotencia) | Se añaden reglas para eventos **desordenados, faltantes, fuera de rango** y **tabla de cuarentena** + precedencia de fuentes (sección 7) | **G5** — criterio de aceptación f.4 del caso |
| §7 microparadas sin criterio numérico | Umbral configurable `microparada_min = 5` y criterio falla/microparada (sección 7) | **G6** — el caso exige distinguir microparadas de fallas |
| §4 propuesta de carpetas | Se añade `specs/` y `AGENTS.md`; la raíz del proyecto es el repositorio actual | Congruencia SDD y anti-confusión entre sesiones |
| §3 objetivo 200 000 eventos / 90 días | Se mantiene el **mínimo** del caso y se fija objetivo de diseño 300 000 / 180 días | El caso es un mínimo; se supera con margen |

Todo lo demás del Documento Maestro permanece vigente y se considera incorporado por referencia.

---

## 5. Modelo de datos normativo

### 5.1 Tablas de hechos

| Tabla | Grano | Notas |
|---|---|---|
| `fact_produccion` | 1 fila por orden + máquina + turno (+ segmento si aplica) | conteos, tiempos, ciclo ideal |
| `fact_parada` | 1 fila por episodio de parada | inicio, fin, duración, causa, plan/no plan |
| `fact_mantenimiento` | 1 fila por orden/intervención | fechas, tipo, técnico, duración |
| `fact_calidad` | 1 fila por inspección/lote | inspeccionadas, buenas, defectuosas, retrabajo |
| `fact_evento` | 1 fila por evento crudo de origen | aterrizaje, `source_event_id` único |
| `fact_evento_rechazado` | 1 fila por evento descartado | motivo y payload original |

### 5.2 Dimensiones conformadas

`dim_planta`, `dim_linea`, `dim_maquina` (jerarquía Planta→Línea→Máquina)
`dim_familia`, `dim_producto` (jerarquía Familia→Producto)
`dim_turno`, `dim_causa`, `dim_tiempo`, `dim_tecnico`
`dim_orden` (opcional, si mejora claridad)

### 5.3 Jerarquías y drill-down

- `dim_planta → dim_linea → dim_maquina`
- `dim_familia → dim_producto`

El drill-down se resuelve **sobre dimensiones**, nunca duplicando medidas en tablas de hechos.
Las medidas se definen una sola vez y se filtran por las dimensiones conformadas, de modo que
agregar "por máquina" o "por producto" no altera la definición del KPI.

### 5.4 Reglas de integridad

- Claves primarias y foráneas declaradas; grano documentado por tabla.
- No mezclar eventos crudos con agregados sin identificarlos.
- Evitar que los joins entre hechos multipliquen cantidades o duraciones.
- Timestamps con zona (`timestamptz`); distinguir `event_time` de `ingested_at`.
- Restricciones: cantidades y duraciones no negativas; `fin >= inicio`.
- Prohibido el promedio simple de porcentajes (OEE, disponibilidad): siempre ponderado por
  su denominador.

---

## 6. Definiciones de KPI

| KPI | Fórmula | Notas |
|---|---|---|
| OEE | Disponibilidad × Rendimiento × Calidad | ponderado, nunca promedio de porcentajes |
| Disponibilidad | runtime / tiempo de producción planificado | excluye descansos y paradas planificadas |
| Rendimiento | (ideal cycle time × total count) / runtime | ciclo ideal por producto |
| Calidad | good count / total count | |
| MTBF | tiempo operativo / número de fallas | fallas = paradas no planificadas según sección 7 |
| MTTR | tiempo total de reparación / número de reparaciones | alcance = intervenciones CMMS cerradas |
| Downtime no planificado | minutos no planificados / tiempo planificado | |
| Scrap Rate | unidades rechazadas / unidades producidas | definición única |
| FPY | unidades sin retrabajo / unidades procesadas | obligatorio (G3) |
| Energía por Unidad Buena | kWh consumidos / unidades buenas | (G4) |

**Indicadores de apoyo obligatorios** (para el análisis de confiabilidad):

- conteo de **microparadas** (< umbral) y su duración acumulada;
- MTBF de corto plazo / frecuencia de fallas cortas, para detectar equipos con muchas fallas
  breves que no destacan en el promedio de downtime.

**Casos borde obligatorios:** máquina sin producción, turno con cero fallas, división por cero,
periodos incompletos. Deben tratarse de forma explícita y documentada.

---

## 7. Reglas de datos IoT y fuente de verdad

### 7.1 Limpieza

| Problema | Regla |
|---|---|
| Duplicados | dedupe por `(source_system, source_event_id)` con `ON CONFLICT` |
| Desordenados | ventana de reordenamiento de N minutos; *upsert* por `event_time`; recálculo del hecho |
| Lecturas faltantes | último estado conocido (*carry-forward*) con flag de calidad; gap máximo 15 min; más allá ⇒ estado `unknown` |
| Timestamps fuera de rango | rechazo a `fact_evento_rechazado` con motivo; rango válido `[inicio_histórico − 1 d, ahora + 5 min]` |

Nunca se descarta un evento en silencio: o se corrige con trazabilidad o queda en cuarentena.

### 7.2 Fuente de verdad

| Dato | Fuente de verdad |
|---|---|
| Inicio/fin de una parada | transición de estado IoT/SCADA |
| Confirmación de reparación | CMMS (no define la parada, la explica) |
| Conteos de producción | MES |
| Energía y temperatura | IoT/SCADA |
| Unidades buenas/defectuosas/retrabajo | Calidad / MES |

### 7.3 Falla frente a microparada (G6)

Con umbral configurable `microparada_min = 5`:

- parada con duración `< microparada_min` **y sin** orden CMMS asociada ⇒ **microparada**;
- parada con orden CMMS **o** duración `>= microparada_min` ⇒ **falla**.

El criterio se aplica en una vista/consulta única y se documenta en `docs/DATA_DICTIONARY.md`.

---

## 8. Regla de excepción de máquina crítica (G2)

Ventana de evaluación: turno actual (con opción de 2 turnos consecutivos). Se emite alerta si se
cumple **al menos una** condición; severidad **crítica** si se cumplen **dos o más**:

| Condición | Umbral | Acción y responsable | Por qué es accionable |
|---|---|---|---|
| OEE bajo | < 55 % | Revisar pérdida dominante con el ciclo PDCA — Producción | Indica caída sostenida de valor |
| MTBF bajo | < 20 h | Inspección preventiva anticipada — Mantenimiento | Falla recurrente inminente |
| Temperatura alta | > 85 °C durante 15 min | Verificar refrigeración/lubricación — Mantenimiento | Degradación térmica medible |
| Downtime acumulado | > 120 min/turno | Reasignar capacidad / intervenir — Producción | Pérdida de throughput inmediata |

Cada alerta enlaza a su KPI de seguimiento y a un responsable. La regla se implementa en una
vista SQL para que sea verificable e idéntica entre Python y Power BI.

---

## 9. Arquitectura y stack

```text
Generador Python ─▶ CSV/Parquet (data/) ─▶ Carga por lotes ─▶ PostgreSQL
                                                                   ▲
Simulador Python ──────────────────────────────────────────────────┘
                                                                   │
                                              Vistas estables ─────┴──▶ Power BI Desktop
```

- Docker Compose orquesta `db` (PostgreSQL) e `ingestor` (Python).
- Power BI Desktop se ejecuta en Windows y se conecta al puerto local publicado.
- Modo de conexión **pendiente de prueba**: empezar con DirectQuery sobre vistas; cambiar a
  Import si el rendimiento o la fiabilidad de la demo no cumplen. La decisión y sus mediciones
  se registran en `docs/DECISIONS.md` y en `specs/006-*/verification.md`.

---

## 10. Seguridad operativa Docker

- Imágenes con versión fija (nunca `latest` sin control).
- Variables de entorno para usuario, base y contraseña; `.env.example` sin secretos; `.env` ignorado.
- Volumen nombrado para los datos de PostgreSQL; healthcheck y `depends_on` con servicio saludable.
- Publicar el puerto **solo en loopback** (`127.0.0.1`).
- Prohibido `docker compose down -v` como comando rutinario.
- Documentar backup/restauración (`pg_dump` / `pg_restore`).
- Los scripts de `docker-entrypoint-initdb.d` solo corren con un directorio de datos vacío; los
  cambios posteriores se aplican con scripts/migraciones explícitas.

---

## 11. Volumen y rendimiento

- Mínimo del caso: 200 000 eventos de origen en ≥ 90 días.
- Objetivo de diseño: 180 días y ~300 000 eventos, ajustado al rendimiento real de 8 GB.
- Carga por lotes; no cargar el histórico completo en memoria.
- Registrar tamaño de tablas, duración de carga y memoria aproximada cuando sea posible.

---

## 12. No objetivos

- Sin microservicios, Kafka ni MQTT en la v1.
- Sin API REST ni aplicación web.
- Sin requisito de nube ni publicación en Power BI Service.
- Sin modo híbrido complejo antes de tener una versión simple funcionando.
- No forzar los datos sintéticos para que reproduzcan exactamente las cifras del caso
  (78 % → 66 %, USD 540 000) salvo que se diseñe un escenario de calibración documentado.

---

## 13. Condiciones de finalización

1. La infraestructura arranca con Docker Compose; PostgreSQL conserva datos entre reinicios.
2. Existen 180 días de datos sintéticos válidos y se alcanza el volumen mínimo documentado.
3. La ingesta simulada inserta eventos nuevos sin duplicados.
4. Los KPI se validan de forma independiente.
5. Power BI contiene las 4 páginas solicitadas con 9 KPIs y navegación máquina→detalle.
6. Se elige DirectQuery o Import mediante pruebas documentadas; se mide y explica la latencia real.
7. La demo se repite siguiendo un runbook; el plan de mejora muestra evidencias y supuestos.
8. `README.md` y la documentación permiten que otra persona ejecute el proyecto.

---

## 14. Proceso SDD

- Un incremento = una carpeta `specs/00N-*/` con `spec.md`, `plan.md`, `tasks.md`, `verification.md`.
- Los requisitos se numeran `FR-xxx`; los criterios de aceptación, `AC-xxx`; las tareas, `T-xxx`.
- Toda tarea pasa por `pendiente → en curso → hecha`. Una tarea `hecha` exige evidencia en
  `verification.md` (comando, salida, fecha).
- El avance entre incrementos respeta el grafo de `specs/README.md`.
- Al cerrar un incremento: actualizar su estado en `specs/README.md` y crear el commit.
