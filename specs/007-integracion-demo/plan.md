# Plan — Incremento 007

## Secuencia

1. Arranque en frío: `down` (sin `-v`) → `up -d` → verificar datos y healthcheck.
2. Ingesta continua + escenario reproducible → medir latencia.
3. Comprobación evento→informe según el modo validado en 006.
4. Backup y restauración en base de prueba separada.
5. Redactar runbook, test plan y plan de mejora.
6. Matriz de cumplimiento final.

## Plan de mejora (estructura)

```text
docs/PLAN_MEJORA.md
├── Metodología y supuestos de coste
├── Riesgos/pérdidas priorizadas (tabla)
├── Ficha por acción (impacto observado vs hipotético)
└── Limitaciones y confianza
```

## Fuentes de coste

Costes sintéticos explícitos: coste de hora-máquina parada, coste por unidad rechazada, coste kWh.
Todos documentados y marcados como supuestos.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Latencia real > 10 min | Documentar la medición y ajustar la frecuencia; explicar la diferencia entre "procesa" y "refresca" |
| Backup no probado | Restaurar en base separada y verificar recuentos |
| Sobrepromesa de ahorros | Etiquetar todo como estimación con supuestos |
