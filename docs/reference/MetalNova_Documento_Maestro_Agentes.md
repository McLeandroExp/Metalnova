# METALNOVA SMART FACTORY BI
## Documento maestro de contexto, arquitectura, ejecución y criterios de aceptación

Versión: 1.0
Fecha: 18 de octubre de 2026
Propósito: guía para el propietario del proyecto y para un agente de programación que trabaje localmente en el equipo del propietario.

---

# 1. INSTRUCCIÓN PRINCIPAL PARA EL AGENTE

Actúa como ingeniero de datos, desarrollador Python y asistente técnico de un proyecto académico de Business Intelligence denominado **MetalNova Smart Factory BI**.

Tu objetivo es construir, probar y documentar un prototipo local reproducible que permita analizar el rendimiento de una fábrica mediante datos históricos sintéticos y eventos recientes simulados. Trabaja sobre los archivos del proyecto en el equipo del usuario. No asumas que tienes permisos para instalar software, borrar datos, modificar configuraciones globales o ejecutar operaciones destructivas sin pedir autorización.

## Reglas de trabajo

1. Antes de cambiar archivos, inspecciona el contenido actual del repositorio y resume qué existe.
2. No sobrescribas ni elimines archivos del usuario sin confirmación.
3. Trabaja en etapas pequeñas y verificables. Después de cada etapa, ejecuta pruebas y comunica:
   - qué cambió;
   - qué comandos ejecutaste;
   - qué resultados obtuviste;
   - qué queda pendiente;
   - cómo puede el usuario comprobarlo.
4. No afirmes que una prueba pasó si no la ejecutaste y observaste su resultado.
5. No inventes credenciales, resultados de rendimiento, datos reales ni métricas de fábrica.
6. Usa datos sintéticos, identificados claramente como tales. No presentes los datos generados como telemetría real de una fábrica.
7. Si necesitas elegir entre dos alternativas que cambien la arquitectura, explica ventajas, inconvenientes y consecuencias antes de fijar la decisión. Respeta las decisiones ya documentadas.
8. Mantén las claves, contraseñas y secretos fuera del control de versiones. No muestres secretos en los logs.
9. No hagas que el proyecto dependa de una cuenta de nube, de un servicio externo o de una conexión a internet durante la demostración, salvo que el usuario lo autorice expresamente.
10. Prioriza soluciones simples y mantenibles adecuadas para un equipo Windows 11 con 8 GB de RAM.
11. Si una herramienta no está instalada, primero comprueba su disponibilidad y presenta las opciones. No instales paquetes globales ni cambies la configuración del sistema sin autorización.
12. No construyas una aplicación web adicional ni un API REST salvo que una necesidad demostrada lo justifique. La primera versión se apoya en PostgreSQL, scripts Python y Power BI Desktop.
13. Usa migraciones o scripts SQL idempotentes cuando sea razonable. No dependas de que un script de inicialización de PostgreSQL se vuelva a ejecutar automáticamente sobre un volumen ya existente.
14. Documenta las decisiones en `docs/DECISIONS.md` y las instrucciones operativas en `README.md`.
15. No pases a la etapa siguiente si falla una prueba esencial de la etapa actual sin informar el bloqueo y proponer una solución.

---

# 2. CONTEXTO DEL CASO DE NEGOCIO

## Caso académico

MetalNova es una empresa manufacturera de componentes automotrices con:
- 3 plantas;
- 52 máquinas críticas;
- datos potenciales de IoT/SCADA, MES, CMMS, ERP, calidad y calendario de turnos;
- sistemas aislados y datos que no están integrados de forma consistente.

El caso reporta, como premisas del escenario:
- OEE disminuyó de 78 % a 66 % durante seis meses;
- las paradas no planificadas aumentaron 31 %;
- el scrap subió de 3,8 % a 6,1 %;
- el consumo energético por unidad aumentó 14 %;
- las pérdidas mensuales superan USD 540.000.

Estos números describen el caso académico. No son resultados calculados a partir de los datos sintéticos. El sistema deberá mantener clara esta distinción y no forzar los datos generados para afirmar que reproducen exactamente las cifras reportadas, a menos que se diseñe y documente expresamente un escenario sintético de calibración.

## Objetivo

