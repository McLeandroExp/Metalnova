# Verificación — Incremento 006

Estado: **en curso** · Última actualización: 2026-10-21 · Entorno: PostgreSQL 16.4-alpine en
Docker (`metalinova_db`, healthy) · Power BI Desktop 2.159.883.0 (Microsoft Store).

Commit de esta etapa: `11224f9` (calibración, optimización de la alerta y TMDL). No cierra T-615:
las cuatro páginas y el refresco visual siguen pendientes.

## Criterios de aceptación

| AC | Comando/observación | Salida esperada | Salida observada | Fecha | Veredicto |
|---|---|---|---|---|---|
| AC-601 | revisar páginas del informe | 4 páginas, 9+ KPIs | solo existe la página de validación de T-604; faltan las 4 páginas definitivas | 2026-10-21 | pendiente |
| AC-602 | comparar KPI informe vs vista SQL | coinciden | SQL calibrado: OEE global 71,96 % (180 d) y 78,02 → 66,00 % (ventanas de 30 d); la tarjeta visual aún no se refrescó tras la calibración | 2026-10-21 | en curso (faltan 8 KPI y refresco visual) |
| AC-603 | aplicar filtros en cada página | coherentes | no evaluado en páginas definitivas | — | pendiente |
| AC-604 | drill-through a máquina | navega a detalle | no implementado | — | pendiente |
| AC-605 | revisar visuales | ninguno roto | el modelo TMDL regenerado valida; la página de validación muestra “—” en tarjetas hasta pulsar «Actualizar ahora» | 2026-10-21 | en curso |
| AC-606 | mediciones DirectQuery/Import | documentadas | DirectQuery medido en el spike (D-019); T-616 redujo la alerta filtrada a 335–464 ms | 2026-10-21 | superada |
| AC-607 | revisar `powerbi/` | `.pbix`/`.pbip` presente | `powerbi/final/MetalNova.pbip` presente; faltan las páginas 2–4 | 2026-10-21 | en curso |
| AC-608 | validar escenario calibrado | OEE ≈78 → 66 %, dispersión 5–10 pp, outlier <55 %, 49/49 | OEE 78,02 → 66,00 %; dispersión 8,5 → 7,3 pp; M-047 51,81 %; 49/49 OK | 2026-10-21 | superada |

## Calibración del histórico (T-617, FR-615)

Comando ejecutado (imagen `metalnova/ingestor:local` reconstruida):

```powershell
docker compose run --rm ingestor python src/generate_history.py `
  --seed 42 --days 180 --end-date 2026-10-18 --escenario calibracion
