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

- **Decisión:** DirectQuery, resuelta y medida en D-019.
- **Criterios:** ver Constitución §9.
- **Estado:** sustituida por D-019 (2026-10-21).

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
  fechas, escenario, intensidad, plantas, máquinas y —en `calibracion`— el manifiesto completo de
  factores. La carga exige `--reset` si la base contiene otro `run_id`.
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

## D-019 · DirectQuery sobre las vistas KPI para el informe 006

- **Decisión:** el modelo semántico del 006 usa **DirectQuery** sobre las vistas KPI. No se migra a
  Import en esta iteración.
- **Alternativas:** Import completo; modelo híbrido (Import para `v_alerta_maquina_critica`);
  DirectQuery sin optimizar.
- **Motivo (mediciones del 2026-10-21, spike T-601…T-603):**
  - Apertura del `.pbip`: 37,50 / 35,46 / 33,21 s; mediana **35,46 s** (umbral ≤ 60 s).
  - Cambio de filtro de planta: tarjeta 549 ms y línea 508 ms; ventana completa 2,64 s.
  - Frescura: una parada nueva apareció en **0,35 s**; refresco de visuales 2,17 s.
  - Página inicial: 3,85 s, de los cuales 3,5 s son la tabla de alertas.
  - Cero errores de proveedor en los visuales.
- **Criterio:** la Constitución §9 indica empezar con DirectQuery y cambiar a Import solo si el
  rendimiento o la fiabilidad no cumplen. Los umbrales acordados se cumplieron, así que no se
  probó Import; se reevaluará si el informe final supera los 60 s de apertura.
- **Consecuencias:**
  - Optimizar `v_alerta_maquina_critica` (materializar el último turno o añadir índices) para bajar
    los 2,9–3,5 s actuales.
  - Reconstruir el modelo en T-604 con nombres limpios y relaciones; el renombrado actual provoca
    «referencia cíclica» al refrescar el modelo.
  - Las vistas necesitan relaciones por `id_planta`, `id_maquina` y `fecha` (o un esquema en
    estrella) para que los filtros sean coherentes entre páginas.
- **Actualización 2026-10-21:** T-616 quedó implementado con `CROSS JOIN LATERAL` e índice
  parcial. La consulta filtrada de los últimos 30 días midió 464 / 335 / 369 ms (antes 2.091 /
  1.754 ms); el modelo sigue en DirectQuery. La calibración de datos no cambia esta decisión.
- **Estado:** aceptada; revisable al cerrar el 006.

## D-020 · Escenario `calibracion` con factores de planta y perfiles de máquina

- **Decisión:** añadir un escenario reproducible `calibracion` (semilla 42) que aplica factores
  persistentes por planta y perfiles persistentes por máquina. El escenario `degradado` original
  se conserva con factores neutros para no romper su reproducibilidad histórica.
- **Alternativas:** cambiar la semilla; dejar el histórico homogéneo; retocar CSV a mano; usar solo
  ruido diario. El diagnóstico mostró que la homogeneidad venía del diseño (una sola secuencia
  `random.Random(42)` y plantas sin factores), no de la semilla. El ruido diario se diluye en 180
  días y no produce outliers persistentes.
- **Motivo:** el informe necesita diferencias visibles entre plantas y máquinas. La medición previa
  daba OEE por planta 84,45 / 84,47 / 84,50 % (rango 0,05 pp) y máquinas 84,47–84,50 %; no había
  señal para comparar. El caso orientativo pide 78 → 66 % de OEE.