Construir un prototipo BI que:
- integre fuentes industriales simuladas;
- conserve un histórico de 180 días;
- genere eventos nuevos de manera continua y simulada;
- calcule indicadores coherentes;
- permita analizar pérdidas de disponibilidad, rendimiento y calidad;
- ayude a priorizar acciones de mantenimiento, producción, calidad y energía;
- se pueda ejecutar y demostrar localmente en el equipo del estudiante.

## Entregables de BI previstos

1. **Executive Plant Performance**: KPI de planta, tendencias, comparaciones entre plantas y alertas.
2. **OEE & Loss Tree**: OEE, disponibilidad, rendimiento, calidad, Pareto de pérdidas y matriz máquina-turno.
3. **Maintenance Reliability**: paradas, MTBF, MTTR, recurrencia de averías, mantenimiento y fiabilidad.
4. **Quality & Energy**: scrap, defectos, rendimiento de primera pasada si los datos lo permiten, consumo energético y energía por unidad.

Se esperan filtros consistentes, navegación al detalle, tooltips, umbrales visuales y un plan de mejora cuantificado. Las recomendaciones deberán derivarse de datos identificables y mostrar sus supuestos.

---

# 3. CONTEXTO DEL EQUIPO Y RESTRICCIONES

Entorno informado por el usuario:
- Sistema operativo: Windows 11.
- Python: instalado.
- Docker: instalado y disponible para uso.
- PostgreSQL: aún no instalado como aplicación local; se ejecutará en contenedor.
- Memoria RAM: 8 GB.
- Herramienta de visualización: Power BI Desktop ejecutándose directamente en Windows.
- Lugar de desarrollo y demostración: el mismo equipo local.
- Nube: no requerida.
- Histórico: 180 días.
- Ingesta: simulación continua.
- Objetivo de latencia: menos de 10 minutos desde la generación/recepción del evento hasta que se pueda ver en el informe, sujeto a pruebas.
- Modo de conexión preferido: DirectQuery, solo si el rendimiento y el comportamiento de actualización son aceptables. Si no, usar Import.

Restricciones importantes:
- Power BI Desktop no se ejecutará dentro de Docker; se ejecuta en Windows.
- Docker Compose coordina los servicios de datos.
- No se requiere Power BI Service ni publicación en la nube para la demostración.
- Una frecuencia de ingesta de un minuto NO significa que Power BI refresque automáticamente cada minuto. Debe medirse y demostrarse por separado.
- El objetivo de 200.000 eventos es un mínimo del caso. Se puede usar 300.000 o más como objetivo inicial, pero se ajustará al rendimiento de los 8 GB de RAM.
- No confundir cantidad de eventos con número de filas de todas las tablas. Documentar la definición de “evento” y los recuentos por tabla.

---

# 4. DECISIONES TÉCNICAS VIGENTES

## Decisiones fijadas

- Proyecto local y reproducible.
- Orquestación con Docker Compose.
- PostgreSQL en un contenedor Docker.
- Python en un contenedor para generación e ingesta, compartiendo código con el entorno de desarrollo si hace falta.
- Archivos históricos CSV o Parquet conservados en una carpeta local y montados como volumen.
- Datos sintéticos con 180 días de historia.
- Simulación de eventos nuevos, inicialmente con un ciclo de aproximadamente 1 minuto.
- Power BI Desktop en Windows.
- Cuatro páginas de informe.
- Sin servicios de nube como requisito.
- Prioridad en sencillez, observabilidad, persistencia y facilidad de demostración.

## Decisión pendiente y condicionada a pruebas

**DirectQuery frente a Import**:
- Empezar probando DirectQuery sobre vistas de PostgreSQL.
- Medir latencia, tiempo de carga de los visuales, efecto de los filtros y consumo de recursos.
- Cambiar a Import si DirectQuery es lento, genera demasiada carga o no permite una demostración fiable.
- No comprometerse a actualización automática por minuto antes de validar el comportamiento real de Power BI Desktop.
- Mantener las transformaciones críticas y las reglas de negocio lo más centralizadas posible en SQL/documentación para facilitar el cambio de modo.

## Propuesta de carpetas

