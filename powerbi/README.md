# Power BI — Incremento 006 (en curso)

`powerbi/MetalNova.pbip` es el **spike de conexión** y se conserva como referencia de las
mediciones. El entregable en construcción vive en `powerbi/final/MetalNova.pbip` (modelo TMDL de
12 tablas, 20 relaciones y 45 medidas). Las cifras de este README son las del spike con el
histórico anterior; el informe final usa el histórico calibrado (D-020).

## Abrir

1. Power BI Desktop 2.159 o superior.
2. Abrir `MetalNova.pbip`.
3. Si pide credenciales: servidor `127.0.0.1`, base `metalinova`, usuario `metalinova` y la
   contraseña de `POSTGRES_PASSWORD` en `.env` (no se versiona).

## Contenido del spike

- Conexión **DirectQuery** a cuatro vistas: `v_kpi_oee_planta_dia`, `v_kpi_parada`,
  `v_loss_tree`, `v_alerta_maquina_critica`.
- Página `Spike DirectQuery 006`:
  - tarjeta `OEE KPI` (84,47 % global);
  - línea de OEE por fecha y planta;
  - barras de downtime no planificado por causa;
  - segmentación por planta;
  - tabla de máquinas con alerta en el último turno;
  - tabla de paradas de M-001 (para la prueba de frescura).

## Medición (2026-10-21)

| Métrica | Resultado |
|---|---|
| Apertura (mediana de 3) | 35,46 s |
| Cambio de filtro (tarjeta/línea) | ~0,5 s |
| Frescura de una parada nueva | 0,35 s |
| Página completa | 2,17–3,85 s |
| Tabla de alertas | 2,9–3,5 s (cuello de botella) |

Decisión: [D-019](../docs/DECISIONS.md). Evidencia: `logs/powerbi_spike_006.txt` y exportes del
Analizador de rendimiento en `logs/`.

## Limitaciones conocidas

- Las cuatro vistas **no tienen relaciones**: la segmentación solo filtra tarjeta y línea.
- Renombrar las tablas en el modelo provoca «referencia cíclica» al pulsar **Actualizar**;
  **Actualizar objetos visuales** sí funciona.
- La tabla de M-001 no tiene filtro de fecha y devuelve 502 filas.
- La vista `v_alerta_maquina_critica` tarda ~2,9 s en PostgreSQL.

## Siguiente paso (T-604 y páginas)

El modelo de `powerbi/final/` ya se generó y validó. Falta abrirlo, pulsar **Actualizar ahora** y
confirmar las tarjetas de la página de validación; después se montan las cuatro páginas
definitivas. La vista de alertas ya está optimizada (T-616: 335–464 ms filtrada) y el histórico
calibrado está cargado. El spike se conserva como referencia de las mediciones.
