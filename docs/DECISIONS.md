# Registro de decisiones — MetalNova Smart Factory BI

Formato: decisión, alternativas consideradas, motivo, consecuencias y estado.

---

## D-001 · Arquitectura SDD con specs versionadas

- **Decisión:** organizar el trabajo en `specs/00N-*/` con `spec.md`, `plan.md`, `tasks.md` y
  `verification.md`, y mantener `specs/CONSTITUTION.md` como fuente de verdad.
- **Alternativas:** trabajar solo con el Documento Maestro; usar el doc maestro como spec viva.
- **Motivo:** evitar confusión entre sesiones y garantizar trazabilidad requisito→evidencia.
- **Consecuencias:** los documentos originales pasan a `docs/reference/` como insumos no normativos.
- **Estado:** aceptada.

## D-002 · Conservar los insumos originales sin editar ni eliminar

- **Decisión:** mover `caso_practico.txt` y `MetalNova_Documento_Maestro_Agentes.md` a
  `docs/reference/` intactos.
- **Alternativas:** editarlos a v1.1; eliminarlos tras extraer su contenido.
- **Motivo:** preservar trazabilidad académica; evitar dos fuentes de verdad en conflicto.
- **Consecuencias:** las divergencias se listan en la sección Supersesiones de la Constitución.
- **Estado:** aceptada.

## D-003 · PostgreSQL 16.4-alpine en Docker con puerto en loopback

- **Decisión:** imagen `postgres:16.4-alpine`, publicación `127.0.0.1:5432`, volumen nombrado.
- **Alternativas:** `latest`; exponer a la red; instalar PostgreSQL nativo.
- **Motivo:** reproducibilidad, superficie de exposición mínima y ajuste a 8 GB.
- **Consecuencias:** Power BI Desktop se conecta a `127.0.0.1:5432`.
- **Estado:** aceptada.

## D-004 · Enmiendas G1–G6

- **Decisión:** aplicar las enmiendas G1 a G6 (jerarquías línea/familia, alerta con temperatura,
  FPY obligatorio con retrabajo, energía por unidad buena, reglas IoT completas, umbral de microparada).
- **Motivo:** cerrar brechas entre el Documento Maestro y el enunciado del caso.
- **Consecuencias:** la Constitución prevalece sobre el Documento Maestro donde difieran.
- **Estado:** aceptada.

## D-005 · Modo de conexión Power BI (DirectQuery vs Import)

- **Decisión:** pendiente de prueba en el incremento 006.
- **Criterios:** ver Constitución §9.
- **Estado:** pendiente.

## D-006 · pgAdmin como cliente de base de datos

- **Decisión:** incluir `dpage/pgadmin4:9.18` en el Compose, accesible en `http://127.0.0.1:5050`,
  con volumen propio `metalinova_pgadmin` y servidor PostgreSQL pre-registrado.
- **Alternativas:** no incluirlo y usar solo `psql` (recomendación original del Documento Maestro
  por la RAM); instalar un cliente nativo en Windows.
- **Motivo:** el propietario quiere verificar visualmente que existan los elementos de la base
  (servidor, base de datos, tablas y vistas).
- **Consecuencias:** +200–300 MB de RAM; un puerto local más; credenciales de pgAdmin separadas de
  las de PostgreSQL en `.env`. No es dependencia del pipeline: si se detiene, nada más se rompe.
- **Detalles:** modo servidor (login obligatorio); email `admin@metalinova.com` porque el validador
  rechaza dominios `.local`; el volumen `metalinova_pgadmin` solo guarda configuración.
- **Estado:** aceptada.

## D-007 · Catálogo de referencia sembrado en el incremento 002

- **Decisión:** el incremento 002 siembra plantas, líneas, 52 máquinas, familias, productos, turnos,
  causas, técnicos y 1095 días de calendario. El 003 genera los hechos.
- **Alternativas:** sembrar todo en 003 junto con la generación de eventos.
- **Motivo:** el esquema queda verificable de inmediato en pgAdmin y las pruebas de integridad
  tienen datos de referencia reales.
- **Consecuencias:** los catálogos son estáticos y reproducibles; el 003 puede ampliarlos.
- **Estado:** aceptada.

## D-008 · Constraints inline y `03_comentarios.sql`