```text
metalnova-smart-factory-bi/
├── compose.yaml
├── .env.example
├── .env                       # local, ignorado por Git
├── .gitignore
├── README.md
├── docker/
│   └── postgres/
│       └── init/
├── python/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── generate_history.py
│       ├── simulate_events.py
│       ├── ingest.py
│       ├── validate_data.py
│       └── common/
├── sql/
│   ├── schema/
│   ├── views/
│   ├── indexes/
│   └── validation/
├── data/
│   ├── raw/
│   ├── processed/
│   └── exports/
├── logs/
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_DICTIONARY.md
│   ├── DECISIONS.md
│   ├── TEST_PLAN.md
│   └── DEMO_RUNBOOK.md
└── powerbi/
    └── MetalNova.pbix
```

Esta estructura es una propuesta inicial. Antes de crearla, inspeccionar el directorio de trabajo y evitar sobrescribir archivos existentes.

---

# 5. ARQUITECTURA LÓGICA

Flujo de datos:

1. **Generación histórica Python**:
   - crea un conjunto de datos sintéticos coherentes para 180 días;
   - produce archivos CSV o Parquet en `data/raw/` o `data/processed/`;
   - registra la semilla aleatoria y parámetros para poder repetir la generación;
   - genera dimensiones de referencia y eventos relacionados mediante claves válidas.

2. **Carga inicial**:
   - carga los archivos históricos por lotes a PostgreSQL;
   - valida recuentos, claves, fechas, nulos y duplicados;
   - registra la ejecución de carga.

3. **Almacenamiento analítico PostgreSQL**:
   - mantiene tablas de hechos, dimensiones y, si es útil, una tabla de eventos crudos;
   - ofrece vistas optimizadas para Power BI;
   - incluye índices basados en los filtros y joins usados de verdad;
   - conserva los datos al recrear contenedores mediante un volumen persistente.

4. **Simulador/ingestor Python**:
   - genera eventos nuevos en intervalos configurables;
   - inserta eventos idempotentemente, evitando duplicados;
   - registra `event_time`, `ingested_at` y, cuando sea viable, `processed_at`;
   - captura errores y reintenta de forma limitada, sin duplicar registros;
   - admite detenerse y reiniciarse de forma controlada.

5. **Power BI Desktop en Windows**:
   - se conecta al puerto local publicado por PostgreSQL;
   - usa vistas con contratos estables;
   - ofrece cuatro páginas, medidas, filtros y navegación;
   - inicialmente se prueba DirectQuery y se conserva Import como alternativa.

6. **Demostración**:
   - inicia PostgreSQL;
   - confirma la conectividad;
   - ejecuta la ingesta simulada;
   - muestra un evento nuevo en PostgreSQL;
   - actualiza/refresca el informe según el modo validado;
   - enseña la latencia medida y un caso de análisis.

---

# 6. DISEÑO DE DATOS

## Fuentes sintéticas a representar

- IoT/SCADA: señales de máquina, estados, contadores y energía.
- MES: órdenes, producto, cantidades, producción buena y defectuosa, tiempos de ciclo.
- CMMS: avisos, órdenes de mantenimiento, técnicos, inicio/fin de reparación y tipo de intervención.
- ERP: productos, órdenes, costes de referencia y producción planificada cuando corresponda.
- Calidad: inspecciones, unidades evaluadas, defectos y resultados.
- Calendario de turnos: turnos, horarios, pausas planificadas y tiempo programado.

No es necesario simular todos los sistemas como microservicios. En la primera versión se pueden generar archivos separados por fuente y consolidarlos mediante Python y PostgreSQL.

## Modelo dimensional requerido

Tablas de hechos:
- `fact_produccion`: grano propuesto de una fila por orden + máquina + turno (y fecha/segmento cuando se necesite separar el periodo).
- `fact_parada`: una fila por episodio de parada, con inicio, fin, duración, causa, máquina y condición planificada/no planificada.
- `fact_mantenimiento`: una fila por orden/intervención de mantenimiento, con fechas, tipo, técnico y duración.
- `fact_calidad`: una fila por inspección o lote inspeccionado, con cantidades inspeccionadas, buenas, defectuosas y clasificación.
- Puede existir `fact_evento` o una tabla de aterrizaje para los eventos de origen, según la estrategia de ingesta.

Dimensiones compartidas:
- `dim_maquina`
- `dim_planta`
- `dim_turno`
- `dim_producto`
- `dim_causa`
- `dim_tiempo`
- `dim_tecnico`

Dimensiones adicionales como orden, tipo de defecto o tipo de mantenimiento se pueden incorporar si mejoran la claridad del modelo.

## Reglas de integridad

