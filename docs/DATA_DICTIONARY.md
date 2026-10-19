# Diccionario de datos — MetalNova Smart Factory BI

> Estado: borrador inicial. Las tablas y columnas se completan en el incremento 002.

## Convenciones

- Duración en **minutos**; ciclo ideal en **segundos**; energía en **kWh**; temperatura en **°C**;
  conteos en **unidades**.
- Timestamps con zona (`timestamptz`). Se distinguen `event_time` (cuándo ocurrió),
  `generated_at` (cuándo se generó) e `ingested_at` (cuándo se persistió).

## Tablas de hechos

| Tabla | Grano | Estado |
|---|---|---|
| `fact_produccion` | orden + máquina + turno | por definir |
| `fact_parada` | episodio de parada | por definir |
| `fact_mantenimiento` | orden de trabajo | por definir |
| `fact_calidad` | inspección / lote | por definir |
| `fact_evento` | evento crudo de origen | por definir |
| `fact_evento_rechazado` | evento descartado | por definir |

## Dimensiones conformadas

| Dimensión | Jerarquía |
|---|---|
| `dim_planta` → `dim_linea` → `dim_maquina` | Planta → Línea → Máquina |
| `dim_familia` → `dim_producto` | Familia → Producto |
| `dim_turno`, `dim_causa`, `dim_tiempo`, `dim_tecnico` | — |

## Definiciones de KPI

| KPI | Fórmula | Notas |
|---|---|---|
| OEE | Disponibilidad × Rendimiento × Calidad | ponderado, nunca promedio de porcentajes |
| Disponibilidad | runtime / tiempo de producción planificado | excluye descansos y paradas planificadas |
| Rendimiento | (ciclo ideal × total count) / runtime | |
| Calidad | good count / total count | |
| MTBF | tiempo operativo / nº de fallas | |
| MTTR | tiempo total de reparación / nº de reparaciones | |
| Downtime no planificado | minutos no planificados / tiempo planificado | |
| Scrap Rate | unidades rechazadas / unidades producidas | |
| FPY | unidades sin retrabajo / unidades procesadas | |
| Energía por Unidad Buena | kWh consumidos / unidades buenas | |

## Reglas de clasificación

- **Microparada:** duración < 5 min y sin orden CMMS asociada.
- **Falla:** con orden CMMS o duración ≥ 5 min.

## Latencia

- Objetivo de 10 min: `ingested_at − generated_at`.
- `ingested_at − event_time` se registra aparte (puede ser negativa con reloj simulado).