- **Implementación:**
  - `dim_maquina.perfil_rendimiento` (`estandar`, `desgastada`, `critica`, `calidad`, `energia`);
    la migración es idempotente y `v_dim_maquina` expone la columna.
  - Perfiles outlier (7 de 52 máquinas): M-005 `energia`; M-015, M-024, M-040 y M-049
    `desgastada`; M-032 `calidad`; M-047 `critica`.
  - Factores por planta (`rendimiento` / `fallas` / `calidad` / `energia`): P-NORTE
    0,934 / 0,90 / 1,00 / 1,00; P-CENTRO 0,898 / 1,00 / 0,995 / 1,05; P-SUR
    0,873 / 1,15 / 0,985 / 1,10.
  - Parámetros globales de calibración: calidad 0,98; degradación de rendimiento 0,15, de fallas
    0,40, de calidad 0,03 y de energía 0,01; piso de rendimiento 0,45.
  - El `run_id` incluye el manifiesto de calibración; dos configuraciones distintas no comparten
    identidad. El manifiesto de la corrida registra todos los factores.
- **Resultado observado (2026-10-21, `hist-h3a58b2b659`):** OEE global 78,02 → 66,00 % en ventanas
  de 30 días; plantas 81,98 / 78,00 / 73,44 % al inicio y 69,32 / 66,07 / 62,04 % al cierre
  (dispersión 8,5 y 7,3 pp). Máquinas: M-047 51,81 %, M-049 60,37 %, M-040 60,51 %, M-024
  62,78 %, M-015 65,81 %, M-032 66,79 %. Scrap 3,66 → 6,08 %; energía por unidad buena +12,2 %;
  downtime no planificado +49,4 % (el caso orientativo dice +31 %, no se forzó).
- **Consecuencias:**
  - El histórico final del 006 usa `--escenario calibracion`; la base anterior quedó respaldada en
    `backups/metalinova_pre_calibracion_20261021.dump` (no versionado).
  - Se reejecutaron `verify_history.py` (17/17), `validate_data.py` (49/49) y la comprobación de
    T-616. La evidencia de 003/004/005 se actualiza en 006.
  - El umbral de OEE de la alerta se compara con 6 decimales para que un OEE exactamente igual a
    55 % no cambie de lado por precisión numérica. Afecta solo al borde, no a la regla.
- **Estado:** aceptada.

## D-021 · Generar las páginas del informe con PBIR reproducible

- **Decisión:** las 4 páginas principales, el detalle de máquina, el detalle de
  causa y la página de tooltip se generan con `tools/generate_pbir.py` en el
  formato PBIR (JSON) del proyecto `powerbi/final/MetalNova.Report`. La página de
  validación de T-604 se conserva oculta.
- **Alternativas:** construir las páginas a mano en Power BI Desktop siguiendo
  `BUILD_GUIDE.md`; generar solo el modelo y dejar el informe fuera del control
  de versiones.
- **Motivo:** el informe queda versionado, revisable y reproducible; el agente no
  puede operar la GUI y el usuario solo tiene que abrir, refrescar y validar. El
  esquema PBIR ya estaba probado por la página de validación de T-604.
- **Consecuencias:**
  - `tools/validate_report.py` comprueba que cada `queryRef` existe en el TMDL
    antes de abrir Power BI.
  - El formato fino (colores por serie, disposición exacta, tooltips nativos) se
    completa en Desktop si algún visual no renderiza como se espera.
  - Power BI Desktop debe estar cerrado cuando se regeneran las páginas; el
    script reescribe los JSON.
- **Estado:** aceptada.

## D-022 · Alcance del manejo de calidad IoT (G5)

- **Decisión:** implementar en `event_quality.py` y `ingest.py` el rango válido,
  la cuarentena, el marcado de eventos tardíos/reordenados y una vista de
  cobertura de señal. **No** se aplica *carry-forward* que fabrique lecturas: los
  huecos se declaran (`incompleta`/`unknown`) y se mide la cadencia real.
- **Alternativas:** solo documentar las reglas (estado anterior); implementar
  *carry-forward* completo y recálculo del hecho; cambiar el generador a
  muestreo cada 15 min (elevaría el volumen de ~402k a ~1,3M eventos).
- **Motivo:** el caso f.4 pide manejo explícito y evidencia ejecutada. El feed
  sintético emite dos lecturas por turno (cinco en excursión térmica), no una
  cada 15 min; forzar el muestreo de 15 min multiplicaría por tres el volumen y
  rompería la reproducibilidad del histórico calibrado. Declarar el hueco es más
  honesto que inventar la lectura.