- Usar claves primarias y foráneas cuando corresponda.
- Definir el grano de cada tabla y documentarlo.
- No mezclar eventos crudos con agregados sin identificarlos.
- Evitar que las uniones entre hechos multipliquen cantidades o duraciones.
- Mantener una zona horaria consistente. Para el prototipo se puede usar timestamps con zona horaria (`timestamptz`) y documentar la zona local de presentación. Evitar sumar horas de duración mediante diferencias de relojes ambiguas.
- Distinguir hora del evento de hora de ingesta.
- Identificar el origen y tipo de cada registro sintético.
- Añadir una clave de evento estable o combinación idempotente que impida duplicados al reiniciar el simulador.
- Usar restricciones razonables para que cantidades y duraciones no sean negativas y las fechas de fin no precedan a las de inicio.

## Volumen

Mínimo: 200.000 eventos de origen para al menos 90 días. Objetivo de diseño: 180 días y aproximadamente 300.000 o más eventos, si el rendimiento local lo permite. Las tablas dimensionales y agregadas son adicionales.

El generador debe permitir configurar:
- días históricos;
- semilla aleatoria;
- volumen o intensidad de eventos;
- velocidad de simulación;
- número de plantas y máquinas;
- escenario base o escenario con degradación.

Debe ser posible volver a generar el histórico de forma reproducible. No regenerar ni borrar una base de datos ya cargada sin pedir confirmación o usar un entorno de prueba separado.

---

# 7. DEFINICIÓN Y VALIDACIÓN DE KPI

Documentar las definiciones antes de crear medidas DAX o visuales. Las definiciones deben aplicarse consistentemente por planta, máquina, turno y periodo.

## OEE

- Disponibilidad = tiempo operativo / tiempo de producción planificado.
- Rendimiento = producción ideal correspondiente al tiempo operativo / producción real o capacidad ideal equivalente, según la convención escogida.
- Calidad = unidades buenas / unidades totales producidas.
- OEE = disponibilidad × rendimiento × calidad.

Precisar:
- cómo se excluyen descansos y paradas planificadas;
- cómo se contabilizan microparadas;
- cómo se trata una máquina sin producción;
- cómo se calcula la producción ideal con el tiempo de ciclo ideal;
- cómo se agregan OEE entre máquinas y turnos. No promediar porcentajes sin ponderación apropiada.

## Otros KPI

- Paradas no planificadas: conteo, duración total y porcentaje del tiempo programado.
- MTTR: tiempo total de reparación / número de reparaciones completadas, con alcance documentado.
- MTBF: tiempo operativo entre fallos / número de fallos, definiendo con claridad el método.
- Scrap rate: unidades defectuosas / unidades totales producidas o inspeccionadas, escogiendo una definición única según disponibilidad de datos.
- Energía por unidad: energía consumida / unidades producidas; definir tratamiento de turnos sin producción.
- Rendimiento de primera pasada (FPY): solo calcular si el modelo tiene datos que permitan distinguir unidades que pasan sin retrabajo.
- Latencia de ingesta: `ingested_at - event_time` puede ser negativa si se simulan eventos con reloj futuro o retrasados; además registrar la diferencia entre generación y persistencia (`ingested_at - generated_at`) para medir el pipeline controlado. Definir cuál métrica representa el objetivo de 10 minutos.
- Pérdida económica: usar costes sintéticos explícitos y documentados. No presentar los USD 540.000 del caso como una cifra derivada si no se calcula realmente.

Validar los KPI mediante consultas SQL o código Python independiente y comparar los resultados con Power BI.

---

# 8. INGESTA SIMULADA Y OBJETIVO DE LATENCIA

La simulación debe ser reproducible, configurable y segura.

Requisitos:
- Intervalo inicial configurable, por defecto 60 segundos.
- Eventos relacionados con las 3 plantas y las 52 máquinas.
- Distribuciones realistas de funcionamiento, paradas, defectos, mantenimientos y energía.
- Algunos eventos deben producir cambios visibles en KPI y gráficos.
- Usar transacciones y operaciones por lotes cuando sea eficiente.
- Hacer las inserciones idempotentes mediante claves únicas y `ON CONFLICT` o mecanismo equivalente.
- No mantener una conexión de base de datos abierta indefinidamente sin gestionar errores.
- Emitir logs legibles con hora, cantidad de eventos, duración de la operación y errores.
- Poder detener el proceso con Ctrl+C y salir limpiamente.
- No imprimir contraseñas en logs.
- Guardar un identificador de ejecución o métrica para analizar fallos.

