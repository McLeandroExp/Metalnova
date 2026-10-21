# Verificación — Incremento 006

Estado: **en curso** · Última actualización: 2026-10-21 · Entorno: PostgreSQL 16.4-alpine en
Docker (`metalinova_db`, healthy) · Power BI Desktop 2.159.883.0 (Microsoft Store).

| AC | Comando/observación | Salida esperada | Salida observada | Fecha | Veredicto |
|---|---|---|---|---|---|
| AC-601 | revisar páginas del informe | 4 páginas, 9+ KPIs | página de spike con 1 KPI (OEE) | 2026-10-21 | pendiente |
| AC-602 | comparar KPI informe vs vista SQL | coinciden | OEE tarjeta 84,47 % vs SQL 84,4736 %; por planta 84,50/84,47/84,45 % | 2026-10-21 | en curso (faltan 8 KPI) |
| AC-603 | aplicar filtros en cada página | coherentes | tarjeta y línea filtran; barras y alertas no (vistas sin relaciones) | 2026-10-21 | pendiente |
| AC-604 | drill-through a máquina | navega a detalle | — | — | pendiente |
| AC-605 | revisar visuales | ninguno roto | página de spike sin visuales rotos; error al refrescar el modelo (ver notas) | 2026-10-21 | en curso |
| AC-606 | mediciones DirectQuery/Import | documentadas | DirectQuery medido; decisión D-019 | 2026-10-21 | superada |
| AC-607 | revisar `powerbi/` | `.pbix`/`.pbip` presente | `powerbi/MetalNova.pbip` (PBIR + TMDL) | 2026-10-21 | en curso |

## Medición de modo de conexión

| Modo | Apertura | Cambio de filtro | Respuesta de visuales | Veredicto |
|---|---|---|---|---|
| DirectQuery | 35,46 s (mediana de 3) | 0,5 s tarjeta/línea; 2,64 s ventana completa | página 3,85 s; frescura 0,35 s | viable (D-019) |
| Import | — | — | no probado: DirectQuery cumplió los umbrales | — |

Umbrales acordados: apertura ≤ 60 s, cambio de filtro ≤ 5 s, frescura ≤ 60 s, 0 errores de
proveedor. Evidencia completa en `logs/powerbi_spike_006.txt`,
`logs/PowerBIPerformanceFilter.json` y `logs/PowerBIPerformanceFreshness.json`.

## Spike de conexión (T-601…T-603)

Modelo inicial: 4 vistas en DirectQuery (`v_kpi_oee_planta_dia`, `v_kpi_parada`,
`v_loss_tree`, `v_alerta_maquina_critica`), una página con tarjeta OEE, línea por planta,
barras de downtime, segmentación de planta y tablas de alertas/paradas.

- La tarjeta coincide con SQL: 84,47 % global; 84,50 / 84,47 / 84,45 % por planta.
- La tabla de alertas coincide con SQL en su turno más reciente: 15 alerta + 5 crítica = 20.
- El refresco de visuales insertó una parada y la mostró en ~0,35 s; el refresco completo tardó
  2,17 s.
- La tabla de alertas es el cuello de botella: 2,9 s en SQL y 3,5 s vía DirectQuery.
- Las vistas no tienen relaciones: la segmentación solo filtra los visuales de
  `v_kpi_oee_planta_dia`. El modelo definitivo (T-604) debe relacionarlas.
- Renombrar las tablas en el modelo (quitar el prefijo `public`) provoca «referencia cíclica» al
  pulsar «Actualizar»; «Actualizar objetos visuales» funciona. Se corregirá al reconstruir el
  modelo desde Power Query.
- El detalle de M-001 quedó sin filtro de fecha (502 filas); la página definitiva lo limitará.
