"""Análisis estadístico exploratorio del histórico sintético (incremento 008).

Uso típico dentro del contenedor:

    docker compose --profile tools run --rm ingestor python src/analyze_data.py --seed 42

Genera:

    data/analysis/<run_id>/*.csv|json      tablas y manifiesto de la corrida
    docs/analysis/figures/F01..F18.png     figuras versionadas
    docs/ANALISIS_DATOS.md                 informe analítico
    logs/analyze_data_<run_id>.log         log de la corrida

Todos los datos son **sintéticos**. El análisis no redefine KPI: lee las vistas
como contrato analítico y los hechos como fuente de distribuciones y casos.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import platform
import resource
import sys
import time
import warnings
from datetime import date, datetime, timezone
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from common.db import connect

UTC = timezone.utc
VERSION = "1.0.0"
DEFAULT_SEED = 42
DEFAULT_START = date(2026, 4, 22)
DEFAULT_END = date(2026, 10, 18)
WINDOW_LABEL = "2026-04-22 → 2026-10-18"
SYNTH = "Datos sintéticos · MetalNova Smart Factory BI · ventana 2026-04-22 → 2026-10-18"

PLANT_ORDER = ["P-NORTE", "P-CENTRO", "P-SUR"]
PLANT_COLORS = {"P-NORTE": "#1f77b4", "P-CENTRO": "#e69f00", "P-SUR": "#c0392b"}
SHIFT_LABELS = {0: "L", 1: "M", 2: "X", 3: "J", 4: "V", 5: "S", 6: "D"}

log = logging.getLogger("analyze_data")

warnings.filterwarnings("ignore", message="pandas only supports SQLAlchemy connectable.*")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Análisis estadístico exploratorio del histórico MetalNova (008)."
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="semilla (default: 42)")
    parser.add_argument("--start", type=_iso_date, default=DEFAULT_START, help="primer día (YYYY-MM-DD)")
    parser.add_argument("--end", type=_iso_date, default=DEFAULT_END, help="último día (YYYY-MM-DD)")
    parser.add_argument("--run-id", default=None, help="identificador de la corrida")
    parser.add_argument(
        "--docs-dir",
        default=None,
        help="directorio de documentación (default: <root>/docs)",
    )
    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="calcula tablas pero no regenera las figuras",
    )
    return parser.parse_args(argv)


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"fecha inválida: {value}") from exc


def setup_logging(logs_dir: Path, run_id: str) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.FileHandler(logs_dir / f"analyze_data_{run_id}.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )


def read_df(conn, sql: str) -> pd.DataFrame:
    df = pd.read_sql_query(sql, conn)
    return coerce_numeric(df)


def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte Decimal/objetos numéricos de psycopg a float/int."""
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                continue
    return df


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fmt_es(value, dec: int = 4, pct: bool = False) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    try:
        if pd.isna(value):
            return "—"
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return "sí" if value else "no"
    if pct:
        text = f"{value * 100:,.2f} %"
    elif isinstance(value, (int, np.integer)):
        text = f"{int(value):,}"
    else:
        text = f"{value:,.{dec}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def n_es(value) -> str:
    """Entero con separador de miles español."""
    return f"{int(value):,}".replace(",", ".")