Registrar timestamps suficientes para medir:
1. hora de creación del evento;
2. hora de recepción/persistencia;
3. hora en que el informe lo muestra, si se puede observar de forma fiable durante la prueba.

El objetivo de menos de 10 minutos se verifica mediante pruebas repetidas y documentadas. No se debe afirmar que se cumple solo porque el script se ejecuta cada minuto.

---

# 9. DOCKER COMPOSE Y SEGURIDAD OPERATIVA

## Servicios previstos

- `db`: PostgreSQL.
- `ingestor`: Python para carga histórica, validación y simulación. Puede usar un comando distinto o perfiles Compose para separar la carga inicial del simulador.
- Opcional, solo si aporta valor demostrado: herramienta de administración de base de datos. No añadirla por defecto en una máquina con 8 GB de RAM.

## Requisitos del Compose

- Fijar versiones estables de las imágenes en lugar de usar `latest` sin control.
- Usar variables de entorno para usuario, base de datos y contraseña.
- Incluir un `.env.example` sin secretos reales.
- Añadir `.env` a `.gitignore`.
- Usar healthcheck de PostgreSQL y `depends_on` con condición de servicio saludable cuando sea compatible con la versión de Compose.
- Usar volumen nombrado para los datos de PostgreSQL.
- Montar las carpetas históricas y logs cuando corresponda.
- Publicar PostgreSQL únicamente en la interfaz local cuando sea viable; por ejemplo, enlazar el puerto al loopback de Windows y no exponerlo a toda la red.
- Documentar el puerto elegido y evitar conflictos con servicios existentes.
- No usar `docker compose down -v` como comando rutinario, porque puede eliminar el volumen con la base de datos.
- Documentar cómo hacer backup y restauración (`pg_dump` y `pg_restore` o alternativa equivalente).
- Documentar que los scripts de `docker-entrypoint-initdb.d` normalmente se ejecutan solo al inicializar un directorio de datos vacío; los cambios de esquema posteriores deben ejecutarse mediante scripts/migraciones explícitas.

## Restricciones de memoria

El equipo tiene 8 GB de RAM. No imponer límites de memoria arbitrarios que provoquen fallos; medir primero y documentar la configuración efectiva de Docker Desktop. Evitar servicios innecesarios, paralelismo excesivo y cargas completas gigantes en memoria. Cargar datos en lotes. Registrar tamaño de tablas, duración de carga y memoria aproximada cuando sea posible.

---

# 10. POWER BI: PRUEBA DIRECTQUERY VS IMPORT

## Primera prueba: DirectQuery

1. Conectar Power BI Desktop a PostgreSQL local.
2. Usar vistas estables en lugar de replicar lógica compleja en muchos visuales.
3. Construir una página de prueba con:
   - KPI principales;
   - tendencia temporal;
   - Pareto de paradas;
   - filtro por planta y máquina.
4. Medir tiempo de apertura, cambio de filtros y respuesta de visuales.
5. Insertar un evento nuevo en PostgreSQL.
6. Probar cómo y cuándo lo muestra Power BI Desktop después de actualizar los visuales.
7. Registrar limitaciones observadas.

## Criterios para mantener DirectQuery

Mantenerlo si:
- los visuales clave responden con fluidez en el equipo del usuario;
- las consultas no saturan PostgreSQL ni hacen que la presentación sea poco fiable;
- el mecanismo de actualización observable cumple el objetivo práctico de latencia;
- no hay inconsistencias entre los visuales.

## Criterios para cambiar a Import

Cambiar a Import si:
- los filtros y visuales son persistentemente lentos;
- las consultas concurrentes provocan una experiencia inaceptable;
- la actualización en Desktop no se comporta como requiere la demostración;
- Import proporciona una presentación más fiable y puede actualizarse con una cadencia suficiente para la demo.

## Plan de contingencia

Si DirectQuery no funciona bien:
- mantener PostgreSQL como fuente analítica;
- cambiar el modelo Power BI a Import;
- documentar el proceso de actualización manual o el mecanismo local probado;
- continuar registrando los eventos nuevos en PostgreSQL;
- demostrar por separado la ingesta continua y actualizar el informe en el momento apropiado.