docker compose run --rm ingestor python src/load_history.py --reset
```

Identidad de la corrida: `run_id = hist-h3a58b2b659`, semilla 42, 180 días
(2026-04-22 → 2026-10-18), 52 máquinas. El `run_id` incluye el manifiesto de calibración, por lo
que dos configuraciones distintas no comparten identidad.

| Tabla | Filas |
|---|---:|
| `dim_orden` | 28.080 |
| `fact_produccion` | 28.080 |
| `fact_parada` | 76.021 |
| `fact_mantenimiento` | 2.628 |
| `fact_calidad` | 28.080 |
| `fact_evento` (histórico) | 401.787 |

Generación: 21,15 s · pico 42,8 MB. Carga: 89,15 s · pico 62,7 MB.

### OEE por ventanas de 30 días (medición SQL)

| Ámbito | Inicio | Cierre | Cambio |
|---|---:|---:|---:|
| Global | 0,7802 | 0,6600 | −12,02 pp |
| P-NORTE | 0,8198 | 0,6932 | −12,66 pp |
| P-CENTRO | 0,7800 | 0,6607 | −11,93 pp |
| P-SUR | 0,7344 | 0,6204 | −11,40 pp |
| Dispersión entre plantas | 8,5 pp | 7,3 pp | dentro de 5–10 pp |

A/P/Q global: inicio 0,9902 / 0,8178 / 0,9634; cierre 0,9855 / 0,7131 / 0,9392. El OEE global de
los 180 días es 0,7196 (A 0,9879 · P 0,7655 · Q 0,9516).

### Outliers persistentes (OEE de 180 días por máquina)

| Máquina | Planta | Perfil | OEE |
|---|---|---|---:|
| M-047 | P-SUR | `critica` | 0,5181 |
| M-049 | P-SUR | `desgastada` | 0,6037 |
| M-040 | P-SUR | `desgastada` | 0,6051 |
| M-024 | P-CENTRO | `desgastada` | 0,6278 |
| M-015 | P-NORTE | `desgastada` | 0,6581 |
| M-032 | P-CENTRO | `calidad` | 0,6679 |
| M-005 | P-NORTE | `energia` | — (outlier de consumo) |

Rango de OEE entre máquinas: 0,5181–0,7638. No se afirma que las cuatro máquinas estén por
debajo de 60 %: la medición da una por debajo de 55 % (M-047) y tres por debajo de 61 %.

### Scrap, downtime y energía (ventanas de 30 días)

| Métrica | Inicio | Cierre | Cambio |
|---|---:|---:|---:|
| Scrap | 3,66 % | 6,08 % | +2,42 pp |
| Downtime no planificado | 340 h | 508 h | +49,4 % |
| Energía por unidad buena | 0,3217 kWh | 0,3609 kWh | +12,2 % |

El caso orientativo menciona scrap 3,8 → 6,1 %, downtime +31 % y energía +14 %. Scrap y energía
quedaron cerca; el downtime relativo sigue por encima y se documenta como brecha, no como
coincidencia exacta.

### Validaciones posteriores

- `validate_data.py`: **49/49 comprobaciones OK**; diferencia máxima 2,22e-16 (tolerancia 1e-9).
- `sql/validation/03_calibracion.sql`: **7/7 comprobaciones OK** (OEE inicio 0,7802; cierre
  0,6600; dispersión 0,0853 / 0,0727; una máquina <55 %; tres <61 %; siete outliers).
- `verify_history.py`: **17/17 OK**; histórico con 43 eventos de la ingesta 004.
- Reproducibilidad: una segunda generación con la misma semilla, rango y escenario produjo los
  seis CSV con SHA-256 idéntico y el mismo `run_id`.
- `v_alerta_maquina_critica`: 28.101 filas; 3.284 `alerta`, 248 `critica`, 24.569 `sin_alerta`;
  13 alertas en el último turno por máquina.
- Último evento: `2026-10-22 02:01:15+00` (43 eventos y 21 paradas de la ingesta).
- Respaldo previo: `backups/metalinova_pre_calibracion_20261021.dump` (no versionado).

### Corrección de borde en la alerta

La calibración produjo un OEE exactamente igual a 0,5500000000000000000014 en M-047, turno 1
del 2026-06-28. La vista lo consideraba “no menor a 55 %” y la validación Python lo redondeaba de
otro modo. Se fijó la comparación con 6 decimales en la vista y en `validate_data.py`; el caso
borde ya coincide y la regla no cambia para valores distintos del umbral.

## T-616 · Optimización de la alerta

La vista usa `CROSS JOIN LATERAL` sobre las lecturas de proceso y el índice parcial
`ix_fact_evento_lectura_maquina_time`. Medición sobre el histórico calibrado:

```sql
EXPLAIN ANALYZE
SELECT count(*) FROM v_alerta_maquina_critica
WHERE fecha >= DATE '2026-09-19';
```

Resultados: **464 / 335 / 369 ms** en tres ejecuciones (antes de la optimización: 2.091 / 1.754
ms). La consulta sin filtro midió 347 ms en una ejecución. La validación independiente de la
regla sigue en 49/49, incluida la igualdad de `v_alerta` contra el cálculo Python.

## Modelo semántico (T-604)

`python tools/generate_tmdl.py` generó 12 tablas, 20 relaciones y 45 medidas;
`python tools/validate_model.py` devolvió:

```text
OK: 45 medidas, 20 relaciones, 12 tablas; referencias y tipos coherentes.
```

`v_dim_maquina` incluye la nueva columna `perfil_rendimiento`. El TMDL se regeneró después de la
calibración. La página de validación de T-604 sigue pendiente de que el usuario pulse
«Actualizar ahora» en Power BI Desktop: las tarjetas mostraban “—” aunque las medidas calculan por
ADOMD. No se marca T-604 como hecha sin esa observación visual.

## Medición de modo de conexión (spike)

| Modo | Apertura | Cambio de filtro | Respuesta de visuales | Veredicto |
|---|---|---|---|---|
| DirectQuery | 35,46 s (mediana de 3) | 0,5 s tarjeta/línea; 2,64 s ventana completa | página 3,85 s; frescura 0,35 s | viable (D-019) |
| Import | — | — | no probado: DirectQuery cumplió los umbrales | — |

Umbrales acordados: apertura ≤ 60 s, cambio de filtro ≤ 5 s, frescura ≤ 60 s, 0 errores de
proveedor. Evidencia del spike en `logs/powerbi_spike_006.txt`,
`logs/PowerBIPerformanceFilter.json` y `logs/PowerBIPerformanceFreshness.json`.

## Pendientes y bloqueos

1. Abrir `powerbi/final/MetalNova.pbip`, pulsar «Actualizar ahora» y confirmar que las 10 tarjetas
   de validación muestran valores; luego marcar T-604 y AC-605.
2. Construir las páginas Executive, OEE & Loss Tree, Maintenance y Quality & Energy (T-606–T-609).
3. Verificar filtros, drill-through, tooltips, umbrales y navegación (T-610–T-613).
4. Medir de nuevo la apertura y los filtros en el informe final; si supera 60 s, reevaluar D-019.
5. Completar AC-601…AC-605, AC-607 y el commit T-615.
