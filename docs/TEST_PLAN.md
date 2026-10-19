# Plan de pruebas — MetalNova Smart Factory BI

Resultados reproducibles. Una prueba solo se marca como superada con evidencia observada.

## Registro

| ID | Prueba | Incremento | Comando | Resultado esperado | Resultado observado | Fecha | Veredicto |
|---|---|---|---|---|---|---|---|
| P-001 | Compose válido | 001 | `docker compose config` | sin errores | — | — | pendiente |
| P-002 | Base saludable | 001 | `docker compose ps` | `db healthy` | — | — | pendiente |
| P-003 | Conectividad Python | 001 | `check_connection.py` | `SELECT 1 -> 1` | — | — | pendiente |
| P-004 | Persistencia tras reinicio | 001 | `down` → `up -d` | datos intactos | — | — | pendiente |
| P-005 | Esquema idempotente | 002 | re-ejecutar DDL | sin duplicados | — | — | pendiente |
| P-006 | Integridad referencial | 002 | `sql/validation/01_integridad.sql` | 0 huérfanos | — | — | pendiente |
| P-007 | Recuento mínimo de eventos | 003 | `SELECT count(*)` | ≥ 200 000 | — | — | pendiente |
| P-008 | Cobertura 180 días | 003 | min/max fecha | 180 días | — | — | pendiente |
| P-009 | Reproducibilidad | 003 | regenerar misma semilla | recuentos idénticos | — | — | pendiente |
| P-010 | No duplicación al reiniciar | 004 | reiniciar simulador | recuento estable | — | — | pendiente |
| P-011 | Latencia | 004/007 | log de métricas | evidencia presente | — | — | pendiente |
| P-012 | Validación de KPI | 005 | `validate_data.py` | diferencias < tolerancia | — | — | pendiente |
| P-013 | DirectQuery vs Import | 006 | mediciones | decisión documentada | — | — | pendiente |
| P-014 | Evento nuevo visible en informe | 007 | escenario reproducible | cambio visible | — | — | pendiente |
| P-015 | Backup y restauración | 007 | `pg_dump` / `pg_restore` | recuentos coinciden | — | — | pendiente |

## Plantilla de resultado

```text
Prueba:        P-0XX
Fecha/hora:    AAAA-MM-DD HH:MM
Versión:       <commit o estado>
Configuración: <parámetros>
Comando:       <comando exacto>
Salida:        <salida observada>
Esperado:      <resultado esperado>
Veredicto:     superada | fallida | bloqueada
Notas:         <observaciones>
```