No implementar un modo híbrido complejo antes de tener una versión funcional simple. Si luego se estudia una arquitectura híbrida, medir el coste y la complejidad.

---

# 11. PLAN DE TRABAJO POR FASES

## Fase 0 — Inspección y preparación
Tareas:
- inspeccionar Windows, Python, Docker y Docker Compose;
- verificar versión de Docker y estado del motor;
- comprobar puertos locales en uso si es necesario;
- revisar el directorio del proyecto;
- crear el esqueleto de carpetas sin borrar archivos existentes.

Aceptación:
- informe breve del entorno;
- estructura inicial creada;
- lista de dependencias y bloqueos;
- instrucciones de arranque documentadas.

## Fase 1 — PostgreSQL en Docker
Tareas:
- escribir `compose.yaml`, Dockerfile de Python y `.env.example`;
- configurar PostgreSQL, healthcheck, volumen persistente y red interna;
- definir conexión local para Power BI;
- añadir una prueba de conectividad desde Python;
- documentar comandos de inicio, logs, parada y reinicio.

Aceptación:
- `docker compose config` valida el Compose;
- `docker compose up --build -d` levanta la base;
- healthcheck llega a estado saludable;
- Python conecta y ejecuta una consulta sencilla;
- reiniciar el contenedor no borra datos;
- el puerto no queda expuesto públicamente por accidente.

## Fase 2 — Modelo SQL
Tareas:
- definir tablas, claves, constraints e índices;
- crear dimensiones y tablas de hechos;
- definir scripts versionados y repetibles;
- crear vistas analíticas iniciales;
- escribir pruebas de integridad.

Aceptación:
- esquema creado en base limpia;
- volver a ejecutar scripts seguros no duplica objetos ni destruye datos;
- claves y relaciones verificadas;
- diccionario de datos documentado.

## Fase 3 — Generador histórico
Tareas:
- generar 180 días;
- representar las 3 plantas y 52 máquinas;
- generar al menos 200.000 eventos de origen;
- exportar archivos CSV/Parquet;
- registrar semilla y parámetros;
- cargar en PostgreSQL en lotes.

Aceptación:
- recuentos de filas por fuente y tabla;
- cobertura temporal de 180 días;
- integridad de claves;
- ningún evento de fin antes del inicio;
- sin cantidades negativas no justificadas;
- generación repetible con la misma semilla;
- tiempos y tamaños de archivo documentados.

## Fase 4 — Ingesta continua
Tareas:
- generar eventos recientes con intervalo configurable;
- persistirlos en PostgreSQL de forma idempotente;
- registrar tiempos y errores;
- incluir un escenario de parada/defecto visible;
- documentar cómo iniciar y detener la simulación.

Aceptación:
- eventos nuevos aparecen en la base;
- reiniciar el proceso no duplica eventos ya insertados;
- errores se registran de forma comprensible;
- latencia se mide con timestamps;
- Ctrl+C permite una salida controlada.

## Fase 5 — Validación de KPI y vistas
Tareas:
- implementar fórmulas de OEE y KPI relacionados;
- comparar cálculos SQL/Python;
- probar filtros por planta, máquina, turno, producto y fecha;
- verificar que joins no multiplican conteos.

Aceptación:
- resultados coinciden dentro de tolerancias documentadas;
- casos de cero producción, cero fallos o datos incompletos se tratan explícitamente;
- definiciones publicadas en `docs/DATA_DICTIONARY.md`.

## Fase 6 — Power BI
Tareas:
- conectar Power BI Desktop a PostgreSQL;
- probar DirectQuery con página pequeña;
- medir rendimiento y actualización;
- decidir DirectQuery o Import con base en resultados;
- construir cuatro páginas, filtros y navegación.

Aceptación:
- filtros coherentes entre páginas;
- KPI trazables a SQL;
- no hay visuales críticos rotos;
- modo de conexión elegido y razones documentados;
- guardar el `.pbix` en `powerbi/`.

## Fase 7 — Prueba integral y demostración
Tareas:
- probar el arranque desde cero y tras reiniciar;
- ejecutar ingesta continua;
- comprobar la llegada de un evento hasta el informe;
- validar copias de seguridad;
- preparar guion de presentación y escenarios.

Aceptación:
- el proceso se puede repetir con pasos documentados;
- no depende de internet para el flujo normal;
- hay evidencias de latencia;
- existen instrucciones para recuperar la base;
- la presentación explica claramente que los datos son sintéticos.

