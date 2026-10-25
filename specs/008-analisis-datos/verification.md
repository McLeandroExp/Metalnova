# Verificación — Incremento 008 · Análisis estadístico exploratorio

Estado: **hecho** · Fecha: **2026-10-25** · Corrida canónica: `eda-20261025T172443-9ba731`

Entorno: Windows 11 + Docker Desktop; `db` healthy; imagen `metalinova/ingestor:local`
reconstruida con las dependencias de `python/requirements-analysis.txt`. Todos los datos son
sintéticos y la ventana analizada es **2026-04-22 → 2026-10-18** (180 días).

## 1. Criterios de aceptación

| ID | Criterio | Evidencia | Veredicto |
|---|---|---|---|
| AC-801 | Ejecución completa con código 0 y todas las salidas | `logs/analyze_008_final_b.txt`: 22,8 s, 660,9 MB de pico; 23 CSV/JSON y 18 PNG | OK |
| AC-802 | Dos corridas con la misma semilla producen SHA-256 idénticos | 41 archivos comparados (23 CSV/JSON + 18 PNG); 0 diferencias | OK |
| AC-803 | Estadísticos SQL vs Python con tolerancia 1e-9 | `validate_analysis.py`: **54/54** OK; coincidencia hasta 12 cifras significativas | OK |
| AC-804 | Descriptivos, cuartiles y atípicos para toda variable numérica | T05 (23 variables por nivel) y T08 (11 variables × 4 métodos) | OK |
| AC-805 | Cada figura/tabla declara fuente y n | Informe T01–T17 y F01–F18; el validador comprueba que las 18 figuras existen | OK |
| AC-806 | Advertencia de datos sintéticos, calibración y no causalidad | Cabecera del informe, pies de figura y §11–§12 | OK |
| AC-807 | Documentación y evidencia | `specs/008-*`, README, DATA_DICTIONARY, DECISIONS, TEST_PLAN y este archivo | OK |
| AC-808 | Validaciones existentes siguen pasando | `validate_data.py` 49/49; `02` 24/24; `03` 7/7; `04` 5/5; `05` 13/13; `06` rollback limpio; `07` 12/12 | OK |

## 2. Comandos y salidas observadas

### 2.1 Construcción de la imagen

```powershell
docker compose build ingestor
```

Salida observada: imagen construida; se instalaron pandas 2.2.3, numpy 2.1.3, scipy 1.14.1 y
matplotlib 3.9.2. El pipeline existente sigue funcionando con psycopg 3.2.9.

### 2.2 Análisis completo

```powershell
docker compose --profile tools run --rm ingestor python src/analyze_data.py --seed 42
```

Salida observada (extracto de `logs/analyze_008_final_b.txt`):

```text
run_id            eda-20261025T172443-9ba731
oee_dia           9.360 filas
oee_turno        28.080 filas
oee_planta          540 filas
parada_cons       76.021 filas
mantenimiento     2.628 filas
evento_hist     401.787 filas
evento_sim           51 filas
tablas           23 archivos
figuras          18 PNG
informe          docs/ANALISIS_DATOS.md
duración         22,8 s · pico 660,9 MB
```

Resumen calculado:

```text
OEE ponderado 71,96 % · media máquina-día 71,92 % · mediana 72,28 % · sd 6,41 pp
P-SUR 68,40 % vs P-NORTE 75,67 % (Kruskal–Wallis p < 1e-300, ε² 0,234)
atípicos OEE 184/9.360 (1,97 %) fuera de IQR 1,5×
tendencia -2,40 pp / 30 días (R² 0,976); primeras 30 jornadas 78,02 %, últimas 66,00 %
latencia p95 eventos sim-* 35,0 ms
controles de calidad con fallas 0
```

### 2.3 Validación independiente SQL vs Python

```powershell
docker compose --profile tools run --rm ingestor python src/validate_analysis.py
```

Salida observada (final de `logs/analyze_008_final_validate.txt`):

```text
1. Recuentos y niveles                       5/5 OK
2. Estadísticos descriptivos (máquina-día)  28/28 OK
3. Correlaciones (máquina-turno)            10/10 OK
4. Paradas y temperatura                     8/8 OK
5. Salidas y manifiesto                      3/3 OK
Resultado: 54/54 comprobaciones OK
VEREDICTO: OK
```

Se compararon n, media, mediana, desviación estándar y correlaciones de OEE, disponibilidad,
rendimiento, calidad, scrap, energía, downtime, duración de parada y temperatura. Los 42
archivos del manifiesto conservaron su SHA-256.

### 2.4 Controles estructurales en SQL

```powershell
docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/08_analisis.sql
```

