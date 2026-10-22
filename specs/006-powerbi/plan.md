# Plan — Incremento 006

## Estrategia híbrida

```text
powerbi/
├── MetalNova.pbip                # proyecto (texto) abierto por Power BI Desktop
├── MetalNova.SemanticModel/      # TMDL: tablas, relaciones, medidas
├── MetalNova.Report/             # report.json (visuales)
├── measures.dax                  # medidas DAX versionadas y legibles
└── BUILD_GUIDE.md                # guía paso a paso para montar visuales en Desktop
```

## Fases

1. **Prueba DirectQuery:** página mínima (KPI, tendencia, Pareto, filtro). Medir apertura, filtros
   y respuesta. Insertar un evento y observar cuándo aparece.
2. **Decisión DirectQuery vs Import** con criterios de la Constitución §9; registrar en
   `docs/DECISIONS.md`.
3. **Modelo semántico:** generar TMDL con tablas de vistas, relaciones y jerarquías
   (Planta→Línea→Máquina, Familia→Producto).
4. **Medidas DAX:** portar los KPI desde las vistas; nunca recalcular lógica divergente.
5. **Visuales:** montar por `BUILD_GUIDE.md`; verificar cada AC.

## Medidas DAX

Se documentan en `measures.dax` y en `docs/DATA_DICTIONARY.md`, con la misma definición que las
vistas SQL (contrato único).

## Hallazgos del spike (2026-10-21)

- DirectQuery cumple los umbrales: apertura 35,46 s, filtro ~0,5 s, frescura 0,35 s. Decisión
  D-019.
- `v_alerta_maquina_critica` tarda 2,9 s en SQL y 3,5 s en DirectQuery; domina la página. Antes de
  montar las cuatro páginas hay que optimizarla (T-616).
- Las cuatro vistas están desconectadas: la segmentación solo filtra la tabla de OEE. El modelo
  definitivo debe apoyarse en dimensiones y relaciones por `id_planta`, `id_maquina`, `id_tiempo`.
- Renombrar tablas en el modelo provoca «referencia cíclica» al refrescar. T-604 reconstruirá el
  modelo con nombres limpios desde Power Query en lugar de renombrar en el modelo.
- El `.pbip` del spike se conserva como referencia de las mediciones; las páginas definitivas lo
  sustituirán.

## Calibración del histórico (FR-615, T-617)

El diagnóstico previo mostró OEE por planta 84,45 / 84,47 / 84,50 % (rango 0,05 pp) y
máquinas 84,47–84,50 %. Las plantas solo se diferenciaban por ruido; cambiar la semilla no crea
dispersión estructural. Se optó por un escenario nuevo, manteniendo `degradado` como histórico
reproducible.

Diseño aplicado:

- `dim_maquina.perfil_rendimiento` con cinco valores; migración idempotente y exposición en
  `v_dim_maquina`.
- Factores por planta (rendimiento/fallas/calidad/energía) y globales de calibración.
- Siete outliers persistentes: M-005 energía, M-015/M-024/M-040/M-049 desgastada, M-032 calidad,
  M-047 crítica.
- El `run_id` incluye el manifiesto de calibración para que dos configuraciones no compartan
  identidad.
- El umbral de alerta OEE se redondea a 6 decimales para estabilizar el borde exacto de 55 %.

Resultado medido (30 días inicio/cierre): OEE 78,02 → 66,00 %; plantas 81,98/78,00/73,44 →
69,32/66,07/62,04; dispersión 8,5 → 7,3 pp; M-047 51,81 %; scrap 3,66 → 6,08 %; energía por
unidad buena +12,2 %; downtime +49,4 % (brecha frente al +31 % orientativo, documentada). La
validación independiente siguió en 49/49 y la reproducibilidad de los seis CSV fue idéntica.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| DirectQuery lento en 8 GB | Criterios de cambio a Import ya definidos |
| Autoría programática de visuales frágil | Fallback: guía manual + verificación conjunta |
| Divergencia DAX vs SQL | DAX solo agrega la vista; validación cruzada en 007 |