---

# 12. GUÍA DE COMANDOS OPERATIVOS

El agente debe adaptar los comandos a los archivos reales creados y verificar los resultados. No asumir que un comando funciona sin ejecutarlo.

Desde la raíz del proyecto:

```powershell
# Ver versiones y comprobar disponibilidad
python --version
docker --version
docker compose version
docker info

# Validar configuración Compose
docker compose config

# Construir e iniciar servicios
docker compose up --build -d

# Ver estado de servicios
docker compose ps

# Ver logs
docker compose logs --tail 100
docker compose logs -f db
docker compose logs -f ingestor

# Parar contenedores conservando volúmenes
docker compose down

# Volver a iniciar
docker compose up -d
```

Advertencia: no ejecutar `docker compose down -v` como parte de la rutina normal. Puede borrar el volumen que contiene PostgreSQL.

Cuando el proyecto implemente los comandos correspondientes, documentar los comandos concretos para:
- generar históricos;
- cargar históricos;
- validar datos;
- iniciar simulación;
- detener simulación;
- hacer backup;
- restaurar backup;
- reiniciar solo el ingestor sin interrumpir PostgreSQL.

---

# 13. PRUEBAS Y OBSERVABILIDAD

Crear `docs/TEST_PLAN.md` y registrar resultados reproducibles.

Pruebas mínimas:
- configuración Docker válida;
- base saludable;
- persistencia después de reinicio;
- conectividad desde Python;
- carga histórica repetible;
- cobertura de 180 días;
- recuento mínimo de eventos;
- ausencia de claves huérfanas;
- control de duplicados;
- validación de timestamps;
- validación independiente de KPI;
- inserción de un evento nuevo;
- medición de latencia;
- prueba DirectQuery/Import;
- recuperación a partir de backup.

Registrar:
- fecha y hora;
- commit o versión del código, si existe;
- configuración de la prueba;
- número de filas;
- duración de carga y consultas;
- errores;
- resultado esperado y observado.

No exigir un benchmark de producción industrial. El objetivo es un prototipo académico consistente, medible y demostrable.

---

# 14. CRITERIOS DE CALIDAD DEL CÓDIGO

- Python con funciones pequeñas y responsabilidades claras.
- Dependencias mínimas, fijadas en `requirements.txt`.
- Configuración mediante variables de entorno.
- Consultas parametrizadas; no concatenar entradas en SQL.
- Manejo de excepciones con mensajes útiles.
- Logs sin contraseñas.
- Tipos y nombres coherentes.
- Scripts que se puedan ejecutar varias veces sin duplicar ni borrar datos accidentalmente.
- Evitar cargar todo el histórico en RAM si se puede procesar por lotes.
- Tests automáticos para funciones de cálculo y validación.
- Documentar comandos y decisiones.
- No introducir frameworks innecesarios.
- No añadir servicios de mensajería como Kafka o MQTT en la primera versión: la ingesta continua se simula mediante Python. Se pueden reconsiderar solo si el proyecto evoluciona y existe una necesidad clara.

---

# 15. PLAN DE DEMOSTRACIÓN

Preparar un guion de 5–10 minutos, ajustable a la duración solicitada por el profesor.

Secuencia:
1. Explicar el problema de MetalNova y aclarar que el conjunto de datos es sintético.
2. Mostrar el esquema general: archivos históricos → Python → PostgreSQL → Power BI.
3. Mostrar las tres plantas y 52 máquinas en el panel ejecutivo.
4. Abrir OEE & Loss Tree e identificar una pérdida relevante.
5. Ir a Maintenance Reliability y relacionar las paradas con una causa o equipo.
6. Abrir Quality & Energy y mostrar una tendencia de scrap o energía.
7. Iniciar o mantener la ingesta simulada y generar un evento identificable.
8. Mostrar el registro en PostgreSQL y medir cuándo se refleja en Power BI según el modo validado.
9. Presentar 3–5 acciones priorizadas, con impacto estimado, coste/supuesto, responsable propuesto y KPI de seguimiento.
10. Explicar las limitaciones del prototipo y qué requeriría una implantación real.

La demostración no debe depender de que un evento aleatorio ocurra en el momento. Debe existir un escenario reproducible para provocar un cambio visible.

---

# 16. PLAN DE MEJORA CUANTIFICADO

El prototipo debe ayudar a proponer acciones, no solo mostrar gráficos.