Salida observada (`logs/analyze_008_final_sql.txt`): **22 filas, todas con
`incidencias = 0` y estado `OK`**. Incluye 180 días, 52 máquinas, 9.360 máquina-día,
28.080 máquina-turno, 540 planta-día, 76.021 paradas, 401.787 eventos históricos, fórmula
OEE, nulos, rangos, disponibilidad en techo, correlaciones dentro de bandas y temperatura.

### 2.5 Reproducibilidad

Dos ejecuciones consecutivas con `--seed 42`:

```text
Run A: data/analysis/eda-20261025T172414-9ba731
Run B: data/analysis/eda-20261025T172443-9ba731
Archivos comparados: 41 (23 CSV/JSON + 18 PNG)
Diferencias: 0
```

El primer intento detectó una diferencia mínima en `latencia.csv` porque la consulta de eventos
`sim-*` no tenía `ORDER BY` y la suma de flotantes dependía del orden físico. Se añadió
ordenamiento determinista a todas las extracciones y la comparación posterior dio 0
diferencias. Este incidente queda documentado porque explica por qué el orden importa incluso
con los mismos datos.

### 2.6 Regresión de las validaciones existentes

| Comando | Resultado observado |
|---|---|
| `python src/validate_data.py` | **49/49** comprobaciones OK |
| `sql/validation/02_historico.sql` | 24 filas, 0 incidencias |
| `sql/validation/03_calibracion.sql` | 7/7 bandas OK (OEE 78,02 → 66,00; 1–8 máquinas < 55 %) |
| `sql/validation/04_iot.sql` | 5/5 controles OK; 52/52 máquinas; 0 estados inválidos |
| `sql/validation/05_parada_consolidada.sql` | 13 filas, 0 incidencias; 76.045 → 76.045 episodios |
| `sql/validation/06_parada_consolidada_prueba.sql` | `ROLLBACK`; 0 filas de prueba persistidas |
| `sql/validation/07_kpi_formulas.sql` | 12/12 fórmulas OK; OEE 71,9645 %; MTBF 85,6078 h; MTTR 17,8392 min; FPY 97,6295 % |

## 3. Salidas verificadas

| Artefacto | Estado |
|---|---|
| `docs/ANALISIS_DATOS.md` | 31.853 bytes; 13 secciones; T01–T17; F01–F18 |
| `docs/analysis/figures/F01..F18.png` | 18 archivos, 40–360 KB cada uno |
| `docs/analysis/README.md` | índice de figuras y tablas |
| `docs/analysis/manifest.json` | copia versionada del manifiesto |
| `data/analysis/eda-20261025T172443-9ba731/` | 23 CSV/JSON; manifiesto con 42 SHA-256 |
| `logs/analyze_data_eda-20261025T172443-9ba731.log` | log UTC de la corrida |

## 4. Limitaciones y notas de honestidad

1. **Datos sintéticos.** El escenario `calibracion` fue diseñado para mostrar señal; el análisis
   describe el dataset, no una fábrica real.
2. **Significancia inflada.** Con 9.360–28.080 filas, diferencias triviales resultan
   significativas; se reportan tamaños de efecto, IC y FDR, pero la magnitud manda.
3. **Dependencia temporal.** La autocorrelación lag-1 del OEE diario (0,983) invalida supuestos
   de independencia en pruebas sobre la serie.
4. **Niveles de agregación.** Las correlaciones por máquina-turno y por máquina agregada no son
   intercambiables; el informe muestra ambos niveles y advierte la falacia ecológica.
5. **Disponibilidad en techo.** Media 0,9879 y sd 0,0096: poca varianza y correlación limitada.
6. **Identidades contables.** `A–downtime % ≈ −1` y `calidad–scrap ≈ −1` se derivan de la
   definición; no son hallazgos.
7. **MTBF de corto plazo.** El MTBF de máquina-turno (~7 h) no es el MTBF agregado de 180 días
   (~85,6 h). Se explican ambos y la diferencia de denominador.
8. **Exclusiones.** Las 24 paradas y 51 eventos `sim-*` quedan fuera del análisis principal por
   estar fuera de la ventana; se usan solo para latencia y calidad IoT.
9. **Cobertura IoT.** El feed emite 6, 9 o 12 lecturas por máquina-día y un hueco máximo de
   210 min; la cadencia de 15 min se reporta como diagnóstico (0/9.360), no se imputa.
10. **Coste de infraestructura.** La imagen del ingestor crece ~200 MB y el build requiere
    internet una vez; la ejecución posterior es local.

## 5. Veredicto

El incremento 008 cumple los ocho criterios de aceptación, no altera el esquema ni las
definiciones de KPI, y deja el análisis reproducible con un comando único. Las cifras son
consistentes con los incrementos 005/006 (OEE 71,96 % global; 78,02 → 66,00 % en ventanas de
30 días). **Aprobado.**