- **Decisión:** PK, FK, UNIQUE y CHECK se declaran dentro de `CREATE TABLE IF NOT EXISTS`. El
  archivo previsto `03_constraints.sql` pasa a `03_comentarios.sql` (documentación del grano).
- **Alternativas:** `ALTER TABLE ... ADD CONSTRAINT` con bloques `DO` para idempotencia.
- **Motivo:** la creación es atómica, la re-ejecución es trivialmente segura y se evita el
  *boilerplate* de comprobar `pg_constraint`.
- **Consecuencias:** los cambios futuros de constraints requerirán una migración explícita.
- **Estado:** aceptada.

## D-009 · FK compuesta orden–producto

- **Decisión:** `fact_produccion` referencia `dim_orden (id_orden, id_producto)`.
- **Motivo:** impide que un hecho registre un producto distinto al de su orden.
- **Consecuencias:** `dim_orden` declara `UNIQUE (id_orden, id_producto)`.
- **Estado:** aceptada.

## D-010 · Histórico en CSV y generación en streaming

- **Decisión:** exportar el histórico a CSV en `data/raw/` y escribirlo en streaming, sin mantener
  las filas en memoria. Se descarta Parquet en la v1.
- **Alternativas:** Parquet (requiere `pyarrow`, +~100 MB de imagen); cargar directo a PostgreSQL
  sin archivos intermedios.
- **Motivo:** CSV es suficiente para el volumen (≈99 MB), no añade dependencias y permite
  inspección manual; el streaming mantiene el pico de memoria en ~43 MB.
- **Consecuencias:** el cargador usa `COPY` CSV a una tabla temporal y luego
  `INSERT … ON CONFLICT DO NOTHING`.
- **Estado:** aceptada.

## D-011 · `run_id` determinista y guardia contra mezcla de ejecuciones

- **Decisión:** `run_id = hist-<hash>` donde el hash cubre versión del generador, semilla, días,
  fechas, escenario, intensidad, plantas y máquinas. La carga exige `--reset` si la base contiene
  otro `run_id`.
- **Alternativas:** borrar y recargar siempre; usar un `run_id` con marca de tiempo.
- **Motivo:** la misma semilla produce el mismo `run_id` y una recarga idempotente; una ejecución
  distinta no se mezcla en silencio con la anterior.
- **Consecuencias:** `--reset` vacía hechos y `dim_orden` (nunca el catálogo ni el volumen).
- **Estado:** aceptada.

## D-012 · Escenario por defecto `degradado`

- **Decisión:** el generador usa `degradado` por defecto; `base` queda disponible por parámetro.
- **Motivo:** el caso de estudio gira en torno a la caída de OEE y la priorización de pérdidas.
- **Consecuencias:** 180 días degradados producen OEE 0,91 → 0,78; el escenario base, 0,92 → 0,89.
  Las cifras no se fuerzan a las del enunciado (Constitución §12).
- **Estado:** aceptada.

## D-013 · Las vistas KPI son el contrato único y la agregación es ponderada

- **Decisión:** exponer los KPI en vistas SQL (`sql/views/02..08`) y usarlas como contrato para
  Power BI, Python y validación. Los porcentajes se agregan sumando numeradores y denominadores;
  nunca se promedian porcentajes.
- **Alternativas:** calcular los KPI en DAX directamente desde los hechos; crear una tabla ancha
  materializada por cada grano.
- **Motivo:** una sola definición verificable, sin divergencia entre SQL, Python y DAX; el OEE de
  una planta debe ponderar por tiempo/unidades, no promediar máquinas.
- **Consecuencias:** cada vista de grano superior recalcula A/P/Q con `SUM/SUM`; la validación
  independiente compara los numeradores, los denominadores y el resultado. Cambiar una fórmula
  exige cambiar la vista, el diccionario y la prueba.
- **Estado:** aceptada.

## D-014 · División por cero: `NULL` intencional, nunca `NaN`

- **Decisión:** toda razón con denominador cero devuelve `NULL`; no se usa `0` como sustituto porque
  ocultaría la ausencia de base de cálculo. La alerta trata `NULL` como condición no cumplida.