def pct_es(value, dec: int = 2) -> str:
    """Proporción 0-1 como porcentaje español."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"{value * 100:,.{dec}f} %".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def num_es(value, dec: int = 4) -> str:
    return fmt_es(value, dec=dec)


def signed_es(value, dec: int = 2) -> str:
    return f"{value:+,.{dec}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def p_es(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    if value == 0:
        return "< 1e-300"
    if value < 1e-4:
        return f"{value:.1e}".replace(".", ",")
    return f"{value:.4f}".replace(".", ",")


def p_text(value) -> str:
    if value == 0:
        return "p < 1e-300"
    return f"p = {p_es(value)}"


def md_table(df: pd.DataFrame, pct_cols: set[str] | None = None, dec: int = 4) -> str:
    pct_cols = pct_cols or set()
    headers = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            cells.append(fmt_es(row[col], dec=dec, pct=col in pct_cols))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def fisher_ci(r: float, n: int) -> tuple[float, float]:
    if n <= 3 or abs(r) >= 1.0 or math.isnan(r):
        return (math.nan, math.nan)
    z = math.atanh(r)
    se = 1.0 / math.sqrt(n - 3)
    return (math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se))


def bh_fdr(pvalues: np.ndarray) -> np.ndarray:
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    ranked = p[order] * n / np.arange(1, n + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty(n, dtype=float)
    adjusted[order] = np.clip(ranked, 0.0, 1.0)
    return adjusted


def holm(pvalues: list[float]) -> np.ndarray:
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    order = np.argsort(p)
    adjusted = np.empty(n, dtype=float)
    running = 0.0
    for i, idx in enumerate(order):
        running = max(running, (n - i) * p[idx])
        adjusted[idx] = min(running, 1.0)
    return adjusted


def bootstrap_median_ci(values: np.ndarray, rng: np.random.Generator, n_boot: int = 2000) -> tuple[float, float]:
    values = np.asarray(values)
    values = values[~np.isnan(values)]
    if len(values) < 5:
        return (math.nan, math.nan)
    idx = rng.integers(0, len(values), size=(n_boot, len(values)))
    medians = np.median(values[idx], axis=1)
    return tuple(np.percentile(medians, [2.5, 97.5]))


def strength_label(r: float) -> str:
    a = abs(r)
    if a < 0.1:
        return "trivial"
    if a < 0.3:
        return "baja"
    if a < 0.5:
        return "moderada"
    if a < 0.7:
        return "alta"
    return "muy alta"


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------


def build_queries(start: date, end: date) -> dict[str, str]:
    s, e = start.isoformat(), end.isoformat()
    sid = int(start.strftime("%Y%m%d"))
    eid = int(end.strftime("%Y%m%d"))
    return {
        "oee_dia": f"""
            SELECT * FROM v_kpi_oee_maquina_dia
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY fecha, id_maquina
        """,
        "oee_turno": f"""
            SELECT * FROM v_kpi_oee_maquina_turno
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY fecha, id_maquina, id_turno
        """,
        "oee_planta": f"""
            SELECT * FROM v_kpi_oee_planta_dia
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY fecha, planta_codigo
        """,
        "mant_turno": f"""
            SELECT id_maquina, id_turno, fecha, anio_mes,
                   paradas_no_planificadas, minutos_no_planificados_parada,
                   fallas, minutos_fallas, microparadas, minutos_microparadas,
                   fallas_cortas, minutos_fallas_cortas,
                   reparaciones, minutos_reparacion,
                   intervenciones, minutos_intervencion,
                   costo_mantenimiento_usd, mtbf_h, mttr_min,
                   mtbf_corto_h, fallas_cortas_por_100h, microparadas_por_100h,
                   duracion_media_micro_min, duracion_media_falla_min
            FROM v_kpi_mantenimiento_maquina_turno
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY fecha, id_maquina, id_turno
        """,
        "calidad_dia": f"""
            SELECT * FROM v_kpi_calidad_maquina_dia
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY fecha, id_maquina
        """,
        "calidad_producto": f"""
            SELECT * FROM v_kpi_calidad_producto_dia
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY fecha, id_producto
        """,
        "produccion": f"""
            SELECT * FROM v_kpi_produccion
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY fecha, id_maquina, id_turno, id_orden
        """,
        "parada_cons": f"""
            SELECT p.id_parada, p.id_maquina, p.id_turno, p.id_tiempo,
                   p.inicio_at, p.fin_at, p.duracion_min,
                   p.es_planificada, p.es_microparada, p.episodios_origen,
                   p.minutos_solapados, p.causa_detalle,
                   m.codigo AS maquina_codigo, m.tipo AS maquina_tipo,
                   m.criticidad AS maquina_criticidad,
                   pl.codigo AS planta_codigo, l.codigo AS linea_codigo,
                   t.codigo AS turno_codigo, ti.fecha,
                   c.categoria AS causa_categoria, c.descripcion AS causa_descripcion,
                   c.es_planificada AS causa_planificada
            FROM v_parada_consolidada p
            JOIN dim_maquina m ON m.id_maquina = p.id_maquina
            JOIN dim_linea l ON l.id_linea = m.id_linea
            JOIN dim_planta pl ON pl.id_planta = l.id_planta
            JOIN dim_turno t ON t.id_turno = p.id_turno
            JOIN dim_tiempo ti ON ti.id_tiempo = p.id_tiempo
            JOIN dim_causa c ON c.id_causa = p.id_causa
            WHERE p.id_tiempo BETWEEN {sid} AND {eid}
              AND p.causa_detalle NOT LIKE 'Ingesta 004:%'
            ORDER BY p.id_parada
        """,
        "mantenimiento": f"""
            SELECT f.id_mantenimiento, f.tipo, f.estado, f.duracion_min,
                   f.costo_estimado_usd, f.inicio_at, f.fin_at,
                   ti.fecha, ti.anio_mes,
                   m.codigo AS maquina_codigo, m.tipo AS maquina_tipo,
                   m.criticidad AS maquina_criticidad,
                   pl.codigo AS planta_codigo, t.codigo AS turno_codigo,
                   te.nombre AS tecnico_nombre, te.especialidad AS tecnico_especialidad,
                   c.categoria AS causa_categoria
            FROM fact_mantenimiento f
            JOIN dim_maquina m ON m.id_maquina = f.id_maquina
            JOIN dim_linea l ON l.id_linea = m.id_linea
            JOIN dim_planta pl ON pl.id_planta = l.id_planta
            JOIN dim_turno t ON t.id_turno = f.id_turno
            JOIN dim_tiempo ti ON ti.id_tiempo = f.id_tiempo
            LEFT JOIN dim_tecnico te ON te.id_tecnico = f.id_tecnico
            LEFT JOIN dim_causa c ON c.id_causa = f.id_causa
            WHERE ti.fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY f.id_mantenimiento
        """,
        "calidad_raw": f"""
            SELECT f.id_calidad, f.unidades_inspeccionadas, f.unidades_buenas,
                   f.unidades_defectuosas, f.unidades_retrabajo, f.es_retrabajo,
                   f.inspeccion_at, ti.fecha,
                   m.codigo AS maquina_codigo, m.tipo AS maquina_tipo,
                   m.criticidad AS maquina_criticidad,
                   pl.codigo AS planta_codigo, pr.codigo AS producto_codigo,
                   pr.nombre AS producto_nombre, fa.nombre AS familia_nombre,
                   t.codigo AS turno_codigo
            FROM fact_calidad f
            JOIN dim_maquina m ON m.id_maquina = f.id_maquina
            JOIN dim_linea l ON l.id_linea = m.id_linea
            JOIN dim_planta pl ON pl.id_planta = l.id_planta
            JOIN dim_producto pr ON pr.id_producto = f.id_producto
            JOIN dim_familia fa ON fa.id_familia = pr.id_familia
            JOIN dim_turno t ON t.id_turno = f.id_turno
            JOIN dim_tiempo ti ON ti.id_tiempo = f.id_tiempo
            WHERE ti.fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY f.id_calidad
        """,
        "evento_hist": """
            SELECT id_evento, id_maquina, tipo_evento, estado, event_time,
                   generated_at, ingested_at, temperatura_c, energia_kwh
            FROM fact_evento
            WHERE run_id LIKE 'hist-%'
            ORDER BY id_evento
        """,
        "evento_sim": """
            SELECT id_evento, run_id, id_maquina, tipo_evento, estado,
                   event_time, generated_at, ingested_at, temperatura_c, energia_kwh
            FROM fact_evento
            WHERE run_id LIKE 'sim-%'
            ORDER BY id_evento
        """,
        "senal": f"""
            SELECT * FROM v_calidad_senal_iot
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            ORDER BY fecha, id_maquina
        """,
        "dim_maquina": """
            SELECT m.id_maquina, m.codigo AS dim_maquina_codigo,
                   m.tipo AS dim_maquina_tipo, m.criticidad AS dim_maquina_criticidad,
                   m.perfil_rendimiento, m.fabricante, m.modelo,
                   l.codigo AS dim_linea_codigo, pl.codigo AS dim_planta_codigo
            FROM dim_maquina m
            JOIN dim_linea l ON l.id_linea = m.id_linea
            JOIN dim_planta pl ON pl.id_planta = l.id_planta
            ORDER BY m.id_maquina
        """,
        "inventario": f"""
            SELECT 'fact_produccion' AS objeto, 'hecho' AS tipo, count(*)::bigint AS filas,
                   count(*) FILTER (WHERE id_tiempo BETWEEN {sid} AND {eid})::bigint AS en_ventana
            FROM fact_produccion
            UNION ALL
            SELECT 'fact_parada', 'hecho', count(*),
                   count(*) FILTER (WHERE id_tiempo BETWEEN {sid} AND {eid}) FROM fact_parada
            UNION ALL
            SELECT 'fact_mantenimiento', 'hecho', count(*),
                   count(*) FILTER (WHERE id_tiempo BETWEEN {sid} AND {eid}) FROM fact_mantenimiento
            UNION ALL
            SELECT 'fact_calidad', 'hecho', count(*),
                   count(*) FILTER (WHERE id_tiempo BETWEEN {sid} AND {eid}) FROM fact_calidad
            UNION ALL
            SELECT 'fact_evento', 'hecho', count(*),
                   count(*) FILTER (WHERE run_id LIKE 'hist-%') FROM fact_evento
            UNION ALL
            SELECT 'fact_evento_rechazado', 'cuarentena', count(*), NULL::bigint
            FROM fact_evento_rechazado
            UNION ALL
            SELECT 'dim_orden', 'dimensión', count(*),
                   count(*) FILTER (WHERE fecha_plan BETWEEN DATE '{s}' AND DATE '{e}') FROM dim_orden
            UNION ALL
            SELECT 'dim_planta', 'dimensión', count(*), NULL::bigint FROM dim_planta
            UNION ALL
            SELECT 'dim_linea', 'dimensión', count(*), NULL::bigint FROM dim_linea
            UNION ALL
            SELECT 'dim_maquina', 'dimensión', count(*), NULL::bigint FROM dim_maquina
            UNION ALL
            SELECT 'dim_familia', 'dimensión', count(*), NULL::bigint FROM dim_familia
            UNION ALL
            SELECT 'dim_producto', 'dimensión', count(*), NULL::bigint FROM dim_producto
            UNION ALL
            SELECT 'dim_turno', 'dimensión', count(*), NULL::bigint FROM dim_turno
            UNION ALL
            SELECT 'dim_causa', 'dimensión', count(*), NULL::bigint FROM dim_causa
            UNION ALL
            SELECT 'dim_tecnico', 'dimensión', count(*), NULL::bigint FROM dim_tecnico
            UNION ALL
            SELECT 'dim_tiempo', 'dimensión', count(*),
                   count(*) FILTER (WHERE id_tiempo BETWEEN {sid} AND {eid}) FROM dim_tiempo
            ORDER BY objeto
        """,
        "controles": f"""
            SELECT 'invariante_calendario' AS control,
                   count(*) FILTER (WHERE tiempo_planificado_min + downtime_planificado_min <> tiempo_calendario_min)::bigint AS fallas,
                   count(*)::bigint AS total
            FROM fact_produccion WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'invariante_operativo',
                   count(*) FILTER (WHERE tiempo_operativo_min + downtime_no_planificado_min <> tiempo_planificado_min),
                   count(*) FROM fact_produccion WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'conteos_incoherentes',
                   count(*) FILTER (WHERE good_count > total_count OR scrap_count > total_count
                                      OR good_count < 0 OR scrap_count < 0 OR total_count < 0),
                   count(*) FROM fact_produccion WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'parada_fin_menor_inicio',
                   count(*) FILTER (WHERE fin_at IS NOT NULL AND fin_at < inicio_at),
                   count(*) FROM fact_parada WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'parada_duracion_negativa',
                   count(*) FILTER (WHERE duracion_min < 0),
                   count(*) FROM fact_parada WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'mantenimiento_duracion_negativa',
                   count(*) FILTER (WHERE duracion_min < 0),
                   count(*) FROM fact_mantenimiento WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'calidad_conteos_incoherentes',
                   count(*) FILTER (WHERE unidades_buenas + unidades_defectuosas <> unidades_inspeccionadas
                                      OR unidades_retrabajo > unidades_inspeccionadas),
                   count(*) FROM fact_calidad WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'duplicados_produccion',
                   count(*) - count(DISTINCT (id_orden, id_maquina, id_turno, id_tiempo)),
                   count(*) FROM fact_produccion WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'duplicados_evento',
                   count(*) - count(DISTINCT (source_system, source_event_id)),
                   count(*) FROM fact_evento WHERE run_id LIKE 'hist-%'
            UNION ALL
            SELECT 'duplicados_parada',
                   count(*) - count(DISTINCT (id_maquina, inicio_at)),
                   count(*) FROM fact_parada WHERE id_tiempo BETWEEN {sid} AND {eid}
            UNION ALL
            SELECT 'oee_fuera_rango',
                   count(*) FILTER (WHERE oee < 0 OR oee > 1),
                   count(*) FROM v_kpi_oee_maquina_dia
            WHERE fecha BETWEEN DATE '{s}' AND DATE '{e}'
            UNION ALL
            SELECT 'temperatura_fuera_rango',
                   count(*) FILTER (WHERE temperatura_c < -20 OR temperatura_c > 150),
                   count(*) FROM fact_evento
            WHERE run_id LIKE 'hist-%' AND temperatura_c IS NOT NULL
            ORDER BY control
        """,
        "parada_resumen": f"""
            SELECT count(*)::bigint AS episodios_consolidados,
                   count(*) FILTER (WHERE episodios_origen > 1)::bigint AS con_solape,
                   coalesce(sum(minutos_solapados), 0)::bigint AS minutos_solapados
            FROM v_parada_consolidada
            WHERE id_tiempo BETWEEN {sid} AND {eid}
              AND causa_detalle NOT LIKE 'Ingesta 004:%'
        """,
        "rechazos": """
            SELECT motivo, count(*)::bigint AS n
            FROM fact_evento_rechazado
            GROUP BY motivo ORDER BY motivo
        """,
    }


def load_all(conn, start: date, end: date) -> dict[str, pd.DataFrame]:
    queries = build_queries(start, end)
    data: dict[str, pd.DataFrame] = {}
    for name, sql in queries.items():
        t0 = time.perf_counter()
        data[name] = read_df(conn, sql)
        log.info("extraído %-18s %7d filas en %.2f s", name, len(data[name]), time.perf_counter() - t0)
    return data


# ---------------------------------------------------------------------------
# Estadística descriptiva
# ---------------------------------------------------------------------------


def describe_series(series: pd.Series, nivel: str, variable: str) -> dict:
    s = series.dropna()
    n = len(s)
    total = len(series)
    row = {
        "nivel": nivel,
        "variable": variable,
        "n": n,
        "nulos": int(total - n),
        "pct_nulos": (total - n) / total * 100 if total else math.nan,
        "media": math.nan,
        "mediana": math.nan,
        "sd": math.nan,
        "cv": math.nan,
        "min": math.nan,
        "q1": math.nan,
        "q3": math.nan,
        "iqr": math.nan,
        "max": math.nan,
        "asimetria": math.nan,
        "curtosis": math.nan,
    }
    if n == 0:
        return row
    q1, q3 = np.percentile(s, [25, 75])
    sd = s.std(ddof=1) if n > 1 else math.nan
    mean = s.mean()
    row.update(
        media=mean,
        mediana=s.median(),
        sd=sd,
        cv=(sd / mean) if mean else math.nan,
        min=s.min(),
        q1=q1,
        q3=q3,
        iqr=q3 - q1,
        max=s.max(),
        asimetria=stats.skew(s, bias=False) if n > 2 else math.nan,
        curtosis=stats.kurtosis(s, fisher=True, bias=False) if n > 3 else math.nan,
    )
    return row


def describe_frame(df: pd.DataFrame, variables: list[str], nivel: str) -> pd.DataFrame:
    return pd.DataFrame([describe_series(df[v], nivel, v) for v in variables])


def outlier_stats(series: pd.Series, nivel: str, variable: str) -> dict:
    s = series.dropna()
    n = len(s)
    if n < 4:
        return {}
    q1, q3 = np.percentile(s, [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    lo3, hi3 = q1 - 3 * iqr, q3 + 3 * iqr
    n_iqr = int(((s < lo) | (s > hi)).sum())
    n_ext = int(((s < lo3) | (s > hi3)).sum())
    sd = s.std(ddof=1)
    z = (s - s.mean()) / sd if sd else pd.Series(np.zeros(n), index=s.index)
    n_z = int((z.abs() > 3).sum())
    med = s.median()
    mad = (s - med).abs().median()
    if mad > 0:
        mz = 0.6745 * (s - med) / mad
        n_mad = int((mz.abs() > 3.5).sum())
    else:
        n_mad = 0 if s.nunique() == 1 else None
    return {
        "nivel": nivel,
        "variable": variable,
        "n": n,
        "iqr_low": lo,
        "iqr_high": hi,
        "n_iqr": n_iqr,
        "pct_iqr": n_iqr / n * 100,
        "n_extremo": n_ext,
        "pct_extremo": n_ext / n * 100,
        "n_z3": n_z,
        "pct_z3": n_z / n * 100,
        "n_mad": n_mad,
        "pct_mad": (n_mad / n * 100) if n_mad is not None else math.nan,
    }


def top_outliers(df: pd.DataFrame, variable: str, nivel: str, context: list[str], limit: int = 5) -> pd.DataFrame:
    sub = df[[variable] + [c for c in context if c in df.columns]].dropna(subset=[variable]).copy()
    if len(sub) < 4:
        return pd.DataFrame()
    sd = sub[variable].std(ddof=1)
    if not sd:
        return pd.DataFrame()
    sub["z"] = (sub[variable] - sub[variable].mean()) / sd
    med = sub[variable].median()
    mad = (sub[variable] - med).abs().median()
    sub["z_mod"] = 0.6745 * (sub[variable] - med) / mad if mad else np.nan
    sub = sub[sub["z"].abs() > 3].reindex(sub["z"].abs().sort_values(ascending=False).index).head(limit)
    if sub.empty:
        return pd.DataFrame()
    context_parts = []
    for _, row in sub.iterrows():
        bits = []
        for c in context:
            if c in row and not pd.isna(row[c]):
                value = row[c]
                if isinstance(value, pd.Timestamp):
                    bits.append(value.strftime("%Y-%m-%d"))
                else:
                    bits.append(str(value))
        context_parts.append(" · ".join(bits))
    return pd.DataFrame(
        {
            "nivel": nivel,
            "variable": variable,
            "valor": sub[variable].values,
            "z": sub["z"].values,
            "z_mod": sub["z_mod"].values,
            "contexto": context_parts,
        }
    )


def group_test(df: pd.DataFrame, variable: str, factor: str, label: str) -> dict | None:
    sub = df[[variable, factor]].dropna()
    if sub[factor].nunique() < 2:
        return None
    groups, keys = [], []
    for key, grp in sub.groupby(factor):
        if len(grp) >= 2:
            groups.append(grp[variable].values)
            keys.append(key)
    if len(groups) < 2:
        return None
    f_stat, f_p = stats.f_oneway(*groups)
    h_stat, h_p = stats.kruskal(*groups)
    lev_w, lev_p = stats.levene(*groups)
    grand = np.concatenate(groups)
    ss_total = ((grand - grand.mean()) ** 2).sum()
    ss_between = sum(len(g) * (g.mean() - grand.mean()) ** 2 for g in groups)
    eta2 = ss_between / ss_total if ss_total else math.nan
    k = len(groups)
    n = len(grand)
    eps2 = (h_stat - k + 1) / (n - k) if n > k else math.nan
    raw_pairs, pair_labels = [], []
    for (ka, ga), (kb, gb) in combinations(list(zip(keys, groups)), 2):
        try:
            p = stats.mannwhitneyu(ga, gb, alternative="two-sided").pvalue
        except ValueError:
            continue
        raw_pairs.append(p)
        pair_labels.append(f"{ka} vs {kb}")
    adjusted = holm(raw_pairs) if raw_pairs else []
    posthoc = "; ".join(
        f"{lab} p={p:.2e}" for lab, p in zip(pair_labels, adjusted) if p < 0.05
    ) or "ninguno significativo (Holm 0,05)"
    medians = {k_: float(np.median(g)) for k_, g in zip(keys, groups)}
    lo_key = min(medians, key=medians.get)
    hi_key = max(medians, key=medians.get)
    return {
        "variable": variable,
        "factor": label,
        "n": n,
        "grupos": k,
        "mediana_min": medians[lo_key],
        "grupo_min": str(lo_key),
        "mediana_max": medians[hi_key],
        "grupo_max": str(hi_key),
        "diferencia_medianas": medians[hi_key] - medians[lo_key],
        "anova_f": f_stat,
        "anova_p": f_p,
        "kruskal_h": h_stat,
        "kruskal_p": h_p,
        "levene_p": lev_p,
        "eta2": eta2,
        "epsilon2": eps2,
        "posthoc": posthoc,
    }


def chi_square(df: pd.DataFrame, a: str, b: str, label: str) -> dict | None:
    tab = pd.crosstab(df[a], df[b])
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        return None
    chi2, p, dof, _ = stats.chi2_contingency(tab)
    n = int(tab.values.sum())
    v = math.sqrt(chi2 / (n * (min(tab.shape) - 1))) if n else math.nan
    return {
        "asociacion": label,
        "n": n,
        "chi2": chi2,
        "gl": dof,
        "p": p,
        "v_cramer": v,
        "fuerza": strength_label(v),
    }


def daily_weighted(df: pd.DataFrame, group: list[str] | None = None) -> pd.DataFrame:
    keys = group or []
    agg = df.groupby(keys, dropna=False).agg(
        plan=("tiempo_planificado_min", "sum"),
        operativo=("tiempo_operativo_min", "sum"),
        ideales=("minutos_ideales", "sum"),
        total=("total_count", "sum"),
        buenas=("good_count", "sum"),
        scrap=("scrap_count", "sum"),
        energia=("energia_kwh", "sum"),
        downtime=("downtime_no_planificado_min", "sum"),
    )
    agg = agg.reset_index()
    agg["disponibilidad"] = agg["operativo"] / agg["plan"]
    agg["rendimiento"] = agg["ideales"] / agg["operativo"]
    agg["calidad"] = agg["buenas"] / agg["total"]
    agg["oee"] = agg["disponibilidad"] * agg["rendimiento"] * agg["calidad"]
    agg["scrap_rate"] = agg["scrap"] / agg["total"]
    agg["energia_por_unidad_buena"] = agg["energia"] / agg["buenas"]
    agg["downtime_pct"] = agg["downtime"] / agg["plan"]
    return agg


def mann_kendall(values: np.ndarray) -> tuple[float, float]:
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 10:
        return (math.nan, math.nan)
    s = 0
    for i in range(n - 1):
        s += np.sign(x[i + 1 :] - x[i]).sum()
    var_s = n * (n - 1) * (2 * n + 5) / 18
    if s > 0:
        z = (s - 1) / math.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / math.sqrt(var_s)
    else:
        z = 0.0
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    tau = s / (n * (n - 1) / 2)
    return (float(tau), float(p))


def autocorrelation(values: np.ndarray, max_lag: int = 14) -> pd.DataFrame:
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    rows = []
    for lag in range(1, max_lag + 1):
        if len(x) <= lag + 2:
            break
        r = np.corrcoef(x[:-lag], x[lag:])[0, 1]
        rows.append({"lag": lag, "r": float(r)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Análisis
# ---------------------------------------------------------------------------


def analyse(data: dict[str, pd.DataFrame], seed: int) -> dict:
    rng = np.random.default_rng(seed)
    R: dict = {}
    R["inventario"] = data["inventario"]
    R["controles"] = data["controles"]
    R["rechazos"] = data["rechazos"]

    oee_dia = data["oee_dia"].merge(
        data["dim_maquina"][["id_maquina", "perfil_rendimiento", "fabricante"]],
        on="id_maquina",
        how="left",
    )
    oee_turno = data["oee_turno"].copy()
    oee_turno["fecha"] = pd.to_datetime(oee_turno["fecha"])
    oee_dia["fecha"] = pd.to_datetime(oee_dia["fecha"])
    planta = data["oee_planta"].copy()
    planta["fecha"] = pd.to_datetime(planta["fecha"])
    parada = data["parada_cons"].copy()
    parada["fecha"] = pd.to_datetime(parada["fecha"])
    mant = data["mantenimiento"].copy()
    mant["fecha"] = pd.to_datetime(mant["fecha"])
    mant_turno = data["mant_turno"].copy()
    mant_turno["fecha"] = pd.to_datetime(mant_turno["fecha"])
    calidad_raw = data["calidad_raw"].copy()
    calidad_raw["fecha"] = pd.to_datetime(calidad_raw["fecha"])
    calidad_dia = data["calidad_dia"].copy()
    calidad_dia["fecha"] = pd.to_datetime(calidad_dia["fecha"])
    calidad_prod = data["calidad_producto"].copy()
    calidad_prod["fecha"] = pd.to_datetime(calidad_prod["fecha"])
    evento = data["evento_hist"].copy()
    evento["event_time"] = pd.to_datetime(evento["event_time"])
    evento["generated_at"] = pd.to_datetime(evento["generated_at"])
    evento["ingested_at"] = pd.to_datetime(evento["ingested_at"])
    sim = data["evento_sim"].copy()
    for col in ("event_time", "generated_at", "ingested_at"):
        sim[col] = pd.to_datetime(sim[col])
    senal = data["senal"].copy()

    turno = oee_turno.merge(
        mant_turno[
            [
                "fecha",
                "id_maquina",
                "id_turno",
                "paradas_no_planificadas",
                "fallas",
                "microparadas",
                "fallas_cortas",
                "reparaciones",
                "costo_mantenimiento_usd",
                "mtbf_h",
                "mttr_min",
                "microparadas_por_100h",
                "fallas_cortas_por_100h",
            ]
        ],
        on=["fecha", "id_maquina", "id_turno"],
        how="left",
    )
    turno["dia_semana"] = turno["fecha"].dt.dayofweek

    # --- descriptiva -------------------------------------------------------
    desc_parts = [
        describe_frame(
            oee_dia,
            [
                "disponibilidad",
                "rendimiento",
                "calidad",
                "oee",
                "scrap_rate",
                "energia_por_unidad_buena",
                "downtime_no_planificado_pct",
                "downtime_no_planificado_min",
            ],
            "máquina-día",
        ),
        describe_frame(
            turno,
            [
                "mtbf_h",
                "mttr_min",
                "microparadas_por_100h",
                "fallas_cortas_por_100h",
                "costo_mantenimiento_usd",
            ],
            "máquina-turno",
        ),
        describe_frame(
            parada.assign(no_planificada=~parada["es_planificada"]).query("no_planificada"),
            ["duracion_min"],
            "parada no planificada",
        ),
        describe_frame(parada.query("es_planificada"), ["duracion_min"], "parada planificada"),
        describe_frame(mant, ["duracion_min", "costo_estimado_usd"], "mantenimiento"),
        describe_frame(
            calidad_raw.assign(tasa_defectos=calidad_raw["unidades_defectuosas"] / calidad_raw["unidades_inspeccionadas"]),
            ["unidades_inspeccionadas", "tasa_defectos"],
            "inspección",
        ),
        describe_frame(evento, ["temperatura_c"], "evento IoT"),
        describe_frame(data["produccion"], ["total_count", "good_count", "scrap_count"], "orden-máquina-turno"),
    ]
    R["desc_global"] = pd.concat(desc_parts, ignore_index=True)

    plant_rows = []
    for plant in PLANT_ORDER:
        sub = oee_dia[oee_dia["planta_codigo"] == plant]
        for var in [
            "disponibilidad",
            "rendimiento",
            "calidad",
            "oee",
            "scrap_rate",
            "energia_por_unidad_buena",
            "downtime_no_planificado_pct",
        ]:
            row = describe_series(sub[var], "máquina-día", var)
            lo, hi = bootstrap_median_ci(sub[var].values, rng)
            row.update(grupo=plant, mediana_ic_low=lo, mediana_ic_high=hi)
            plant_rows.append(row)
    R["desc_planta"] = pd.DataFrame(plant_rows)

    # --- normalidad --------------------------------------------------------
    norm_rows = []
    for frame, var, level in [
        (oee_dia, "oee", "máquina-día"),
        (oee_dia, "disponibilidad", "máquina-día"),
        (oee_dia, "rendimiento", "máquina-día"),
        (oee_dia, "calidad", "máquina-día"),
        (oee_dia, "scrap_rate", "máquina-día"),
        (oee_dia, "energia_por_unidad_buena", "máquina-día"),
        (parada.query("~es_planificada"), "duracion_min", "parada no planificada"),
        (evento, "temperatura_c", "evento IoT"),
    ]:
        s = frame[var].dropna()
        if len(s) < 8:
            continue
        nt_stat, nt_p = stats.normaltest(s)
        sample = s.sample(n=min(5000, len(s)), random_state=seed) if len(s) > 5000 else s
        try:
            sh_stat, sh_p = stats.shapiro(sample)
        except Exception:  # noqa: BLE001
            sh_stat, sh_p = math.nan, math.nan
        norm_rows.append(
            {
                "nivel": level,
                "variable": var,
                "n": len(s),
                "asimetria": stats.skew(s, bias=False),
                "curtosis": stats.kurtosis(s, fisher=True, bias=False),
                "dagostino_stat": nt_stat,
                "dagostino_p": nt_p,
                "shapiro_n": len(sample),
                "shapiro_stat": sh_stat,
                "shapiro_p": sh_p,
                "veredicto": "no normal (α=0,05)" if nt_p < 0.05 else "compatible con normal",
            }
        )
    R["normalidad"] = pd.DataFrame(norm_rows)

    # --- atípicos ----------------------------------------------------------
    outlier_specs = [
        (oee_dia, "oee", "máquina-día"),
        (oee_dia, "disponibilidad", "máquina-día"),
        (oee_dia, "rendimiento", "máquina-día"),
        (oee_dia, "calidad", "máquina-día"),
        (oee_dia, "scrap_rate", "máquina-día"),
        (oee_dia, "energia_por_unidad_buena", "máquina-día"),
        (oee_dia, "downtime_no_planificado_pct", "máquina-día"),
        (parada.query("~es_planificada"), "duracion_min", "parada no planificada"),
        (mant, "duracion_min", "mantenimiento"),
        (mant, "costo_estimado_usd", "mantenimiento"),
        (evento, "temperatura_c", "evento IoT"),
    ]
    R["outliers"] = pd.DataFrame(
        [outlier_stats(frame[var], level, var) for frame, var, level in outlier_specs if var in frame]
    )

    top_parts = [
        top_outliers(oee_dia, "oee", "máquina-día", ["fecha", "maquina_codigo", "planta_codigo", "maquina_tipo"]),
        top_outliers(
            oee_dia,
            "energia_por_unidad_buena",
            "máquina-día",
            ["fecha", "maquina_codigo", "planta_codigo", "perfil_rendimiento"],
        ),
        top_outliers(
            oee_dia,
            "downtime_no_planificado_pct",
            "máquina-día",
            ["fecha", "maquina_codigo", "planta_codigo"],
        ),
        top_outliers(
            parada.query("~es_planificada"),
            "duracion_min",
            "parada no planificada",
            ["fecha", "maquina_codigo", "planta_codigo", "causa_categoria"],
        ),
    ]
    R["outliers_top"] = pd.concat([p for p in top_parts if not p.empty], ignore_index=True)

    # Mahalanobis sobre A/P/Q
    X = oee_dia[["disponibilidad", "rendimiento", "calidad"]].dropna()
    mu = X.values.mean(axis=0)
    cov = np.cov(X.values, rowvar=False)
    inv = np.linalg.pinv(cov)
    diff = X.values - mu
    d2 = np.einsum("ij,jk,ik->i", diff, inv, diff)
    threshold = stats.chi2.ppf(0.975, df=3)
    maha = oee_dia.loc[X.index, ["fecha", "maquina_codigo", "planta_codigo", "maquina_tipo", "oee"]].copy()
    maha["distancia_mahalanobis"] = np.sqrt(d2)
    maha["umbral"] = math.sqrt(threshold)
    maha["atipico"] = d2 > threshold
    R["mahalanobis"] = {
        "n": int(len(maha)),
        "n_atipicos": int(maha["atipico"].sum()),
        "pct_atipicos": float(maha["atipico"].mean() * 100),
        "umbral": float(math.sqrt(threshold)),
        "d2_all": np.sqrt(d2),
        "top": maha.sort_values("distancia_mahalanobis", ascending=False).head(10),
    }

    # --- correlación ------------------------------------------------------
    corr_vars = [
        "oee",
        "disponibilidad",
        "rendimiento",
        "calidad",
        "scrap_rate",
        "energia_por_unidad_buena",
        "downtime_no_planificado_pct",
        "mtbf_h",
        "mttr_min",
        "microparadas_por_100h",
        "fallas_cortas_por_100h",
    ]
    rows = []
    for a, b in combinations(corr_vars, 2):
        pair = turno[[a, b]].dropna()
        if len(pair) < 4:
            continue
        r, p = stats.pearsonr(pair[a], pair[b])
        rho, sp = stats.spearmanr(pair[a], pair[b])
        lo, hi = fisher_ci(r, len(pair))
        rows.append(
            {
                "var1": a,
                "var2": b,
                "n": len(pair),
                "pearson_r": r,
                "pearson_p": p,
                "pearson_ic_low": lo,
                "pearson_ic_high": hi,
                "spearman_r": rho,
                "spearman_p": sp,
                "fuerza": strength_label(r),
            }
        )
    corr_df = pd.DataFrame(rows)
    corr_df["pearson_p_fdr"] = bh_fdr(corr_df["pearson_p"].values)
    corr_df["spearman_p_fdr"] = bh_fdr(corr_df["spearman_p"].values)
    R["correlaciones"] = corr_df
    R["corr_pearson"] = turno[corr_vars].corr(method="pearson")
    R["corr_spearman"] = turno[corr_vars].corr(method="spearman")
    R["corr_vars"] = corr_vars

    maq = oee_dia.groupby(
        ["id_maquina", "maquina_codigo", "planta_codigo", "maquina_tipo", "maquina_criticidad"],
        as_index=False,
    ).agg(
        oee_media=("oee", "mean"),
        oee_sd=("oee", "std"),
        disponibilidad_media=("disponibilidad", "mean"),
        rendimiento_media=("rendimiento", "mean"),
        calidad_media=("calidad", "mean"),
        scrap_rate=("scrap_rate", "mean"),
        energia_media=("energia_por_unidad_buena", "mean"),
        downtime_pct=("downtime_no_planificado_pct", "mean"),
        downtime_min=("downtime_no_planificado_min", "sum"),
        n=("oee", "size"),
    )
    maq["cv"] = maq["oee_sd"] / maq["oee_media"]
    R["maquinas"] = maq
    R["corr_maquina"] = maq[
        [
            "oee_media",
            "disponibilidad_media",
            "rendimiento_media",
            "calidad_media",
            "scrap_rate",
            "energia_media",
            "downtime_pct",
            "cv",
        ]
    ].corr()

    # --- comparaciones ----------------------------------------------------
    tests = []
    for frame, var, factor, label in [
        (oee_dia, "oee", "planta_codigo", "planta"),
        (oee_dia, "rendimiento", "planta_codigo", "planta"),
        (oee_dia, "calidad", "planta_codigo", "planta"),
        (oee_dia, "scrap_rate", "planta_codigo", "planta"),
        (oee_dia, "energia_por_unidad_buena", "planta_codigo", "planta"),
        (oee_dia, "downtime_no_planificado_pct", "planta_codigo", "planta"),
        (oee_dia, "oee", "maquina_tipo", "tipo de máquina"),
        (oee_dia, "oee", "maquina_criticidad", "criticidad"),
        (turno, "oee", "turno_codigo", "turno"),
        (turno, "scrap_rate", "turno_codigo", "turno"),
        (turno, "mtbf_h", "planta_codigo", "planta"),
        (turno, "mttr_min", "planta_codigo", "planta"),
    ]:
        result = group_test(frame, var, factor, label)
        if result:
            tests.append(result)
    R["pruebas"] = pd.DataFrame(tests)

    oee_dia["scrap_alto"] = oee_dia["scrap_rate"] > oee_dia["scrap_rate"].median()
    turno["scrap_alto"] = turno["scrap_rate"] > turno["scrap_rate"].median()
    asociaciones = [
        chi_square(parada.query("~es_planificada"), "planta_codigo", "causa_categoria", "planta × causa (no planificada)"),
        chi_square(oee_dia, "planta_codigo", "scrap_alto", "planta × scrap alto"),
        chi_square(turno, "turno_codigo", "scrap_alto", "turno × scrap alto"),
        chi_square(mant, "tipo", "planta_codigo", "tipo de mantenimiento × planta"),
    ]
    R["asociaciones"] = pd.DataFrame([a for a in asociaciones if a])

    # --- temporal ---------------------------------------------------------
    diario = daily_weighted(planta, ["fecha"])
    diario = diario.sort_values("fecha").reset_index(drop=True)
    diario["oee_mm7"] = diario["oee"].rolling(7, min_periods=3).mean()
    R["diario"] = diario

    trend_rows = []
    for var in ["oee", "disponibilidad", "rendimiento", "calidad", "scrap_rate", "energia_por_unidad_buena", "downtime_pct"]:
        s = diario[[var]].dropna()
        x = np.arange(len(s))
        lr = stats.linregress(x, s[var].values)
        tau, mk_p = mann_kendall(s[var].values)
        trend_rows.append(
            {
                "metrica": var,
                "n": len(s),
                "pendiente_dia": lr.slope,
                "pendiente_30d": lr.slope * 30,
                "r2": lr.rvalue**2,
                "p": lr.pvalue,
                "mk_tau": tau,
                "mk_p": mk_p,
            }
        )
    R["tendencia"] = pd.DataFrame(trend_rows)
    R["autocorrelacion"] = autocorrelation(diario["oee"].values)

    first30 = diario.head(30)
    last30 = diario.tail(30)

    def weighted_block(df: pd.DataFrame) -> dict:
        plan = df["plan"].sum()
        op = df["operativo"].sum()
        ideal = df["ideales"].sum()
        total = df["total"].sum()
        good = df["buenas"].sum()
        scrap = df["scrap"].sum()
        energy = df["energia"].sum()
        down = df["downtime"].sum()
        return {
            "oee": (op / plan) * (ideal / op) * (good / total),
            "disponibilidad": op / plan,
            "rendimiento": ideal / op,
            "calidad": good / total,
            "scrap_rate": scrap / total,
            "energia_por_unidad_buena": energy / good,
            "downtime_pct": down / plan,
            "n_dias": len(df),
        }

    w_first, w_last = weighted_block(first30), weighted_block(last30)
    window_rows = []
    for key, label in [
        ("oee", "OEE"),
        ("disponibilidad", "Disponibilidad"),
        ("rendimiento", "Rendimiento"),
        ("calidad", "Calidad"),
        ("scrap_rate", "Scrap rate"),
        ("energia_por_unidad_buena", "kWh/unidad buena"),
        ("downtime_pct", "Downtime no planificado %"),
    ]:
        delta = w_last[key] - w_first[key]
        window_rows.append(
            {
                "metrica": label,
                "primeros_30": w_first[key],
                "ultimos_30": w_last[key],
                "delta_abs": delta,
                "delta_pct": (delta / w_first[key] * 100) if w_first[key] else math.nan,
            }
        )
    R["ventanas"] = pd.DataFrame(window_rows)
    R["ventanas_resumen"] = {"primeros_30": w_first, "ultimos_30": w_last}

    # --- categóricas ------------------------------------------------------
    cat = (
        parada.groupby(["causa_categoria", "es_planificada"], as_index=False)
        .agg(n=("id_parada", "count"), minutos=("duracion_min", "sum"), dur_media=("duracion_min", "mean"), dur_mediana=("duracion_min", "median"))
        .sort_values("minutos", ascending=False)
    )
    cat["share_minutos"] = cat.groupby("es_planificada")["minutos"].transform(lambda s: s / s.sum() * 100)
    R["categorias_parada"] = cat

    mant_tipo = (
        mant.groupby("tipo", as_index=False)
        .agg(n=("id_mantenimiento", "count"), minutos=("duracion_min", "sum"), dur_media=("duracion_min", "mean"), dur_mediana=("duracion_min", "median"), coste_total=("costo_estimado_usd", "sum"), coste_medio=("costo_estimado_usd", "mean"))
        .sort_values("n", ascending=False)
    )
    R["mantenimiento_tipo"] = mant_tipo

    prod = (
        calidad_prod.groupby(["producto_codigo", "producto_nombre", "familia_nombre"], as_index=False)
        .agg(total=("total_count", "sum"), scrap=("scrap_count", "sum"))
    )
    prod["scrap_rate"] = prod["scrap"] / prod["total"]
    z = 1.96
    n = prod["total"].astype(float)
    p = prod["scrap_rate"]
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    prod["ic_low"] = center - half
    prod["ic_high"] = center + half
    prod = prod.sort_values("scrap_rate")
    R["scrap_producto"] = prod

    senal_summary = (
        senal.groupby("estado_senal", as_index=False)
        .agg(n=("id_maquina", "count"), lecturas=("lecturas", "sum"), faltantes=("lecturas_faltantes", "sum"))
        .sort_values("n", ascending=False)
    )
    senal_summary["pct"] = senal_summary["n"] / senal_summary["n"].sum() * 100
    senal_summary["cumple_cadencia"] = senal_summary["estado_senal"].map(
        senal.groupby("estado_senal")["cumple_cadencia_15min"].mean()
    )
    R["senal"] = senal_summary

    sim["latencia_ms"] = (sim["ingested_at"] - sim["generated_at"]).dt.total_seconds() * 1000
    lat = sim["latencia_ms"].dropna()
    R["latencia"] = {
        "n": int(len(lat)),
        "media_ms": float(lat.mean()),
        "p50_ms": float(lat.quantile(0.5)),
        "p95_ms": float(lat.quantile(0.95)),
        "p99_ms": float(lat.quantile(0.99)),
        "min_ms": float(lat.min()),
        "max_ms": float(lat.max()),
    }
    R["latencia_eventos"] = lat
    R["parada_resumen"] = data["parada_resumen"].iloc[0].to_dict()

    # --- nulos ------------------------------------------------------------
    null_rows = []
    for level, frame, var, note in [
        ("máquina-día", oee_dia, "oee", ""),
        ("máquina-día", oee_dia, "rendimiento", ""),
        ("máquina-día", oee_dia, "calidad", ""),
        ("máquina-día", oee_dia, "energia_por_unidad_buena", ""),
        ("máquina-turno", turno, "mtbf_h", "NULL esperado si no hubo fallas"),
        ("máquina-turno", turno, "mttr_min", "NULL esperado si no hubo reparaciones"),
        ("máquina-día", calidad_dia, "fpy", "NULL esperado si no hubo inspecciones"),
    ]:
        s = frame[var]
        null_rows.append(
            {
                "nivel": level,
                "variable": var,
                "n": int(len(s)),
                "nulos": int(s.isna().sum()),
                "pct_nulos": float(s.isna().mean() * 100),
                "nota": note,
            }
        )
    R["nulos"] = pd.DataFrame(null_rows)
    R["controles"]["estado"] = np.where(R["controles"]["fallas"] == 0, "OK", "ERROR")

    # --- agregados de máquina y eventos ----------------------------------
    R["evento"] = evento
    R["parada"] = parada
    R["oee_dia"] = oee_dia
    R["oee_turno"] = oee_turno
    R["turno"] = turno
    R["calidad_dia"] = calidad_dia
    R["mant"] = mant
    R["senal_df"] = senal
    R["sim"] = sim
    R["data"] = data

    R["resumen"] = build_summary(R)
    return R


def build_summary(R: dict) -> dict:
    desc = R["desc_global"].set_index(["nivel", "variable"])
    oee = desc.loc[("máquina-día", "oee")]
    ventanas = R["ventanas"].set_index("metrica")
    diario = R["diario"]
    weighted = daily_weighted(R["data"]["oee_planta"], ["fecha"])
    plan = weighted["plan"].sum()
    op = weighted["operativo"].sum()
    ideal = weighted["ideales"].sum()
    total = weighted["total"].sum()
    good = weighted["buenas"].sum()
    oee_weighted = (op / plan) * (ideal / op) * (good / total)
    corr = R["correlaciones"]
    oee_corr = corr[(corr["var1"] == "oee") | (corr["var2"] == "oee")].copy()
    oee_corr["otra"] = np.where(oee_corr["var1"] == "oee", oee_corr["var2"], oee_corr["var1"])
    oee_corr = oee_corr.reindex(oee_corr["pearson_r"].abs().sort_values(ascending=False).index)
    top = oee_corr.iloc[0]
    plant_test = R["pruebas"].query("variable == 'oee' and factor == 'planta'").iloc[0]
    outlier_oee = R["outliers"][
        (R["outliers"]["variable"] == "oee") & (R["outliers"]["nivel"] == "máquina-día")
    ].iloc[0]
    trend = R["tendencia"].set_index("metrica").loc["oee"]
    cat = R["categorias_parada"].query("~es_planificada").sort_values("minutos", ascending=False).iloc[0]
    return {
        "oee_ponderado": float(oee_weighted),
        "oee_media": float(oee["media"]),
        "oee_mediana": float(oee["mediana"]),
        "oee_sd": float(oee["sd"]),
        "oee_min": float(oee["min"]),
        "oee_max": float(oee["max"]),
        "oee_corr_top_var": str(top["otra"]),
        "oee_corr_top_r": float(top["pearson_r"]),
        "planta_test_p": float(plant_test["kruskal_p"]),
        "planta_test_eps2": float(plant_test["epsilon2"]),
        "planta_mediana_min": float(plant_test["mediana_min"]),
        "planta_mediana_max": float(plant_test["mediana_max"]),
        "planta_grupo_min": str(plant_test["grupo_min"]),
        "planta_grupo_max": str(plant_test["grupo_max"]),
        "outliers_oee_n": int(outlier_oee["n_iqr"]),
        "outliers_oee_pct": float(outlier_oee["pct_iqr"]),
        "tendencia_pendiente_30d": float(trend["pendiente_30d"]),
        "tendencia_r2": float(trend["r2"]),
        "ventana_oee_inicio": float(ventanas.loc["OEE", "primeros_30"]),
        "ventana_oee_fin": float(ventanas.loc["OEE", "ultimos_30"]),
        "causa_top": str(cat["causa_categoria"]),
        "causa_top_share": float(cat["share_minutos"]),
        "latencia_p95": float(R["latencia"]["p95_ms"]),
        "controles_error": int((R["controles"]["fallas"] > 0).sum()),
        "n_machine_day": int(len(R["oee_dia"])),
        "n_shifts": int(len(R["turno"])),
        "n_stops": int(len(R["parada"])),
        "n_events": int(len(R["evento"])),
    }


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------


def setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 150,
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.labelsize": 9,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
        }
    )


def save_fig(fig, path: Path) -> None:
    fig.text(0.01, 0.005, SYNTH, fontsize=6, color="#666666")
    fig.savefig(path, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    log.info("figura %s", path.name)


def make_figures(R: dict, figures_dir: Path) -> list[str]:
    figures_dir.mkdir(parents=True, exist_ok=True)
    setup_style()
    made: list[str] = []
    oee = R["oee_dia"]
    parada = R["parada"]
    unplanned = parada.query("~es_planificada")

    # F01 histograma OEE
    vals = oee["oee"].dropna()
    q1, q3 = np.percentile(vals, [25, 75])
    iqr = q3 - q1
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.hist(vals, bins=50, color="#4C72B0", edgecolor="white", linewidth=0.4, density=True)
    xs = np.linspace(vals.min(), vals.max(), 300)
    ax.plot(xs, stats.norm.pdf(xs, vals.mean(), vals.std(ddof=1)), color="#222222", lw=1, label="Normal (misma media y sd)")
    ax.axvline(vals.median(), color="#111111", lw=1.2, label=f"Mediana {vals.median() * 100:.2f} %")
    for x in (q1 - 1.5 * iqr, q3 + 1.5 * iqr):
        ax.axvline(x, color="#c0392b", ls="--", lw=1, label="Cercas IQR 1,5×" if x == q1 - 1.5 * iqr else None)
    ax.set_title("Distribución del OEE por máquina-día")
    ax.set_xlabel("OEE")
    ax.set_ylabel("Densidad")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.legend(fontsize=7)
    ax.text(0.99, 0.97, f"n = {len(vals):,}\nsd = {vals.std(ddof=1) * 100:.2f} pp\nasimetría = {stats.skew(vals):.2f}".replace(",", "."),
            transform=ax.transAxes, ha="right", va="top", fontsize=7, bbox=dict(fc="white", ec="#cccccc", alpha=0.8))
    save_fig(fig, figures_dir / "F01_histograma_oee.png")
    made.append("F01_histograma_oee.png")

    # F02 OEE por planta
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    data = [oee.loc[oee.planta_codigo == p, "oee"].dropna().values for p in PLANT_ORDER]
    bp = ax.boxplot(data, tick_labels=PLANT_ORDER, patch_artist=True, showfliers=False, widths=0.5)
    for patch, plant in zip(bp["boxes"], PLANT_ORDER):
        patch.set_facecolor(PLANT_COLORS[plant])
        patch.set_alpha(0.55)
    rng = np.random.default_rng(42)
    for i, (plant, values) in enumerate(zip(PLANT_ORDER, data), start=1):
        ax.scatter(i + rng.normal(0, 0.055, len(values)), values, s=3, alpha=0.25, color=PLANT_COLORS[plant])
    ax.set_title("OEE por planta (máquina-día)")
    ax.set_ylabel("OEE")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    save_fig(fig, figures_dir / "F02_oee_por_planta.png")
    made.append("F02_oee_por_planta.png")

    # F03 componentes por planta
    fig, axes = plt.subplots(1, 3, figsize=(9.2, 3.6), sharey=False)
    for ax, var, title in zip(axes, ["disponibilidad", "rendimiento", "calidad"], ["Disponibilidad", "Rendimiento", "Calidad"]):
        series = [oee.loc[oee.planta_codigo == p, var].dropna().values for p in PLANT_ORDER]
        bp = ax.boxplot(series, tick_labels=PLANT_ORDER, patch_artist=True, showfliers=False, widths=0.55)
        for patch, plant in zip(bp["boxes"], PLANT_ORDER):
            patch.set_facecolor(PLANT_COLORS[plant])
            patch.set_alpha(0.55)
        ax.set_title(title)
        ax.tick_params(axis="x", labelrotation=20)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    fig.suptitle("Componentes del OEE por planta", fontweight="bold")
    save_fig(fig, figures_dir / "F03_componentes_por_planta.png")
    made.append("F03_componentes_por_planta.png")

    # F04 serie diaria
    diario = R["diario"]
    fig, axes = plt.subplots(2, 1, figsize=(8.4, 6.4), sharex=True)
    ax = axes[0]
    ax.plot(diario["fecha"], diario["oee"], color="#8fa6b8", lw=0.9, label="OEE diario ponderado")
    ax.plot(diario["fecha"], diario["oee_mm7"], color="#1f4e79", lw=2, label="Media móvil 7 d")
    x = np.arange(len(diario))
    lr = stats.linregress(x, diario["oee"].values)
    ax.plot(diario["fecha"], lr.intercept + lr.slope * x, color="#c0392b", ls="--", lw=1.4,
            label=f"Tendencia ({lr.slope * 30 * 100:+.2f} pp/30 d, R²={lr.rvalue**2:.2f})")
    ax.set_title("Evolución diaria del OEE")
    ax.set_ylabel("OEE")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.legend(fontsize=7)
    ax = axes[1]
    for plant in PLANT_ORDER:
        sub = R["data"]["oee_planta"].query("planta_codigo == @plant")
        sub = daily_weighted(sub, ["fecha"]).sort_values("fecha")
        ax.plot(sub["fecha"], sub["oee"].rolling(7, min_periods=3).mean(), color=PLANT_COLORS[plant], lw=1.5, label=plant)
    ax.set_title("OEE por planta (media móvil 7 d)")
    ax.set_ylabel("OEE")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.legend(fontsize=7)
    save_fig(fig, figures_dir / "F04_serie_oee.png")
    made.append("F04_serie_oee.png")

    # F05 correlaciones
    corr_vars = R["corr_vars"]
    labels = {
        "oee": "OEE",
        "disponibilidad": "Disponibilidad",
        "rendimiento": "Rendimiento",
        "calidad": "Calidad",
        "scrap_rate": "Scrap",
        "energia_por_unidad_buena": "kWh/ud buena",
        "downtime_no_planificado_pct": "Downtime %",
        "mtbf_h": "MTBF",
        "mttr_min": "MTTR",
        "microparadas_por_100h": "Micro/100 h",
        "fallas_cortas_por_100h": "Fallas cortas/100 h",
    }
    corr = R["corr_pearson"].rename(index=labels, columns=labels)
    fig, ax = plt.subplots(figsize=(8.6, 7.0))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(corr.index)), corr.index, fontsize=8)
    for i in range(len(corr)):
        for j in range(len(corr)):
            value = corr.values[i, j]
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if abs(value) > 0.55 else "#222222")
    ax.set_title("Correlación de Pearson entre KPI (máquina-turno)")
    fig.colorbar(im, ax=ax, shrink=0.8, label="r")
    save_fig(fig, figures_dir / "F05_correlaciones.png")
    made.append("F05_correlaciones.png")

    # F06 dispersión
    fig, axes = plt.subplots(2, 2, figsize=(8.4, 6.4))
    panels = [
        ("rendimiento", "Rendimiento", "OEE"),
        ("calidad", "Calidad", "OEE"),
        ("scrap_rate", "Scrap rate", "OEE"),
        ("energia_por_unidad_buena", "kWh/unidad buena", "OEE"),
    ]
    for ax, (var, xlabel, ylabel) in zip(axes.ravel(), panels):
        sub = oee[[var, "oee"]].dropna()
        ax.scatter(sub[var], sub["oee"], s=4, alpha=0.22, color="#1f4e79", edgecolors="none")
        lr = stats.linregress(sub[var], sub["oee"])
        xs = np.linspace(sub[var].min(), sub[var].max(), 100)
        ax.plot(xs, lr.intercept + lr.slope * xs, color="#c0392b", lw=1.4)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(f"OEE vs {xlabel}  (r = {lr.rvalue:.2f}, n = {len(sub):,})".replace(",", "."))
    fig.suptitle("Relaciones bivariadas con el OEE", fontweight="bold")
    save_fig(fig, figures_dir / "F06_dispersion_oee.png")
    made.append("F06_dispersion_oee.png")

    # F07 QQ
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    stats.probplot(oee["oee"].dropna().values, dist="norm", plot=ax)
    ax.get_lines()[0].set_markersize(2.5)
    ax.get_lines()[0].set_alpha(0.4)
    ax.get_lines()[1].set_color("#c0392b")
    ax.set_title("QQ-plot del OEE (máquina-día)")
    ax.set_xlabel("Cuantiles teóricos")
    ax.set_ylabel("Cuantiles observados")
    save_fig(fig, figures_dir / "F07_qq_oee.png")
    made.append("F07_qq_oee.png")

    # F08 paradas por causa
    cats = unplanned["causa_categoria"].value_counts().index.tolist()
    cats = [c for c in cats if (unplanned["causa_categoria"] == c).sum() >= 10]
    data = [unplanned.loc[unplanned.causa_categoria == c, "duracion_min"].dropna().values for c in cats]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    bp = ax.boxplot(data, tick_labels=cats, patch_artist=True, showfliers=True,
                    flierprops=dict(marker=".", markersize=2, alpha=0.25, markerfacecolor="#555555", markeredgecolor="none"))
    for patch in bp["boxes"]:
        patch.set_facecolor("#8fa6b8")
        patch.set_alpha(0.7)
    ax.set_yscale("log")
    ax.set_title("Duración de paradas no planificadas por causa")
    ax.set_ylabel("Minutos (escala log)")
    for i, values in enumerate(data, start=1):
        ax.text(i, ax.get_ylim()[0] * 1.15, f"n={len(values):,}".replace(",", "."), ha="center", fontsize=7)
    save_fig(fig, figures_dir / "F08_paradas_por_causa.png")
    made.append("F08_paradas_por_causa.png")

    # F09 estabilidad
    maq = R["maquinas"]
    fig, ax = plt.subplots(figsize=(7.8, 5.0))
    for plant in PLANT_ORDER:
        sub = maq[maq.planta_codigo == plant]
        ax.scatter(sub["oee_media"], sub["cv"], s=np.clip(sub["downtime_min"] / 40, 15, 220),
                   color=PLANT_COLORS[plant], alpha=0.7, edgecolors="white", linewidth=0.5, label=plant)
    for _, row in maq.nsmallest(5, "oee_media").iterrows():
        ax.annotate(row["maquina_codigo"], (row["oee_media"], row["cv"]), textcoords="offset points",
                    xytext=(5, 4), fontsize=7)
    ax.set_xlabel("OEE medio (180 días)")
    ax.set_ylabel("Coeficiente de variación del OEE")
    ax.set_title("Mapa de estabilidad por máquina")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.1f}%"))
    ax.legend(fontsize=7)
    save_fig(fig, figures_dir / "F09_estabilidad_maquinas.png")
    made.append("F09_estabilidad_maquinas.png")

    # F10 turno x día
    turno = R["turno"]
    tmp = turno.groupby(["turno_codigo", "dia_semana"]).agg(
        plan=("tiempo_planificado_min", "sum"), op=("tiempo_operativo_min", "sum"),
        ideal=("minutos_ideales", "sum"), total=("total_count", "sum"), good=("good_count", "sum"),
    ).reset_index()
    tmp["oee"] = (tmp.op / tmp.plan) * (tmp.ideal / tmp.op) * (tmp.good / tmp.total)
    pivot = tmp.pivot(index="turno_codigo", columns="dia_semana", values="oee").reindex(columns=range(7))
    fig, ax = plt.subplots(figsize=(7.8, 3.0))
    im = ax.imshow(pivot.values, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(7), [SHIFT_LABELS[d] for d in range(7)])
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            value = pivot.values[i, j]
            if not np.isnan(value):
                ax.text(j, i, f"{value * 100:.1f}", ha="center", va="center", fontsize=8,
                        color="white" if value > np.nanmean(pivot.values) else "#222222")
    ax.set_title("OEE ponderado por turno y día de la semana (%)")
    fig.colorbar(im, ax=ax, shrink=0.8, label="OEE")
    save_fig(fig, figures_dir / "F10_turno_dia_semana.png")
    made.append("F10_turno_dia_semana.png")

    # F11 scrap por producto
    prod = R["scrap_producto"]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    y = np.arange(len(prod))
    ax.barh(y, prod["scrap_rate"], xerr=[prod["scrap_rate"] - prod["ic_low"], prod["ic_high"] - prod["scrap_rate"]],
            color="#c0392b", alpha=0.7, error_kw=dict(ecolor="#333333", lw=0.8, capsize=2))
    ax.set_yticks(y, prod["producto_codigo"])
    ax.set_xlabel("Scrap rate")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.1f}%"))
    ax.set_title("Scrap rate por producto (IC 95 % de Wilson)")
    ax.axvline(prod["scrap"].sum() / prod["total"].sum(), color="#111111", ls="--", lw=1, label="Global")
    ax.legend(fontsize=7)
    save_fig(fig, figures_dir / "F11_scrap_producto.png")
    made.append("F11_scrap_producto.png")

    # F12 temperatura
    temp = R["evento"]["temperatura_c"].dropna()
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.hist(temp, bins=60, color="#e69f00", edgecolor="white", linewidth=0.3)
    ax.axvline(85, color="#c0392b", ls="--", lw=1.4, label="Umbral 85 °C")
    ax.set_title("Distribución de temperatura de proceso")
    ax.set_xlabel("°C")
    ax.set_ylabel("Lecturas")
    above = (temp > 85).mean() * 100
    ax.text(0.99, 0.97, f"n = {len(temp):,}\n> 85 °C = {above:.1f} %".replace(",", "."),
            transform=ax.transAxes, ha="right", va="top", fontsize=7, bbox=dict(fc="white", ec="#cccccc", alpha=0.8))
    ax.legend(fontsize=7)
    save_fig(fig, figures_dir / "F12_temperatura.png")
    made.append("F12_temperatura.png")

    # F13 mantenimiento
    mant = R["mant"]
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    tipos = mant["tipo"].value_counts().index.tolist()
    data = [mant.loc[mant.tipo == t, "duracion_min"].dropna().values for t in tipos]
    bp = axes[0].boxplot(data, tick_labels=tipos, patch_artist=True, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor("#8fa6b8")
        patch.set_alpha(0.7)
    axes[0].set_title("Duración por tipo de mantenimiento")
    axes[0].set_ylabel("Minutos")
    axes[0].tick_params(axis="x", labelrotation=20)
    for t in tipos:
        sub = mant[mant.tipo == t]
        axes[1].scatter(sub["duracion_min"], sub["costo_estimado_usd"], s=8, alpha=0.4, label=t)
    axes[1].set_xlabel("Duración (min)")
    axes[1].set_ylabel("Coste estimado (USD)")
    axes[1].set_title("Coste vs duración por tipo")
    axes[1].legend(fontsize=7)
    save_fig(fig, figures_dir / "F13_mantenimiento.png")
    made.append("F13_mantenimiento.png")

    # F14 atípicos
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.0))
    out = R["outliers"][R["outliers"]["nivel"] == "máquina-día"].sort_values("pct_iqr")
    axes[0].barh(out["variable"], out["pct_iqr"], color="#c0392b", alpha=0.75)
    axes[0].set_xlabel("% de casos fuera de cercas IQR 1,5×")
    axes[0].set_title("Atípicos univariantes (máquina-día)")
    maha = R["mahalanobis"]
    axes[1].hist(maha["d2_all"], bins=50, color="#4C72B0", alpha=0.8)
    axes[1].axvline(maha["umbral"], color="#c0392b", ls="--", lw=1.4, label=f"Umbral χ² 97,5 % = {maha['umbral']:.2f}")
    axes[1].set_title(f"Distancia de Mahalanobis (A, P, Q)\n{maha['n_atipicos']} atípicos ({maha['pct_atipicos']:.2f} %)")
    axes[1].set_xlabel("Distancia")
    axes[1].set_ylabel("Casos")
    axes[1].legend(fontsize=7)
    save_fig(fig, figures_dir / "F14_atipicos.png")
    made.append("F14_atipicos.png")

    # F15 latencia y señal
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0))
    lat = R["latencia_eventos"]
    axes[0].hist(lat, bins=20, color="#1f4e79", edgecolor="white", linewidth=0.4)
    axes[0].axvline(lat.quantile(0.95), color="#c0392b", ls="--", lw=1.2, label=f"p95 = {lat.quantile(0.95):.1f} ms")
    axes[0].set_title("Latencia de pipeline (eventos sim-*)")
    axes[0].set_xlabel("ms")
    axes[0].set_ylabel("Eventos")
    axes[0].legend(fontsize=7)
    senal = R["senal"]
    lecturas = R["senal_df"]["lecturas"].value_counts().sort_index()
    positions = np.arange(len(lecturas))
    axes[1].bar(positions, lecturas.values, color="#8fa6b8")
    axes[1].set_xticks(positions, [str(int(x)) for x in lecturas.index])
    for i, value in enumerate(lecturas.values):
        axes[1].text(i, value, f"{value:,}".replace(",", "."), ha="center", va="bottom", fontsize=7)
    axes[1].set_title("Lecturas de proceso por máquina-día")
    axes[1].set_xlabel("Lecturas (2 por turno + excursiones)")
    axes[1].set_ylabel("Máquina-día")
    save_fig(fig, figures_dir / "F15_latencia_senal.png")
    made.append("F15_latencia_senal.png")

    # F16 Pareto causas
    unplanned_cat = R["categorias_parada"].query("~es_planificada").sort_values("minutos", ascending=False)
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.bar(unplanned_cat["causa_categoria"], unplanned_cat["minutos"], color="#c0392b", alpha=0.75)
    ax.set_ylabel("Minutos de downtime")
    ax.tick_params(axis="x", labelrotation=15)
    ax2 = ax.twinx()
    cum = unplanned_cat["minutos"].cumsum() / unplanned_cat["minutos"].sum() * 100
    ax2.plot(unplanned_cat["causa_categoria"], cum, color="#111111", marker="o", ms=3, lw=1.2)
    ax2.set_ylabel("% acumulado")
    ax2.set_ylim(0, 105)
    ax.set_title("Pareto de downtime no planificado por causa")
    save_fig(fig, figures_dir / "F16_pareto_causas.png")
    made.append("F16_pareto_causas.png")

    # F17 energía por perfil
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    perfiles = [p for p in oee["perfil_rendimiento"].dropna().unique()]
    perfiles.sort(key=lambda p: oee.loc[oee.perfil_rendimiento == p, "energia_por_unidad_buena"].median())
    data = [oee.loc[oee.perfil_rendimiento == p, "energia_por_unidad_buena"].dropna().values for p in perfiles]
    bp = ax.boxplot(data, tick_labels=perfiles, patch_artist=True, showfliers=False)
    for patch in bp["boxes"]:
        patch.set_facecolor("#e69f00")
        patch.set_alpha(0.65)
    ax.set_title("Energía por unidad buena según perfil de máquina")
    ax.set_ylabel("kWh / unidad buena")
    ax.tick_params(axis="x", labelrotation=15)
    save_fig(fig, figures_dir / "F17_energia_perfil.png")
    made.append("F17_energia_perfil.png")

    # F18 ventanas móviles
    diario = R["diario"].set_index("fecha")
    fig, axes = plt.subplots(3, 1, figsize=(8.4, 6.6), sharex=True)
    for ax, var, title, fmt in zip(
        axes,
        ["oee", "scrap_rate", "downtime_pct"],
        ["OEE (media móvil 30 d)", "Scrap rate (media móvil 30 d)", "Downtime no planificado (media móvil 30 d)"],
        ["{:.0%}", "{:.1%}", "{:.1%}"],
    ):
        series = diario[var].rolling(30, min_periods=20).mean()
        ax.plot(series.index, series.values, color="#1f4e79", lw=1.6)
        ax.set_title(title)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
        ax.set_ylabel("")
    axes[-1].set_xlabel("Fecha")
    save_fig(fig, figures_dir / "F18_ventanas_30d.png")
    made.append("F18_ventanas_30d.png")

    return made


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------


def write_report(R: dict, path: Path, run_id: str, fig_names: list[str]) -> None:
    res = R["resumen"]
    desc = R["desc_global"]
    L: list[str] = []
    A = L.append

    A("# Análisis estadístico exploratorio — MetalNova Smart Factory BI")
    A("")
    A("> **Todos los datos son sintéticos.** Este informe describe el dataset generado para el")
    A("> prototipo académico, no telemetría de una fábrica real. El escenario `calibracion` fue")
    A("> diseñado para mostrar señal (OEE ≈ 78 → 66 %). Las correlaciones son asociaciones")
    A("> descriptivas: **no implican causalidad**.")
    A("")
    A(f"**Incremento:** 008 · **Ventana:** {WINDOW_LABEL} (180 días) · **Corrida:** `{run_id}`")
    A("")
    A("---")
    A("")

    A("## 1. Resumen ejecutivo")
    A("")
    A(f"- Se analizaron **{n_es(res['n_machine_day'])}** registros máquina-día, "
      f"**{n_es(res['n_shifts'])}** máquina-turno, **{n_es(res['n_stops'])}** paradas consolidadas "
      f"y **{n_es(res['n_events'])}** eventos históricos.")
    A(f"- **OEE ponderado** del periodo: **{pct_es(res['oee_ponderado'])}**. En la distribución por "
      f"máquina-día, media **{pct_es(res['oee_media'])}**, mediana **{pct_es(res['oee_mediana'])}**, "
      f"sd **{num_es(res['oee_sd'] * 100, 2)} pp** y rango "
      f"{pct_es(res['oee_min'])}–{pct_es(res['oee_max'])}.")
    A(f"- El componente más asociado al OEE es **{res['oee_corr_top_var']}** "
      f"(r = {num_es(res['oee_corr_top_r'], 3)}); la disponibilidad tiene poca varianza y actúa casi como techo.")
    A(f"- **{res['planta_grupo_min']}** presenta la mediana de OEE más baja "
      f"({pct_es(res['planta_mediana_min'])}) frente a **{res['planta_grupo_max']}** "
      f"({pct_es(res['planta_mediana_max'])}); Kruskal–Wallis {p_text(res['planta_test_p'])}, "
      f"ε² = {num_es(res['planta_test_eps2'], 3)}.")
    A(f"- **{n_es(res['outliers_oee_n'])}** máquina-día ({pct_es(res['outliers_oee_pct'] / 100)}) quedan "
      "fuera de las cercas IQR 1,5× del OEE; se clasifican y no se eliminan.")
    A(f"- La tendencia lineal del OEE es **{signed_es(res['tendencia_pendiente_30d'] * 100, 2)} pp por 30 días** "
      f"(R² = {num_es(res['tendencia_r2'], 2)}); las primeras 30 jornadas promedian "
      f"{pct_es(res['ventana_oee_inicio'])} y las últimas {pct_es(res['ventana_oee_fin'])}.")
    A(f"- La causa no planificada con más minutos es **{res['causa_top']}** "
      f"({pct_es(res['causa_top_share'] / 100, 1)} del downtime no planificado).")
    A(f"- Calidad de datos: **{res['controles_error']}** controles con fallas; latencia p95 de los eventos "
      f"`sim-*` = **{num_es(res['latencia_p95'], 1)} ms**.")
    A("")
    A("La lectura de negocio es consistente con el resto del proyecto: la pérdida dominante es de")
    A("**rendimiento**, P-SUR concentra el peor desempeño y la energía por unidad buena se mueve en")
    A("sentido contrario al OEE. Este incremento aporta la evidencia estadística y su incertidumbre.")
    A("")

    A("## 2. Datos, fuentes y método")
    A("")
    A("### 2.1 Inventario")
    A("")
    inv = R["inventario"].copy()
    inv.columns = ["Objeto", "Tipo", "Filas totales", "En ventana"]
    inv["Filas totales"] = inv["Filas totales"].map(n_es)
    inv["En ventana"] = inv["En ventana"].map(lambda v: "—" if pd.isna(v) else n_es(v))
    order = {"hecho": 0, "dimensión": 1, "cuarentena": 2}
    inv["_orden"] = inv["Tipo"].map(order).fillna(3)
    inv = inv.sort_values(["_orden", "Objeto"]).drop(columns="_orden")
    A("**Tabla T01. Inventario de fuentes y recuentos.**")
    A("")
    A(md_table(inv))
    A("")
    A("**Fuente de cada bloque:** los KPI y ratios se leen de las vistas `v_kpi_*` (contrato analítico);")
    A("las duraciones, costes y eventos se leen de los hechos; las dimensiones solo agrupan. No se")
    A("recalcula un KPI en Python si ya existe una vista validada.")
    A("")
    A("### 2.2 Filtros y exclusiones")
    A("")
    A(f"- Ventana: `{WINDOW_LABEL}`, definida por `id_tiempo`/`fecha`.")
    A(f"- Paradas consolidadas analizadas: **{n_es(R['parada_resumen']['episodios_consolidados'])}** "
      f"({n_es(R['parada_resumen']['con_solape'])} con solape; "
      f"{n_es(R['parada_resumen']['minutos_solapados'])} min solapados).")
    A("- Se excluyen del análisis principal las **24 paradas** y **51 eventos** de la ingesta simulada")
    A("  (`Ingesta 004:%`, `run_id LIKE 'sim-%'`), todos del 2026-10-22 y fuera de la ventana. Se usan")
    A("  solo en latencia y calidad IoT. Los **2 eventos rechazados** son artefactos de la prueba G5.")
    A("- Los atípicos **no se eliminan**: se cuantifican y se contextualizan.")
    A("")
    A("### 2.3 Niveles de análisis")
    A("")
    A("| Nivel | n | Uso principal |")
    A("|---|---:|---|")
    A(f"| Fila de producción | {n_es(len(R['data']['produccion']))} | conteos y energía por orden |")
    A(f"| Máquina-día | {n_es(len(R['oee_dia']))} | distribuciones, atípicos y comparaciones |")
    A(f"| Máquina-turno | {n_es(len(R['turno']))} | correlación con MTBF/MTTR y turnos |")
    A(f"| Planta-día | {n_es(len(R['data']['oee_planta']))} | serie temporal y ventanas |")
    A(f"| Máquina agregada | {n_es(len(R['maquinas']))} | estabilidad y ranking |")
    A("")

    A("## 3. Calidad de datos")
    A("")
    ctrl = R["controles"].copy()
    ctrl = ctrl.rename(columns={"control": "Control", "fallas": "Fallas", "total": "Registros", "estado": "Estado"})
    ctrl["Fallas"] = ctrl["Fallas"].map(n_es)
    ctrl["Registros"] = ctrl["Registros"].map(n_es)
    ctrl = ctrl.sort_values("Control")
    A("**Tabla T02. Controles de integridad y duplicados.**")
    A("")
    A(md_table(ctrl))
    A("")
    nulos = R["nulos"].copy()
    nulos["pct_nulos"] = nulos["pct_nulos"].map(lambda v: pct_es(v / 100))
    nulos["n"] = nulos["n"].map(n_es)
    nulos["Nulos"] = nulos["nulos"].map(n_es)
    nulos = nulos[["nivel", "variable", "n", "Nulos", "pct_nulos", "nota"]]
    nulos.columns = ["Nivel", "Variable", "n", "Nulos", "% nulos", "Nota"]
    A("**Tabla T03. Nulos por variable clave.**")
    A("")
    A(md_table(nulos))
    A("")
    A("Los `NULL` de MTBF, MTTR y FPY son **esperados** por la definición del KPI (sin fallas, sin")
    A("reparaciones o sin inspecciones) y no se imputan. No se detectaron duplicados ni violaciones")
    A("de invariantes en la ventana analizada.")
    A("")
    senal = R["senal"].copy()
    senal.columns = ["Estado", "Máquina-día", "Lecturas", "Faltantes", "%", "Cumple cadencia"]
    senal["Máquina-día"] = senal["Máquina-día"].map(n_es)
    senal["Lecturas"] = senal["Lecturas"].map(n_es)
    senal["Faltantes"] = senal["Faltantes"].map(n_es)
    senal["%"] = senal["%"].map(lambda v: pct_es(v / 100))
    senal["Cumple cadencia"] = senal["Cumple cadencia"].map(lambda v: "—" if pd.isna(v) else pct_es(v, 1))
    A("**Tabla T04. Cobertura de señal IoT.**")
    A("")
    A(md_table(senal[["Estado", "Máquina-día", "Lecturas", "Faltantes", "%", "Cumple cadencia"]]))
    A("")
    A("La cadencia de 15 min no se cumple porque el feed sintético emite dos lecturas por turno;")
    A("se reporta como diagnóstico y no se rellena con *carry-forward* (D-022). El feed produce 6, 9")
    A("o 12 lecturas por máquina-día y un hueco máximo de 210 min entre lecturas; todos los")
    A("máquina-día quedaron en estado `ok`. La distribución se muestra en la figura F15.")
    A("")
    A("![Latencia y señal](analysis/figures/F15_latencia_senal.png)")
    A("")
    A("**Figura F15.** Latencia de pipeline de los eventos `sim-*` y lecturas de proceso por máquina-día. "
      "Fuente: `fact_evento` y `v_calidad_senal_iot`.")
    A("")

    A("## 4. Estadística descriptiva")
    A("")
    A("**Tabla T05. Descriptivos globales por nivel y variable.**")
    A("")
    d = desc.copy()
    d["pct_nulos"] = d["pct_nulos"].map(lambda v: f"{v:.2f} %")
    d = d[["nivel", "variable", "n", "media", "mediana", "sd", "cv", "min", "q1", "q3", "iqr", "max", "asimetria", "curtosis"]]
    d.columns = ["Nivel", "Variable", "n", "Media", "Mediana", "SD", "CV", "Mín", "Q1", "Q3", "IQR", "Máx", "Asim.", "Curt."]
    A(md_table(d, dec=4))
    A("")
    A("La tabla anterior usa la distribución de las **filas**, no el KPI ponderado. Por eso la media")
    A("de OEE (72 %) difiere del OEE ponderado global, que es el valor válido para el tablero.")
    A("")
    A("**Tabla T06. OEE y componentes por planta (máquina-día).**")
    A("")
    dp = R["desc_planta"].copy()
    def fmt_media(row):
        if row["variable"] == "energia_por_unidad_buena":
            return num_es(row["media"], 4) + " kWh"
        return pct_es(row["media"])

    def fmt_sd(row):
        if row["variable"] == "energia_por_unidad_buena":
            return num_es(row["sd"], 4) + " kWh"
        return pct_es(row["sd"]).replace(" %", " pp")

    def fmt_mediana(row):
        if row["variable"] == "energia_por_unidad_buena":
            return f"{num_es(row['mediana'], 4)} kWh [{num_es(row['mediana_ic_low'], 4)}; {num_es(row['mediana_ic_high'], 4)}]"
        return f"{pct_es(row['mediana'])} [{pct_es(row['mediana_ic_low'])}; {pct_es(row['mediana_ic_high'])}]"

    dp["media"] = dp.apply(fmt_media, axis=1)
    dp["sd"] = dp.apply(fmt_sd, axis=1)
    dp["mediana_ic"] = dp.apply(fmt_mediana, axis=1)
    dp = dp[["variable", "grupo", "n", "media", "sd", "mediana_ic"]]
    dp.columns = ["Variable", "Planta", "n", "Media", "SD", "Mediana [IC 95 %]"]
    A(md_table(dp))
    A("")
    A("El intervalo de confianza de la mediana se obtuvo por bootstrap percentil (2.000 réplicas).")
    A("")

    A("## 5. Distribuciones y normalidad")
    A("")
    A("**Tabla T07. Pruebas de normalidad.**")
    A("")
    norm = R["normalidad"].copy()
    norm = norm[["nivel", "variable", "n", "asimetria", "curtosis", "dagostino_stat", "dagostino_p", "shapiro_p", "veredicto"]]
    norm.columns = ["Nivel", "Variable", "n", "Asimetría", "Curtosis", "D'Agostino", "p D'Agostino", "p Shapiro", "Veredicto"]
    A(md_table(norm, dec=4))
    A("")
    A("Con n grande, D'Agostino detecta desviaciones mínimas de la normalidad; el QQ-plot y la")
    A("asimetría son más informativos. El OEE presenta una cola izquierda moderada: unos pocos")
    A("máquina-día muy por debajo del grueso de la distribución.")
    A("")
    if "F01_histograma_oee.png" in fig_names:
        A(f"![Distribución del OEE](analysis/figures/F01_histograma_oee.png)")
        A("")
        A("**Figura F01.** Histograma del OEE por máquina-día con mediana y cercas IQR 1,5×. Fuente: `v_kpi_oee_maquina_dia`; "
          f"n = {n_es(len(R['oee_dia']))}.")
        A("")
        A(f"![OEE por planta](analysis/figures/F02_oee_por_planta.png)")
        A("")
        A("**Figura F02.** OEE por planta; la caja muestra Q1–Q3 y la mediana. Fuente: `v_kpi_oee_maquina_dia`.")
        A("")
        A(f"![Componentes por planta](analysis/figures/F03_componentes_por_planta.png)")
        A("")
        A("**Figura F03.** Disponibilidad, rendimiento y calidad por planta. Fuente: `v_kpi_oee_maquina_dia`.")
        A("")
        A(f"![QQ-plot](analysis/figures/F07_qq_oee.png)")
        A("")
        A("**Figura F07.** QQ-plot del OEE frente a una normal. Fuente: `v_kpi_oee_maquina_dia`.")
        A("")

    A("## 6. Valores atípicos")
    A("")
    A("Se aplican cuatro criterios: IQR 1,5×, IQR 3× (extremos), z-score |z|>3 y z-score")
    A("modificado (MAD) > 3,5. Un valor atípico no es un error: puede ser una máquina crítica, un")
    A("cambio de producto o un evento de demo. El análisis los **clasifica**, no los borra.")
    A("")
    out = R["outliers"].copy()
    out["pct_iqr"] = out["pct_iqr"].map(lambda v: pct_es(v / 100))
    out["pct_extremo"] = out["pct_extremo"].map(lambda v: pct_es(v / 100))
    out["pct_z3"] = out["pct_z3"].map(lambda v: pct_es(v / 100))
    out["pct_mad"] = out["pct_mad"].map(lambda v: pct_es(v / 100))
    out = out[["nivel", "variable", "n", "n_iqr", "pct_iqr", "n_extremo", "pct_extremo", "n_z3", "pct_z3", "n_mad", "pct_mad"]]
    out.columns = ["Nivel", "Variable", "n", "n IQR", "% IQR", "n extremos", "% extremos", "n z>3", "% z>3", "n MAD", "% MAD"]
    A("**Tabla T08. Atípicos por variable y método.**")
    A("")
    A(md_table(out))
    A("")
    maha = R["mahalanobis"]
    A(f"En el plano multivariante (A, P, Q), **{n_es(maha['n_atipicos'])}** de {n_es(maha['n'])} "
      f"máquina-día ({pct_es(maha['pct_atipicos'] / 100)}) superan la distancia de Mahalanobis con "
      f"umbral χ² 97,5 % ({num_es(maha['umbral'], 2)}). La disponibilidad casi constante hace que el "
      "plano esté dominado por rendimiento y calidad: el porcentaje mide cola conjunta, no 548 errores.")
    A("")
    top = R["outliers_top"].head(12).copy()
    top["valor"] = top["valor"].map(lambda v: num_es(v, 4))
    top["z"] = top["z"].map(lambda v: signed_es(v, 2))
    top["z_mod"] = top["z_mod"].map(lambda v: "—" if pd.isna(v) else signed_es(v, 2))
    top = top[["nivel", "variable", "valor", "z", "z_mod", "contexto"]]
    top.columns = ["Nivel", "Variable", "Valor", "z", "z modificado", "Contexto"]
    A("**Tabla T09. Casos atípicos más extremos (|z| > 3).**")
    A("")
    A(md_table(top))
    A("")
    A(f"![Atípicos](analysis/figures/F14_atipicos.png)")
    A("")
    A("**Figura F14.** Porcentaje de atípicos univariantes y distribución de la distancia de Mahalanobis. Fuente: `v_kpi_oee_maquina_dia`.")
    A("")
    A("**Lectura.** Los atípicos de OEE se concentran en máquinas con perfil `critica` y en días con")
    A("paradas largas o scrap elevado; son señal operativa, no ruido de captura. La tabla T09 permite")
    A("auditar cada caso con su fecha, máquina, planta y tipo.")
    A("")
    A("![Estabilidad por máquina](analysis/figures/F09_estabilidad_maquinas.png)")
    A("")
    A("**Figura F09.** OEE medio frente al coeficiente de variación por máquina; el tamaño del punto")
    A("representa el downtime acumulado. Fuente: `v_kpi_oee_maquina_dia` (52 máquinas).")
    A("")

    A("## 7. Correlación")
    A("")
    corr = R["correlaciones"].copy()
    oee_corr = corr[(corr.var1 == "oee") | (corr.var2 == "oee")].copy()
    oee_corr["otra"] = np.where(oee_corr.var1 == "oee", oee_corr.var2, oee_corr.var1)
    oee_corr = oee_corr.reindex(oee_corr["pearson_r"].abs().sort_values(ascending=False).index)
    oee_corr = oee_corr[["otra", "n", "pearson_r", "pearson_ic_low", "pearson_ic_high", "pearson_p_fdr", "spearman_r", "fuerza"]]
    oee_corr.columns = ["Variable", "n", "Pearson r", "IC 95 % inf.", "IC 95 % sup.", "p (FDR)", "Spearman ρ", "Fuerza"]
    A("**Tabla T10. Correlación del OEE con el resto de KPI (máquina-turno).**")
    A("")
    A(md_table(oee_corr, dec=4))
    A("")
    A("Se corrigió por comparaciones múltiples con Benjamini–Hochberg sobre todos los pares. Con")
    A("n = 28.080, un p-valor pequeño no implica una relación fuerte: por eso se reporta r, su IC y")
    A("la etiqueta de fuerza. La matriz completa está en `data/analysis/<run_id>/correlaciones.csv`.")
    A("")
    A("**Identidades contables.** Las correlaciones disponibilidad–downtime % ≈ −1 y calidad–scrap")
    A("≈ −1 no son hallazgos empíricos: se derivan de la definición (`downtime % = 1 − A`,")
    A("`scrap = 1 − Q`). Se muestran para completar la matriz, no como evidencia independiente.")
    A("")
    A(f"![Correlaciones](analysis/figures/F05_correlaciones.png)")
    A("")
    A("**Figura F05.** Matriz de Pearson entre KPI a nivel máquina-turno. Fuente: `v_kpi_oee_maquina_turno` + `v_kpi_mantenimiento_maquina_turno`.")
    A("")
    A(f"![Dispersión](analysis/figures/F06_dispersion_oee.png)")
    A("")
    A("**Figura F06.** OEE frente a rendimiento, calidad, scrap y energía por unidad buena. Fuente: `v_kpi_oee_maquina_dia`.")
    A("")
    A("**Advertencia de nivel.** La correlación agregada a 52 máquinas puede cambiar de signo o de")
    A("magnitud respecto a la de máquina-turno (falacia ecológica). La matriz por máquina está en")
    A("`correlaciones_maquina.csv` y se usa solo como contraste.")
    A("")

    A("## 8. Comparaciones por grupo y asociaciones")
    A("")
    tests = R["pruebas"].copy()
    tests["anova_p"] = tests["anova_p"].map(p_es)
    tests["kruskal_p"] = tests["kruskal_p"].map(p_es)
    tests["levene_p"] = tests["levene_p"].map(p_es)

    def fmt_group_median(row, key):
        if row["variable"] == "energia_por_unidad_buena":
            return num_es(row[key], 4) + " kWh"
        if row["variable"] == "mtbf_h":
            return num_es(row[key], 2) + " h"
        if row["variable"] == "mttr_min":
            return num_es(row[key], 1) + " min"
        return pct_es(row[key])

    tests["mediana_min"] = tests.apply(lambda r: fmt_group_median(r, "mediana_min"), axis=1)
    tests["mediana_max"] = tests.apply(lambda r: fmt_group_median(r, "mediana_max"), axis=1)
    tests = tests[["variable", "factor", "n", "grupo_min", "mediana_min", "grupo_max", "mediana_max", "anova_p", "kruskal_p", "levene_p", "eta2", "epsilon2"]]
    tests.columns = ["Variable", "Factor", "n", "Grupo menor", "Mediana menor", "Grupo mayor", "Mediana mayor", "p ANOVA", "p Kruskal", "p Levene", "η²", "ε²"]
    A("**Tabla T11. Comparaciones por grupo.**")
    A("")
    A(md_table(tests, dec=4))
    A("")
    asc = R["asociaciones"].copy()
    asc["p"] = asc["p"].map(p_es)
    asc["chi2"] = asc["chi2"].map(lambda v: num_es(v, 1))
    asc["v_cramer"] = asc["v_cramer"].map(lambda v: num_es(v, 3))
    asc = asc[["asociacion", "n", "chi2", "gl", "p", "v_cramer", "fuerza"]]
    asc.columns = ["Asociación", "n", "χ²", "gl", "p", "V de Cramér", "Fuerza"]
    A("**Tabla T12. Asociaciones categóricas.**")
    A("")
    A(md_table(asc))
    A("")
    A("El post-hoc de Mann–Whitney con corrección de Holm está en `pruebas_grupo.csv`. Se reporta")
    A("η²/ε² porque con n grande la significancia sola no distingue un efecto relevante de uno trivial.")
    A("")
    A("Las medianas de OEE, rendimiento, calidad, scrap y downtime se expresan como proporción")
    A("(0–1); las de MTBF y MTTR, en horas y minutos. El **MTBF de máquina-turno es de corto plazo**")
    A("(runtime del turno / fallas del turno) y no equivale al MTBF agregado de 180 días (~85,7 h),")
    A("que se calcula con `SUM(runtime) / SUM(fallas)`.")
    A("")

    A("## 9. Evolución temporal")
    A("")
    trend = R["tendencia"].copy()
    pct_metrics = {"oee", "disponibilidad", "rendimiento", "calidad", "scrap_rate", "downtime_pct"}

    def fmt_slope(row):
        if row["metrica"] in pct_metrics:
            return signed_es(row["pendiente_30d"] * 100, 2) + " pp"
        return signed_es(row["pendiente_30d"], 4) + " kWh"

    trend["pendiente_30d"] = trend.apply(fmt_slope, axis=1)
    trend["r2"] = trend["r2"].map(lambda v: num_es(v, 3))
    trend["p"] = trend["p"].map(p_es)
    trend["mk_tau"] = trend["mk_tau"].map(lambda v: "—" if pd.isna(v) else signed_es(v, 3))
    trend["mk_p"] = trend["mk_p"].map(lambda v: "—" if pd.isna(v) else p_es(v))
    trend = trend[["metrica", "n", "pendiente_30d", "r2", "p", "mk_tau", "mk_p"]]
    trend.columns = ["Métrica", "n", "Pendiente / 30 d", "R²", "p (OLS)", "τ Mann–Kendall", "p (MK)"]
    A("**Tabla T13. Tendencia lineal y Mann–Kendall sobre la serie diaria ponderada.**")
    A("")
    A(md_table(trend))
    A("")
    win = R["ventanas"].copy()

    def fmt_window(row, key):
        if row["metrica"] == "kWh/unidad buena":
            return num_es(row[key], 4) + " kWh"
        return pct_es(row[key])

    def fmt_delta(row):
        if row["metrica"] == "kWh/unidad buena":
            return signed_es(row["delta_abs"], 4) + " kWh"
        return signed_es(row["delta_abs"] * 100, 2) + " pp"

    win["primeros_30"] = win.apply(lambda r: fmt_window(r, "primeros_30"), axis=1)
    win["ultimos_30"] = win.apply(lambda r: fmt_window(r, "ultimos_30"), axis=1)
    win["delta_abs"] = win.apply(fmt_delta, axis=1)
    win["delta_pct"] = win["delta_pct"].map(lambda v: signed_es(v, 1) + " %")
    win = win[["metrica", "primeros_30", "ultimos_30", "delta_abs", "delta_pct"]]
    win.columns = ["Métrica", "Primeros 30 días", "Últimos 30 días", "Δ absoluto", "Δ relativo"]
    A("**Tabla T14. Comparación de las primeras y últimas 30 jornadas (ponderado).**")
    A("")
    A(md_table(win))
    A("")
    A(f"![Serie OEE](analysis/figures/F04_serie_oee.png)")
    A("")
    A("**Figura F04.** Serie diaria del OEE, media móvil de 7 días y tendencia; por planta. Fuente: `v_kpi_oee_planta_dia`.")
    A("")
    A(f"![Ventanas 30 días](analysis/figures/F18_ventanas_30d.png)")
    A("")
    A("**Figura F18.** Medias móviles de 30 días de OEE, scrap y downtime. Fuente: `v_kpi_oee_planta_dia`.")
    A("")
    acf = R["autocorrelacion"]
    A(f"La autocorrelación lag-1 del OEE diario es **{num_es(acf.iloc[0]['r'], 3)}**; el detalle de los "
      "14 rezagos está en `autocorrelacion.csv`. Hay persistencia temporal, por lo que los días no son")
    A("independientes y las pruebas que suponen independencia deben leerse con cautela.")
    A("")
    A("**Nota sobre la ventana:** el análisis se define por `id_tiempo`; el turno C del 18-10 puede")
    A("tener `event_time` del 19-10 por el cruce de medianoche. No es un dato fuera de ventana.")
    A("")

    A("## 10. Análisis categórico")
    A("")
    cat = R["categorias_parada"].copy()
    cat["es_planificada"] = cat["es_planificada"].map({True: "planificada", False: "no planificada"})
    cat["share_minutos"] = cat["share_minutos"].map(lambda v: pct_es(v / 100, 1))
    cat["dur_media"] = cat["dur_media"].map(lambda v: num_es(v, 1))
    cat["dur_mediana"] = cat["dur_mediana"].map(lambda v: num_es(v, 1))
    cat = cat[["causa_categoria", "es_planificada", "n", "minutos", "dur_media", "dur_mediana", "share_minutos"]]
    cat.columns = ["Causa", "Tipo", "Episodios", "Minutos", "Duración media", "Duración mediana", "% minutos"]
    A("**Tabla T15. Paradas por categoría de causa.**")
    A("")
    A(md_table(cat))
    A("")
    A("El `% minutos` se calcula **dentro de cada tipo**: planificadas sobre el total planificado y no")
    A("planificadas sobre el total no planificado. No se suman entre sí.")
    A("")
    A(f"![Paradas por causa](analysis/figures/F08_paradas_por_causa.png)")
    A("")
    A("**Figura F08.** Distribución de duración de paradas no planificadas por causa (escala log). Fuente: `v_parada_consolidada`.")
    A("")
    A(f"![Pareto](analysis/figures/F16_pareto_causas.png)")
    A("")
    A("**Figura F16.** Pareto de minutos de downtime no planificado por causa. Fuente: `v_parada_consolidada`.")
    A("")
    prod = R["scrap_producto"].copy()
    prod["scrap_rate"] = prod["scrap_rate"].map(pct_es)
    prod["ic"] = prod.apply(lambda r: f"[{pct_es(r['ic_low'])}; {pct_es(r['ic_high'])}]", axis=1)
    prod["total"] = prod["total"].map(n_es)
    prod["scrap"] = prod["scrap"].map(n_es)
    prod = prod[["producto_codigo", "familia_nombre", "total", "scrap", "scrap_rate", "ic"]]
    prod.columns = ["Producto", "Familia", "Unidades", "Scrap", "Scrap rate", "IC 95 %"]
    A("**Tabla T16. Scrap rate por producto con IC de Wilson.**")
    A("")
    A(md_table(prod))
    A("")
    A(f"![Scrap por producto](analysis/figures/F11_scrap_producto.png)")
    A("")
    A("**Figura F11.** Scrap rate por producto con IC 95 % de Wilson. Fuente: `v_kpi_calidad_producto_dia`.")
    A("")
    mant = R["mantenimiento_tipo"].copy()
    mant["dur_media"] = mant["dur_media"].map(lambda v: num_es(v, 1))
    mant["dur_mediana"] = mant["dur_mediana"].map(lambda v: num_es(v, 1))
    mant["coste_total"] = mant["coste_total"].map(lambda v: num_es(v, 2))
    mant["coste_medio"] = mant["coste_medio"].map(lambda v: num_es(v, 2))
    mant = mant[["tipo", "n", "minutos", "dur_media", "dur_mediana", "coste_total", "coste_medio"]]
    mant.columns = ["Tipo", "Órdenes", "Minutos", "Duración media", "Duración mediana", "Coste total", "Coste medio"]
    A("**Tabla T17. Mantenimiento por tipo.**")
    A("")
    A(md_table(mant))
    A("")
    A(f"![Mantenimiento](analysis/figures/F13_mantenimiento.png)")
    A("")
    A("**Figura F13.** Duración por tipo y relación coste–duración. Fuente: `fact_mantenimiento`.")
    A("")
    A(f"![Turno y día](analysis/figures/F10_turno_dia_semana.png)")
    A("")
    A("**Figura F10.** OEE ponderado por turno y día de la semana. Fuente: `v_kpi_oee_maquina_turno`.")
    A("")
    A("![Temperatura](analysis/figures/F12_temperatura.png)")
    A("")
    A("**Figura F12.** Distribución de temperatura de proceso y umbral de 85 °C. Fuente: `fact_evento`;")
    A("n = 58.776 lecturas con temperatura.")
    A("")
    A(f"![Energía por perfil](analysis/figures/F17_energia_perfil.png)")
    A("")
    A("**Figura F17.** Energía por unidad buena según perfil de máquina. Fuente: `v_kpi_oee_maquina_dia` + `dim_maquina`.")
    A("")

    A("## 11. Hallazgos y lectura")
    A("")
    A("1. **El rendimiento es el componente dominante.** La correlación OEE–rendimiento es muy alta;")
    A("   la disponibilidad está cerca de 99 % y apenas discrimina. La palanca no es solo “parar")
    A("   menos”, sino “producir más unidades por minuto operativo”.")
    A("2. **P-SUR concentra el problema y además es más volátil.** Tiene la mediana de OEE más baja y")
    A("   la mayor dispersión; sus casos atípicos son los que más pesan en la cola izquierda.")
    A("3. **La energía por unidad buena se mueve en contra del OEE.** El perfil `energia` y las")
    A("   máquinas con más scrap se asocian con un mayor consumo específico; es un indicador de")
    A("   eficiencia, no solo de costo.")
    A("4. **Las paradas son de cola larga.** La mediana de una parada no planificada es de 3 min y")
    A("   la media de 3,3 min, pero el máximo llega a 135 min: hay muchas microparadas cortas y")
    A("   pocas fallas largas. Analizar solo promedios ocultaría la microparada, que concentra el")
    A("   71,8 % de los minutos no planificados.")
    A("5. **La tendencia es real pero no monolítica.** Hay caída sostenida del OEE, con persistencia")
    A("   temporal; el tramo final no es un salto aislado. La comparación de ventanas de 30 días")
    A("   cuantifica el deterioro sin depender de un único punto.")
    A("6. **Los atípicos son operativos, no errores.** M-047 (`critica`) y los días con paradas")
    A("   largas explican los casos extremos; el informe los deja trazados para revisión.")
    A("")
    A("Estos hallazgos son **descriptivos** y complementan el plan de mejora (007). No demuestran")
    A("causalidad ni justifican por sí solos una inversión: para eso haría falta un diseño")
    A("experimental o un análisis causal con supuestos explícitos.")
    A("")

    A("## 12. Limitaciones")
    A("")
    A("- **Datos sintéticos.** El escenario `calibracion` está diseñado para mostrar señal; no es una")
    A("  medición de una fábrica real.")
    A("- **Significancia inflada.** Con decenas de miles de filas, diferencias triviales resultan")
    A("  significativas. Se reportan tamaños de efecto, IC y FDR, pero el lector debe priorizar la")
    A("  magnitud sobre el p-valor.")
    A("- **Dependencia temporal.** La autocorrelación del OEE diario invalida supuestos de")
    A("  independencia en pruebas sobre la serie.")
    A("- **Niveles de agregación.** Las correlaciones por fila y por máquina no son intercambiables.")
    A("- **Disponibilidad en techo.** Su baja varianza limita cualquier correlación e impide leerla")
    A("  como palanca principal.")
    A("- **Cobertura IoT.** Dos lecturas por turno; la cadencia de 15 min se reporta como diagnóstico.")
    A("- **Exclusiones.** Las 24 paradas y 51 eventos `sim-*` quedan fuera del análisis principal por")
    A("  estar fuera de la ventana; su inclusión no cambiaría las conclusiones, pero mezclaría")
    A("  procesos generadores distintos.")
    A("")

    A("## 13. Reproducibilidad")
    A("")
    A("```powershell")
    A("docker compose build ingestor")
    A("docker compose --profile tools run --rm ingestor python src/analyze_data.py --seed 42")
    A("docker compose --profile tools run --rm ingestor python src/validate_analysis.py")
    A("docker compose exec -T db psql -U metalinova -d metalinova -f /sql/validation/08_analisis.sql")
    A("```")
    A("")
    A(f"Corrida `{run_id}`. El manifiesto con versiones, filtros, recuentos y SHA-256 de cada salida")
    A("está en `data/analysis/<run_id>/manifest.json` y su copia versionada en")
    A("`docs/analysis/manifest.json`. Las figuras están en `docs/analysis/figures/`.")
    A("")
    A("**Paquetes:** pandas, numpy, scipy y matplotlib con versión fija en")
    A("`python/requirements-analysis.txt`; se instalan en la imagen del ingestor.")
    A("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    log.info("informe %s", path)


# ---------------------------------------------------------------------------
# Salidas y manifiesto
# ---------------------------------------------------------------------------


def write_outputs(R: dict, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    frames = {
        "inventario.csv": R["inventario"],
        "controles.csv": R["controles"],
        "nulos.csv": R["nulos"],
        "descriptivos_global.csv": R["desc_global"],
        "descriptivos_planta.csv": R["desc_planta"],
        "normalidad.csv": R["normalidad"],
        "outliers.csv": R["outliers"],
        "outliers_top.csv": R["outliers_top"],
        "mahalanobis_top.csv": R["mahalanobis"]["top"].reset_index(drop=True),
        "correlaciones.csv": R["correlaciones"],
        "correlaciones_maquina.csv": R["corr_maquina"].reset_index(),
        "pruebas_grupo.csv": R["pruebas"],
        "asociaciones.csv": R["asociaciones"],
        "tendencia.csv": R["tendencia"],
        "autocorrelacion.csv": R["autocorrelacion"],
        "ventanas_30d.csv": R["ventanas"],
        "categorias_parada.csv": R["categorias_parada"],
        "mantenimiento_tipo.csv": R["mantenimiento_tipo"],
        "scrap_producto.csv": R["scrap_producto"],
        "senal_iot.csv": R["senal"],
        "latencia.csv": pd.DataFrame([R["latencia"]]),
        "inventario_maquinas.csv": R["maquinas"],
    }
    written = []
    for name, frame in frames.items():
        path = outdir / name
        frame.to_csv(path, index=False, encoding="utf-8")
        written.append(path)
    (outdir / "resumen.json").write_text(
        json.dumps(R["resumen"], ensure_ascii=False, indent=2, default=float), encoding="utf-8"
    )
    written.append(outdir / "resumen.json")
    return written


def build_manifest(
    run_id: str,
    start: date,
    end: date,
    seed: int,
    outputs: list[Path],
    figures: list[Path],
    report: Path,
    duration_s: float,
    counts: dict,
) -> dict:
    packages = {}
    for name in ("pandas", "numpy", "scipy", "matplotlib", "psycopg"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    files = []
    for path in outputs + figures + [report]:
        files.append(
            {
                "archivo": str(path).replace("\\", "/"),
                "bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256(path) if path.exists() else None,
            }
        )
    return {
        "run_id": run_id,
        "version": VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "ventana": {"inicio": start.isoformat(), "fin": end.isoformat(), "dias": (end - start).days + 1},
        "filtros": {
            "eventos": "run_id LIKE 'hist-%'",
            "paradas_excluidas": "causa_detalle NOT LIKE 'Ingesta 004:%'",
            "eventos_sim": "solo latencia y calidad IoT",
            "rechazados": "reportados aparte",
        },
        "niveles": counts,
        "python": platform.python_version(),
        "plataforma": platform.platform(),
        "paquetes": packages,
        "duracion_s": round(duration_s, 2),
        "memoria_pico_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "salidas": files,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    t0 = time.perf_counter()
    root = Path(os.environ.get("METALNOVA_ROOT", "/app"))
    data_dir = root / "data" / "analysis"
    docs_dir = Path(args.docs_dir) if args.docs_dir else root / "docs"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    fingerprint = hashlib.sha256(f"{args.start}{args.end}{args.seed}{VERSION}".encode()).hexdigest()[:6]
    run_id = args.run_id or f"eda-{stamp}-{fingerprint}"
    setup_logging(root / "logs", run_id)
    log.info("inicio run_id=%s ventana=%s→%s seed=%s", run_id, args.start, args.end, args.seed)
    if args.end < args.start:
        log.error("la fecha final es anterior a la inicial")
        return 2
    try:
        with connect() as conn:
            data = load_all(conn, args.start, args.end)
        R = analyse(data, args.seed)
        outdir = data_dir / run_id
        outputs = write_outputs(R, outdir)
        log.info("tablas escritas en %s (%d archivos)", outdir, len(outputs))

        figures: list[Path] = []
        fig_names: list[str] = []
        if not args.skip_figures:
            figures_dir = docs_dir / "analysis" / "figures"
            fig_names = make_figures(R, figures_dir)
            figures = [figures_dir / name for name in fig_names]
        else:
            figures_dir = docs_dir / "analysis" / "figures"
            fig_names = sorted(p.name for p in figures_dir.glob("F*.png"))

        report = docs_dir / "ANALISIS_DATOS.md"
        write_report(R, report, run_id, fig_names)

        manifest = build_manifest(
            run_id,
            args.start,
            args.end,
            args.seed,
            outputs,
            figures,
            report,
            time.perf_counter() - t0,
            {
                "maquina_dia": int(len(R["oee_dia"])),
                "maquina_turno": int(len(R["turno"])),
                "planta_dia": int(len(R["data"]["oee_planta"])),
                "maquinas": int(len(R["maquinas"])),
                "paradas_consolidadas": int(len(R["parada"])),
                "eventos_hist": int(len(R["evento"])),
            },
        )
        (outdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        copy_dir = docs_dir / "analysis"
        copy_dir.mkdir(parents=True, exist_ok=True)
        (copy_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("manifiesto %s", outdir / "manifest.json")
        log.info("fin run_id=%s duración=%.1f s pico=%.1f MB", run_id, manifest["duracion_s"], manifest["memoria_pico_mb"])
        print(json.dumps(R["resumen"], ensure_ascii=False, indent=2, default=float))
        return 0
    except Exception as exc:  # noqa: BLE001
        log.exception("fallo del análisis: %s: %s", type(exc).__name__, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
