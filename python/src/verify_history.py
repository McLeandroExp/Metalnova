"""Verifica el histórico cargado en PostgreSQL (incremento 003).

Comprueba recuento mínimo, cobertura temporal, coherencia de fechas, claves
huérfanas y reglas de clasificación de paradas. Sale con código 1 si alguna
comprobación falla.

Uso:

    docker compose run --rm ingestor python src/verify_history.py

La fuente de verdad de las reglas es ``specs/CONSTITUTION.md`` y los criterios
``AC-301`` a ``AC-307`` del incremento 003.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common.db import connect


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verifica el histórico sintético cargado.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/processed/manifest.json"),
        help="manifiesto de generación (default: data/processed/manifest.json)",
    )
    parser.add_argument(
        "--min-eventos",
        type=int,
        default=200_000,
        help="mínimo de eventos de origen (default: 200000)",
    )
    return parser.parse_args(argv)


def _scalar(cur, sql: str):
    cur.execute(sql)
    return cur.fetchone()[0]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    expected_days = 180
    manifest_run = None
    if args.manifest.exists():
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        expected_days = int(manifest.get("coverage", {}).get("days", expected_days))
        manifest_run = manifest.get("run_id")

    tables = (
        "dim_orden",
        "fact_produccion",
        "fact_parada",
        "fact_mantenimiento",
        "fact_calidad",
        "fact_evento",
    )

    checks: list[tuple[str, str, bool]] = []
    with connect() as conn, conn.cursor() as cur:
        print("Recuentos por tabla")
        print("=" * 72)
        counts = {}
        for table in tables:
            counts[table] = _scalar(cur, f"SELECT count(*) FROM {table}")
            print(f"{table:<26}{counts[table]:>14,}".replace(",", "."))

        print()
        print("Cobertura temporal (fechas de producción)")
        print("=" * 72)
        cur.execute(
            "SELECT min(t.fecha), max(t.fecha), count(DISTINCT t.fecha) "
            "FROM fact_produccion f JOIN dim_tiempo t ON t.id_tiempo = f.id_tiempo"
        )
        start_date, end_date, distinct_days = cur.fetchone()
        print(f"desde: {start_date}  hasta: {end_date}  días distintos: {distinct_days}")

        if manifest_run:
            cur.execute(
                "SELECT DISTINCT run_id FROM fact_evento WHERE run_id IS NOT NULL"
            )
            db_runs = sorted(row[0] for row in cur.fetchall())
            checks.append(
                (
                    "Manifiesto y base comparten el mismo run_id",
                    f"base={db_runs} manifiesto={manifest_run}",
                    db_runs == [manifest_run],
                )
            )

        checks.append(
            (
                f"AC-301 eventos de origen >= {args.min_eventos}",
                f"fact_evento={counts['fact_evento']}",
                counts["fact_evento"] >= args.min_eventos,
            )
        )
        checks.append(
            (
                f"AC-302 cobertura exacta de {expected_days} días",
                f"días distintos={distinct_days}",
                int(distinct_days) == expected_days,
            )
        )

        date_checks = {
            "fact_produccion": "SELECT count(*) FROM fact_produccion WHERE fin_at < inicio_at",
            "fact_parada": (
                "SELECT count(*) FROM fact_parada "
                "WHERE fin_at IS NOT NULL AND fin_at < inicio_at"
            ),
            "fact_mantenimiento": (
                "SELECT count(*) FROM fact_mantenimiento "
                "WHERE fin_at IS NOT NULL AND fin_at < inicio_at"
            ),
        }
        for table, sql in date_checks.items():
            value = _scalar(cur, sql)
            checks.append((f"AC-303 {table}: fin < inicio", str(value), value == 0))

        negative_sql = """
            SELECT count(*) FROM fact_produccion
            WHERE total_count < 0 OR good_count < 0 OR scrap_count < 0
               OR good_count > total_count OR scrap_count > total_count
               OR tiempo_operativo_min < 0 OR energia_kwh < 0
        """
        value = _scalar(cur, negative_sql)
        checks.append(("AC-304 fact_produccion: cantidades/tiempos inválidos", str(value), value == 0))

        orphan_sql = {
            "fact_produccion → dim_orden": (
                "SELECT count(*) FROM fact_produccion f "
                "LEFT JOIN dim_orden o ON o.id_orden = f.id_orden "
                "WHERE o.id_orden IS NULL"
            ),
            "fact_produccion → dim_maquina": (
                "SELECT count(*) FROM fact_produccion f "
                "LEFT JOIN dim_maquina m ON m.id_maquina = f.id_maquina "
                "WHERE m.id_maquina IS NULL"
            ),
            "fact_parada → dim_maquina": (
                "SELECT count(*) FROM fact_parada f "
                "LEFT JOIN dim_maquina m ON m.id_maquina = f.id_maquina "
                "WHERE m.id_maquina IS NULL"
            ),
            "fact_parada → dim_causa": (
                "SELECT count(*) FROM fact_parada f "
                "LEFT JOIN dim_causa c ON c.id_causa = f.id_causa "
                "WHERE c.id_causa IS NULL"
            ),
            "fact_calidad → dim_producto": (
                "SELECT count(*) FROM fact_calidad f "
                "LEFT JOIN dim_producto p ON p.id_producto = f.id_producto "
                "WHERE p.id_producto IS NULL"
            ),
            "fact_evento → dim_maquina": (
                "SELECT count(*) FROM fact_evento f "
                "LEFT JOIN dim_maquina m ON m.id_maquina = f.id_maquina "
                "WHERE f.id_maquina IS NOT NULL AND m.id_maquina IS NULL"
            ),
        }
        for label, sql in orphan_sql.items():
            value = _scalar(cur, sql)
            checks.append((f"AC-307 {label}: huérfanos", str(value), value == 0))

        micro = _scalar(
            cur, "SELECT count(*) FROM fact_parada WHERE es_microparada AND duracion_min >= 5"
        )
        checks.append(("Regla: microparada con duración < 5 min", str(micro), micro == 0))

        both = _scalar(
            cur,
            "SELECT count(*) FROM fact_parada WHERE es_planificada AND es_microparada",
        )
        checks.append(("Regla: planificada y microparada a la vez", str(both), both == 0))

        unclassified = _scalar(
            cur,
            "SELECT count(*) FROM fact_parada "
            "WHERE NOT es_planificada AND NOT es_microparada "
            "AND duracion_min < 5 AND id_mantenimiento IS NULL",
        )
        checks.append(
            ("Regla: parada corta sin CMMS clasificada como falla", str(unclassified), unclassified == 0)
        )

        duplicates = _scalar(
            cur,
            "SELECT count(*) FROM ("
            "  SELECT source_system, source_event_id FROM fact_evento "
            "  GROUP BY source_system, source_event_id HAVING count(*) > 1"
            ") d",
        )
        checks.append(("fact_evento: duplicados de source_event_id", str(duplicates), duplicates == 0))

        print()
        print("Comprobaciones")
        print("=" * 72)
        failed = 0
        for name, detail, ok in checks:
            verdict = "OK" if ok else "FALLA"
            if not ok:
                failed += 1
            print(f"[{verdict}] {name}: {detail}")

        print()
        print(f"run_id en manifiesto: {manifest_run}")
        print(f"resultado: {len(checks) - failed}/{len(checks)} comprobaciones OK")
        return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
