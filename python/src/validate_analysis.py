"""Validación independiente del análisis estadístico (incremento 008).

Recalcula en SQL los recuentos, estadísticos y correlaciones que el análisis
calculó en Python, y los compara con los CSV de la última corrida. También
verifica que las figuras referenciadas existan y que los SHA-256 del manifiesto
coincidan con los archivos en disco.

Uso dentro del contenedor:

    docker compose --profile tools run --rm ingestor python src/validate_analysis.py
    docker compose --profile tools run --rm ingestor python src/validate_analysis.py --run-dir data/analysis/eda-...

Tolerancia: 1e-9 relativa para estadísticos y correlaciones; exacta para conteos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import pandas as pd

from common.db import connect

ROOT = Path(os.environ.get("METALNOVA_ROOT", "/app"))
DATA_DIR = ROOT / "data" / "analysis"
DOCS_DIR = ROOT / "docs"
TOL = 1e-9


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida el análisis 008 contra SQL.")
    parser.add_argument("--run-dir", default=None, help="carpeta de la corrida (default: la última)")
    return parser.parse_args(argv)


def latest_run() -> Path:
    candidates = sorted(
        [p for p in DATA_DIR.glob("eda-*") if (p / "manifest.json").exists()],
        key=lambda p: (p / "manifest.json").stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(f"No hay corridas en {DATA_DIR}")
    return candidates[-1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare(label: str, expected: float, observed: float, tol: float = TOL) -> bool:
    if expected is None or observed is None:
        return False
    if isinstance(expected, float) and math.isnan(expected):
        return False
    if math.isclose(float(expected), float(observed), rel_tol=tol, abs_tol=1e-12):
        print(f"  OK    {label:<52} análisis={float(expected):.12g}  sql={float(observed):.12g}")
        return True
    print(f"  ERROR {label:<52} análisis={float(expected):.12g}  sql={float(observed):.12g}")
    return False


def compare_int(label: str, expected: int, observed: int) -> bool:
    if int(expected) == int(observed):
        print(f"  OK    {label:<52} {int(expected)}")
        return True
    print(f"  ERROR {label:<52} análisis={int(expected)}  sql={int(observed)}")
    return False


def fetch_one(conn, sql: str):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_dir = Path(args.run_dir) if args.run_dir else latest_run()
    if not run_dir.is_absolute():
        run_dir = ROOT / run_dir
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    start = manifest["ventana"]["inicio"]
    end = manifest["ventana"]["fin"]
    print(f"Validación del análisis 008 — corrida {manifest['run_id']}")
    print(f"Ventana {start} → {end}; salidas en {run_dir}\n")

    desc = pd.read_csv(run_dir / "descriptivos_global.csv")
    corr = pd.read_csv(run_dir / "correlaciones.csv")
    checks: list[bool] = []

    with connect() as conn:
        print("1. Recuentos y niveles")
        counts = {
            "maquina_dia": f"""
                SELECT count(*) FROM v_kpi_oee_maquina_dia
                WHERE fecha BETWEEN DATE '{start}' AND DATE '{end}'
            """,
            "maquina_turno": f"""
                SELECT count(*) FROM v_kpi_oee_maquina_turno
                WHERE fecha BETWEEN DATE '{start}' AND DATE '{end}'
            """,
            "planta_dia": f"""
                SELECT count(*) FROM v_kpi_oee_planta_dia
                WHERE fecha BETWEEN DATE '{start}' AND DATE '{end}'
            """,
            "paradas_consolidadas": f"""
                SELECT count(*) FROM v_parada_consolidada
                WHERE id_tiempo BETWEEN {start.replace('-', '')} AND {end.replace('-', '')}
                  AND causa_detalle NOT LIKE 'Ingesta 004:%'
            """,
            "eventos_hist": """
                SELECT count(*) FROM fact_evento WHERE run_id LIKE 'hist-%'
            """,
        }
        for key, sql in counts.items():
            observed = int(fetch_one(conn, sql)[0])
            checks.append(compare_int(f"{key}", manifest["niveles"][key], observed))

        print("\n2. Estadísticos descriptivos (máquina-día)")
        variables = [
            "disponibilidad",
            "rendimiento",
            "calidad",
            "oee",
            "scrap_rate",
            "energia_por_unidad_buena",
            "downtime_no_planificado_pct",
        ]
        for var in variables:
            row = desc[(desc["nivel"] == "máquina-día") & (desc["variable"] == var)].iloc[0]
            sql = f"""
                SELECT avg({var})::float8,
                       percentile_cont(0.5) WITHIN GROUP (ORDER BY {var})::float8,
                       stddev_samp({var})::float8,
                       count({var})
                FROM v_kpi_oee_maquina_dia
                WHERE fecha BETWEEN DATE '{start}' AND DATE '{end}'
            """
            avg, med, sd, n = fetch_one(conn, sql)
            checks.append(compare_int(f"{var}.n", int(row["n"]), int(n)))
            checks.append(compare(f"{var}.media", row["media"], avg))
            checks.append(compare(f"{var}.mediana", row["mediana"], med))
            checks.append(compare(f"{var}.sd", row["sd"], sd))

        print("\n3. Correlaciones (máquina-turno)")
        pairs = [
            ("oee", "rendimiento"),
            ("oee", "calidad"),
            ("oee", "scrap_rate"),
            ("oee", "energia_por_unidad_buena"),
            ("oee", "downtime_no_planificado_pct"),
        ]
        for a, b in pairs:
            row = corr[((corr.var1 == a) & (corr.var2 == b)) | ((corr.var1 == b) & (corr.var2 == a))].iloc[0]
            sql = f"""
                SELECT corr({a}, {b})::float8,
                       count(*) FILTER (WHERE {a} IS NOT NULL AND {b} IS NOT NULL)
                FROM v_kpi_oee_maquina_turno
                WHERE fecha BETWEEN DATE '{start}' AND DATE '{end}'
            """
            r, n = fetch_one(conn, sql)
            checks.append(compare_int(f"corr({a},{b}).n", int(row["n"]), int(n)))
            checks.append(compare(f"corr({a},{b})", row["pearson_r"], r))

        print("\n4. Paradas y temperatura")
        stop_row = desc[(desc["nivel"] == "parada no planificada") & (desc["variable"] == "duracion_min")].iloc[0]
        sql = f"""
            SELECT avg(p.duracion_min)::float8,
                   percentile_cont(0.5) WITHIN GROUP (ORDER BY p.duracion_min)::float8,
                   max(p.duracion_min)::float8,
                   count(*)::float8
            FROM v_parada_consolidada p
            WHERE p.id_tiempo BETWEEN {start.replace('-', '')} AND {end.replace('-', '')}
              AND p.causa_detalle NOT LIKE 'Ingesta 004:%'
              AND p.es_planificada = false
        """
        avg, med, mx, n = fetch_one(conn, sql)
        checks.append(compare_int("parada_no_planificada.n", int(stop_row["n"]), int(n)))
        checks.append(compare("parada_no_planificada.media", stop_row["media"], avg))
        checks.append(compare("parada_no_planificada.mediana", stop_row["mediana"], med))
        checks.append(compare("parada_no_planificada.max", stop_row["max"], mx))

        temp_row = desc[(desc["nivel"] == "evento IoT") & (desc["variable"] == "temperatura_c")].iloc[0]
        sql = """
            SELECT avg(temperatura_c)::float8,
                   stddev_samp(temperatura_c)::float8,
                   max(temperatura_c)::float8,
                   count(temperatura_c)::float8
            FROM fact_evento
            WHERE run_id LIKE 'hist-%' AND temperatura_c IS NOT NULL
        """
        avg, sd, mx, n = fetch_one(conn, sql)
        checks.append(compare_int("temperatura.n", int(temp_row["n"]), int(n)))
        checks.append(compare("temperatura.media", temp_row["media"], avg))
        checks.append(compare("temperatura.sd", temp_row["sd"], sd))
        checks.append(compare("temperatura.max", temp_row["max"], mx))

    print("\n5. Salidas y manifiesto")
    report = DOCS_DIR / "ANALISIS_DATOS.md"
    if report.exists() and report.stat().st_size > 0:
        print(f"  OK    informe {report.relative_to(ROOT)} ({report.stat().st_size} bytes)")
        checks.append(True)
        text = report.read_text(encoding="utf-8")
        referenced = sorted(set(part for part in text.split("analysis/figures/")[1:]))
        missing = []
        for tail in referenced:
            name = tail.split(")")[0]
            if name.endswith(".png") and not (DOCS_DIR / "analysis" / "figures" / name).exists():
                missing.append(name)
        if missing:
            print(f"  ERROR figuras referenciadas no encontradas: {', '.join(missing)}")
            checks.append(False)
        else:
            print(f"  OK    todas las figuras referenciadas existen ({len(referenced)} referencias)")
            checks.append(True)
    else:
        print("  ERROR falta docs/ANALISIS_DATOS.md")
        checks.append(False)

    hash_ok = 0
    hash_bad = []
    for entry in manifest.get("salidas", []):
        path = Path(entry["archivo"])
        if not path.exists():
            hash_bad.append(f"{path.name}: ausente")
            continue
        if sha256(path) == entry["sha256"]:
            hash_ok += 1
        else:
            hash_bad.append(f"{path.name}: hash distinto")
    if hash_bad:
        print(f"  ERROR manifiesto SHA-256: {len(hash_bad)} problemas")
        for item in hash_bad[:10]:
            print(f"        - {item}")
        checks.append(False)
    else:
        print(f"  OK    SHA-256 del manifiesto coincide en {hash_ok} archivos")
        checks.append(True)

    total = len(checks)
    passed = sum(checks)
    print(f"\nResultado: {passed}/{total} comprobaciones OK")
    if passed != total:
        print("VEREDICTO: ERROR")
        return 1
    print("VEREDICTO: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
