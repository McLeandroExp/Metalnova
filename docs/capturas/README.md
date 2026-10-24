# Capturas del informe — MetalNova Smart Factory BI

> **Todos los datos son sintéticos.** Las capturas muestran el prototipo académico, no
> telemetría de una fábrica real.

Capturadas el **2026-10-23** desde `powerbi/final/MetalNova.pbip` con Power BI Desktop
2.159.883.0, usando:

```powershell
npx -y @microsoft/powerbi-report-authoring-cli@latest preview `
  "powerbi/final/MetalNova.pbip" --host desktop `
  --screenshot "<directorio>" --all-pages --scale 1
```

La barra amarilla de sugerencia y el panel **Filtros** de la derecha son parte de la
interfaz de Power BI Desktop, no del informe.

| Archivo | Página | Qué evidencia |
|---|---|---|
| `01-executive.png` | 01 Executive Plant Performance | 6 tarjetas, tendencia y ranking por planta, tabla de alertas con `OEE Alerta` y sin fila total |
| `02-oee-loss-tree.png` | 02 OEE & Loss Tree | A/P/Q, pérdida total, Pareto de causas, matriz máquina-turno con formato condicional y Loss Tree por planta |
| `03-maintenance.png` | 03 Maintenance Reliability | MTBF, MTTR, fallas, downtime, costo, tendencia mensual, dispersión de fallas cortas y tabla por máquina |
| `04-quality-energy.png` | 04 Quality & Energy | FPY, scrap, defectos, retrabajo, energía, scrap por planta/turno/producto y dispersión energía-scrap |
| `detalle-maquina.png` | Detalle máquina | Página de drill-through por `maquina_codigo` |
| `detalle-causa.png` | Detalle causa | Página de drill-through por `dim_causa[categoria]` |
| `tooltip-maquina.png` | Tooltip máquina | Tooltip con MTBF, MTTR y última intervención |
| `modelo-validado-t604.png` | Modelo validado (T-604) | Página oculta de validación de las 10 tarjetas del modelo |

Evidencia detallada y valores observados: `specs/006-powerbi/verification.md`.