- **Consecuencias:**
  - `v_calidad_senal_iot` usa `senal_lecturas_turno_min = 2` como cobertura
    mínima y expone `cumple_cadencia_15min` como diagnóstico separado.
  - `simulate_events.py --scenario invalid M-001` produce un evento normal, uno
    futuro y uno anterior al rango (los dos últimos a cuarentena) y un evento
    tardío/reordenado.
  - `validate_iot.py` (11 comprobaciones) y `sql/validation/04_iot.sql` son la
    evidencia reproducible.
  - La documentación de la alerta se corrigió: ya no afirma que el histórico
    muestrea cada 15 min.
- **Estado:** aceptada.

## D-023 · Consolidación de paradas solapadas en capa analítica

- **Contexto:** `fact_parada` tiene unicidad `(id_maquina, inicio_at)`, que evita
  duplicados con el mismo inicio pero no dos episodios con inicios distintos que
  se cruzan. El generador y el simulador evitan solapes por construcción; una
  fuente externa o un evento tardío podría introducirlos. El modelo sumaba las
  duraciones de ambos episodios y no sabía que eran una sola parada.
- **Decisión:** crear `v_parada_consolidada` como **unión de intervalos
  estrictamente solapados por máquina**. `fact_parada` se conserva intacta para
  trazabilidad; `v_kpi_parada` y `v_kpi_mantenimiento_maquina_turno` leen de la
  vista consolidada. **No se unen intervalos adyacentes** (`fin = siguiente
  inicio`): pueden tener causas distintas y deben seguir contando como dos
  episodios para MTBF/fallas.
- **Reglas de atribución:**
  - inicio/fin: mínimo inicio y máximo fin; si algún origen está abierto, el
    consolidado queda abierto y la duración se mide hasta `CURRENT_TIMESTAMP`;
  - turno/día: los del episodio que inicia primero;
  - causa: la del episodio no planificado de mayor duración; si todos son
    planificados, la del de mayor duración (empate: el más temprano);
  - CMMS: la primera OT no nula, priorizando la de mayor duración y, si hay un
    tramo no planificado, la de ese tramo;
  - `es_planificada`: `true` solo si todos los orígenes son planificados;
  - `es_microparada`: se recalcula con la unión y `microparada_min = 5`;
  - duración: minutos de la unión, no la suma de los episodios.
- **Alternativas:** rechazar solapes con una constraint `EXCLUDE` (no consolida,
  solo bloquea); corregir `fact_parada` con actualizaciones (más invasivo y
  rompe la trazabilidad del evento crudo); materializar la vista (mejor
  rendimiento, pero requiere orquestar refresh).
- **Motivo:** resuelve el caso sin migrar el esquema ni tocar `fact_produccion`.
  Con los datos actuales (0 solapes estrictos) el resultado es idéntico:
  76.045 episodios y 1.063.948 minutos. La consolidación solo cambia los KPI de
  paradas cuando aparecen solapes reales.
- **Consecuencias:**
  - El OEE, la disponibilidad y el Loss Tree siguen usando
    `fact_produccion.downtime_no_planificado_min`; **no cambian** con esta
    decisión. Si se exige que el OEE también refleje la consolidación, hay que
    abrir una segunda fase de reconciliación de `fact_produccion`.
  - Pareto, MTBF, fallas y microparadas usan la vista consolidada.
  - Limitaciones declaradas: en un solape mixto planificado/no planificado se
    aplica “no planificado gana”; un episodio que cruza turno se atribuye al
    turno de inicio; si hay varias OT, se conserva una principal.
  - La vista tarda ~245 ms sobre 76.045 filas; en DirectQuery conviene medir y,
    si molesta, materializar en una fase posterior.
  - Evidencia: `sql/validation/05_parada_consolidada.sql`,
    `sql/validation/06_parada_consolidada_prueba.sql`,
    `docs/verification/solapes-paradas.md` y `validate_data.py` 49/49.
- **Estado:** aceptada.