- **Alternativas:** devolver `0`; excluir la fila; usar un valor centinela.
- **Motivo:** `NULL` distingue “no definido” de un cero real (por ejemplo, MTBF de una máquina sin
  fallas o FPY sin inspecciones) y evita `NaN` en Power BI. El caso borde queda documentado y
  probado con una transacción revertida en `validate_data.py`.
- **Consecuencias:** los visuales muestran celdas en blanco para métricas no definidas; el informe
  debe usar `COALESCE`/`DIVIDE` solo cuando la regla de negocio lo justifique.
- **Estado:** aceptada.

## D-015 · Umbrales de falla corta, temperatura y ventana de alerta

- **Decisión:** falla corta = falla con duración < 30 min. Temperatura alta = lectura > 85 °C; como
  el histórico muestrea cada 15 min, se exigen al menos dos lecturas altas en el turno para
  representar 15 min. La alerta se evalúa por máquina × turno × fecha; `es_ultimo_turno_maquina`
  permite mostrar el turno actual de cada máquina.
- **Alternativas:** usar el mismo umbral de microparada (5 min); evaluar solo el último día global;
  usar un promedio diario de temperatura.
- **Motivo:** la Constitución §8 fija 85 °C/15 min y la ventana por turno, pero no fija el umbral de
  “falla corta” ni el muestreo. Estos valores quedan centralizados en `v_kpi_parametros` y
  documentados para que sean auditables.
- **Consecuencias:** los umbrales son visibles en la vista de parámetros; cambiarlos exige revisar
  la vista, el diccionario y la validación. La temperatura es una aproximación por muestreo, no una
  serie continua.
- **Estado:** aceptada.

## D-016 · Ingesta simulada determinista por slot e idempotente

- **Decisión:** alinear cada ciclo a una rejilla temporal (`slot = floor(t / intervalo)`) y derivar
  las decisiones de `SHA-256(seed, máquina, slot)`. Cada evento recibe un `source_event_id` estable
  y la inserción usa `ON CONFLICT DO NOTHING`. `--at` fija el reloj para pruebas reproducibles.
- **Alternativas:** UUID aleatorio por evento con deduplicación por contenido; mantener el estado
  solo en memoria; borrar y recargar la tabla en cada arranque.
- **Motivo:** reiniciar o reintentar un lote no debe duplicar filas, y una prueba debe poder repetir
  exactamente el mismo ciclo. El estado en memoria no sobrevive a un reinicio.
- **Consecuencias:** misma semilla + mismo slot ⇒ mismos eventos; el simulador no rellena huecos si
  estuvo detenido; `--at` se limita a `ahora + 5 min` (Constitución §7.1).
- **Estado:** aceptada.

## D-017 · El escenario de parada escribe en `fact_parada`

- **Decisión:** `--scenario stop M-001` inserta una parada de 20 min con causa fija `F-MEC` en
  `fact_parada` y sus eventos IoT, en el turno que contiene el instante del escenario.
- **Alternativas:** emitir solo un evento en `fact_evento` (no altera ningún KPI); modificar
  `fact_produccion` (distorsiona conteos y requiere una orden).
- **Motivo:** AC-406 exige un cambio observable en un KPI. Las vistas de mantenimiento calculan el
  downtime desde `fact_parada` cuando no hay producción para esa máquina/turno/día.
- **Consecuencias:** el cambio se ve en `v_kpi_mantenimiento_maquina_turno`,
  `v_kpi_mantenimiento_planta_dia` y en la condición de downtime de la alerta. Si el turno ya tiene
  producción histórica, la vista prioriza `fact_produccion` y el simulador advierte en el log.
- **Estado:** aceptada.

## D-018 · Separar `run_id` de la ingesta (`sim-`) del histórico (`hist-`)

- **Decisión:** la ingesta usa `run_id = sim-<timestamp>-<sufijo>`; `load_history.py` y
  `verify_history.py` filtran `hist-%` al comparar la ejecución histórica.
- **Alternativas:** reutilizar el `run_id` histórico (mezclaría procedencias); añadir una columna
  `origen` al esquema (cambio innecesario).
- **Motivo:** los eventos en vivo no deben bloquear una recarga idempotente del histórico ni hacer
  fallar la comprobación manifiesto↔base.
- **Consecuencias:** el chequeo de duplicados sigue siendo global; la ingesta se identifica por el
  prefijo y las paradas por `causa_detalle`.
- **Estado:** aceptada.
