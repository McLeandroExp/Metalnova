# Power BI — Informe 006

`powerbi/MetalNova.pbip` es el **spike de conexión** y se conserva como referencia de las
mediciones. El entregable vive en `powerbi/final/MetalNova.pbip` (modelo TMDL de 15 tablas, 27
relaciones y 60 medidas; páginas PBIR generadas por `tools/generate_pbir.py`).

## Abrir

1. Power BI Desktop 2.159 o superior.
2. Abrir `powerbi/final/MetalNova.pbip`.
3. Pulsar **Actualizar ahora**.
4. Si pide credenciales: servidor `127.0.0.1`, base `metalinova`, usuario `metalinova` y la
   contraseña de `POSTGRES_PASSWORD` en `.env` (no se versiona).

## Contenido

- Conexión **DirectQuery** a las vistas KPI.
- 4 páginas principales:
  - `01 Executive Plant Performance`
  - `02 OEE & Loss Tree`
  - `03 Maintenance Reliability`
  - `04 Quality & Energy`
- `Detalle máquina` y `Detalle causa` ocultas, configuradas como destino de drill-through.
- `Tooltip máquina` oculta, usada por la tabla de confiabilidad.
- `Modelo validado (T-604)` oculta, conservada como evidencia de la validación del modelo.

## Regenerar

Power BI Desktop debe estar cerrado.

```powershell
python tools/generate_tmdl.py
python tools/validate_model.py
python tools/generate_pbir.py
python tools/validate_report.py
```

`generate_pbir.py` reescribe los JSON de las páginas; no toca los datos ni el modelo. Si un visual
no renderiza, se corrige en el generador y se vuelve a ejecutar. El formato fino (colores por
serie, tooltips nativos) puede completarse en Desktop.

## Medición (2026-10-21, spike)

| Métrica | Resultado |
|---|---|
| Apertura (mediana de 3) | 35,46 s |
| Cambio de filtro (tarjeta/línea) | ~0,5 s |
| Frescura de una parada nueva | 0,35 s |
| Página completa | 2,17–3,85 s |
| Tabla de alertas | 2,9–3,5 s (optimizada a 335–464 ms con T-616) |

Decisión: [D-019](../docs/DECISIONS.md). Generación del informe: [D-021](../docs/DECISIONS.md).
Evidencia: `logs/powerbi_spike_006.txt` y exportes del Analizador de rendimiento en `logs/`.

## Limitaciones conocidas

- El formato fino y la disposición exacta se verifican en Desktop; el generador no puede pulsar
  botones.
- La página de drill-through necesita que el visual de origen tenga el campo `maquina_codigo` o
  `categoria` en su contexto; ya está configurada en el filtro de página.
- El feed sintético emite dos lecturas de proceso por turno; la cadencia de 15 min se reporta como
  diagnóstico en `v_calidad_senal_iot`, no se finge (D-022).
- La línea de referencia de OEE en 85 % es una **meta del prototipo** (referencia habitual de
  clase mundial), no una cifra del caso. El caso orientativo habla de 78 → 66 %; esa trayectoria
  se muestra en la tendencia y se mide en `specs/006-powerbi/verification.md`.
