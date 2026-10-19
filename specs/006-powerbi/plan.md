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

## Riesgos

| Riesgo | Mitigación |
|---|---|
| DirectQuery lento en 8 GB | Criterios de cambio a Import ya definidos |
| Autoría programática de visuales frágil | Fallback: guía manual + verificación conjunta |
| Divergencia DAX vs SQL | DAX solo agrega la vista; validación cruzada en 007 |