Para cada recomendación, registrar:
- problema observado;
- planta/máquina/turno afectado;
- evidencia o consulta que lo respalda;
- acción propuesta;
- prioridad;
- responsable sugerido;
- KPI de seguimiento;
- impacto esperado;
- método de cálculo;
- coste o supuesto usado;
- nivel de confianza y limitaciones.

Distinguir entre:
- impacto observado en los datos sintéticos;
- impacto hipotético calculado mediante supuestos;
- pérdidas del caso académico que no se han recalculado desde los datos.

No presentar una estimación como ahorro garantizado.

---

# 17. ARCHIVOS DOCUMENTALES QUE DEBEN MANTENERSE

`README.md`
- objetivo del proyecto;
- requisitos previos;
- pasos de arranque y parada;
- generación/carga de datos;
- simulación;
- conexión de Power BI;
- troubleshooting;
- backup/restore.

`docs/ARCHITECTURE.md`
- diagrama de componentes;
- flujo de datos;
- puertos y volúmenes;
- responsabilidades por servicio.

`docs/DECISIONS.md`
- decisiones;
- alternativas consideradas;
- motivos;
- consecuencias;
- decisiones pendientes.

`docs/DATA_DICTIONARY.md`
- tablas, columnas, tipos, claves, grano y definiciones KPI.

`docs/TEST_PLAN.md`
- casos, comandos, resultados y fecha de prueba.

`docs/DEMO_RUNBOOK.md`
- orden de arranque;
- escenarios reproducibles;
- pasos de presentación;
- recuperación ante errores.

---

# 18. PRIMER ENCARGO AL AGENTE

Empieza exclusivamente con la **Fase 0: Inspección y preparación**, seguida de una propuesta de la Fase 1.

No generes todavía cientos de miles de datos ni construyas los informes Power BI.

Tareas inmediatas:
1. Inspecciona el directorio de trabajo actual y sus archivos.
2. Comprueba Python, Docker, Docker Compose y el estado del motor Docker.
3. Identifica cualquier conflicto evidente de puertos o permisos, sin cambiar configuraciones globales.
4. Propón la estructura de carpetas final.
5. Prepara `compose.yaml`, `python/Dockerfile`, `python/requirements.txt`, `.env.example`, `.gitignore` y un programa Python mínimo de prueba de conexión, solo después de confirmar dónde debe ubicarse el proyecto y que no se sobrescribirá contenido existente.
6. Configura PostgreSQL con volumen persistente, healthcheck y publicación local segura del puerto.
7. No expongas el puerto de PostgreSQL a toda la red si basta con el acceso desde Windows local.
8. Añade una prueba sencilla que se conecte a PostgreSQL y ejecute `SELECT 1`.
9. Verifica el resultado real de `docker compose config`, el estado saludable y la prueba de conexión.
10. Actualiza el README con los comandos exactos usados y resultados reales.

Al terminar, informa:
- archivos creados o modificados;
- comandos ejecutados;
- resultados de pruebas;
- dónde se guardan los datos persistentes;
- cómo detener y reiniciar sin perder los datos;
- bloqueos y decisiones que requieren autorización del usuario.

No borres volúmenes, no ejecutes `docker compose down -v`, no sobrescribas archivos existentes y no avances a la generación de históricos hasta que el usuario confirme que la base local funciona.

---

# 19. CONDICIONES DE FINALIZACIÓN DEL PROYECTO

Se considera entregado cuando:
- la infraestructura arranca con Docker Compose;
- PostgreSQL conserva los datos entre reinicios;
- existen 180 días de datos sintéticos válidos;
- se alcanza el volumen mínimo documentado de eventos;
- la ingesta simulada inserta eventos nuevos sin duplicados;
- los KPI se validan de manera independiente;
- Power BI contiene las cuatro páginas solicitadas;
- se ha elegido DirectQuery o Import mediante pruebas documentadas;
- se mide y explica la latencia real;
- la demostración se puede repetir siguiendo un runbook;
- el plan de mejora muestra evidencias y supuestos;
- el README y la documentación permiten que otra persona ejecute el proyecto.

**Principio rector:** primero un flujo local mínimo, persistente y comprobable; después datos; luego indicadores; finalmente visualizaciones y demostración. Mantener el sistema sencillo, medible y reproducible es más importante que añadir tecnología innecesaria.
