"""Genera el histórico sintético de 180 días (incremento 003).

Uso típico dentro del contenedor:

    docker compose run --rm ingestor python src/generate_history.py --seed 42

Salidas:

    data/raw/dim_orden.csv
    data/raw/fact_produccion.csv
    data/raw/fact_parada.csv
    data/raw/fact_mantenimiento.csv
    data/raw/fact_calidad.csv
    data/raw/fact_evento.csv
    data/processed/manifest.json

Los datos son **sintéticos**. El manifiesto registra semilla, parámetros,
recuentos, tamaños, duración y memoria máxima. Para el escenario
``calibracion`` también registra los factores de planta, los perfiles de
máquina y la degradación usada, de modo que la corrida sea auditable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from common.catalog import load_catalog
from common.db import connect
from common.simulation import (
    HistoryGenerator,
    SimParams,
    calibration_manifest,
)

UTC = timezone.utc
VERSION = "1.1.0"
DEFAULT_SEED = 42
DEFAULT_DAYS = 180
DEFAULT_SCENARIO = "degradado"
DEFAULT_INTENSITY = 1.0


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"fecha inválida: {value}") from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera el histórico sintético de MetalNova (CSV + manifiesto)."
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="semilla (default: 42)")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="días a generar (default: 180)")
    parser.add_argument(
        "--end-date",
        type=_iso_date,
        default=None,
        help="último día del histórico (default: ayer, hora UTC)",
    )
    parser.add_argument(
        "--escenario",
        choices=("base", "degradado", "calibracion"),
        default=DEFAULT_SCENARIO,
        help="escenario de degradación (default: degradado)",
    )
    parser.add_argument(
        "--intensidad",
        type=float,
        default=DEFAULT_INTENSITY,
        help="multiplicador de fallas/microparadas/temperatura (default: 1.0)",
    )
    parser.add_argument(
        "--plantas",
        type=int,
        default=3,
        help="número de plantas a incluir (default: 3)",
    )
    parser.add_argument(
        "--maquinas",
        type=int,
        default=52,
        help="número máximo de máquinas a incluir (default: 52)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw"),
        help="directorio de los CSV (default: data/raw)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/processed/manifest.json"),
        help="ruta del manifiesto (default: data/processed/manifest.json)",
    )
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> tuple[date, date]:
    if args.days < 1:
        raise SystemExit("--days debe ser >= 1")
    if args.seed < 0:
        raise SystemExit("--seed debe ser >= 0")
    if args.intensidad <= 0:
        raise SystemExit("--intensidad debe ser > 0")
    if args.plantas < 1:
        raise SystemExit("--plantas debe ser >= 1")
    if args.maquinas < 1:
        raise SystemExit("--maquinas debe ser >= 1")

    end_date = args.end_date or (date.today() - timedelta(days=1))
    start_date = end_date - timedelta(days=args.days - 1)
    return start_date, end_date


def _run_tag(args: argparse.Namespace, start_date: date, end_date: date) -> str:
    parts = [
        VERSION,
        str(args.seed),
        str(args.days),
        start_date.isoformat(),
        end_date.isoformat(),
        args.escenario,
        f"{args.intensidad:.4f}",
        str(args.plantas),
        str(args.maquinas),
    ]
    if args.escenario == "calibracion":
        # La configuración forma parte de la identidad de la corrida: dos
        # calibraciones con factores distintos no pueden compartir run_id.
        parts.append(
            json.dumps(
                calibration_manifest(),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    raw = "|".join(parts)
    return "h" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


def _print_summary(manifest: dict) -> None:
    print()
    print("Histórico sintético generado")
    print("=" * 68)
    print(f"run_id:       {manifest['run_id']}")
    print(f"semilla:      {manifest['params']['seed']}")
    print(f"escenario:    {manifest['params']['escenario']}")
    print(f"rango:        {manifest['coverage']['start_date']} → {manifest['coverage']['end_date']}")
    print(f"días:         {manifest['coverage']['days']}")
    print(f"máquinas:     {manifest['catalog']['maquinas']}")
    print(f"duración:     {manifest['duration_seconds']} s")
    print(f"memoria pico: {manifest['peak_memory_mb']} MB")
    print()
    print(f"{'tabla':<26}{'filas':>12}{'bytes':>14}")
    print("-" * 68)
    for item in manifest["files"]:
        print(f"{item['name']:<26}{item['rows']:>12,}{item['bytes']:>14,}".replace(",", "."))
    print("-" * 68)
    print(f"{'eventos de origen':<26}{manifest['total_source_events']:>12,}".replace(",", "."))
    print(f"OEE 7 primeros días: {manifest['oee_first_7d']}")
    print(f"OEE 7 últimos días:  {manifest['oee_last_7d']}")
    print()
    print("Siguiente paso: python src/load_history.py")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    start_date, end_date = _validate_args(args)
    run_tag = _run_tag(args, start_date, end_date)

    params = SimParams(
        seed=args.seed,
        days=args.days,
        start_date=start_date,
        end_date=end_date,
        escenario=args.escenario,
        intensidad=args.intensidad,
    )

    with connect() as conn:
        catalog = load_catalog(
            conn,
            start_date=start_date,
            end_date=end_date,
            max_plantas=args.plantas,
            max_maquinas=args.maquinas,
        )

    generator = HistoryGenerator(
        catalog=catalog,
        params=params,
        output_dir=args.output_dir,
        run_tag=run_tag,
    )
    summary = generator.run()

    manifest = {
        "version": VERSION,
        "generator": "generate_history.py",
        "created_at": datetime.now(UTC).isoformat(),
        "run_id": generator.run_id,
        "run_tag": run_tag,
        "params": {
            "seed": args.seed,
            "days": args.days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "escenario": args.escenario,
            "intensidad": args.intensidad,
            "plantas": args.plantas,
            "maquinas": args.maquinas,
            "run_tag": run_tag,
        },
        "catalog": {
            "plantas": len(catalog.plantas),
            "lineas": len(catalog.lineas),
            "maquinas": len(catalog.maquinas),
            "turnos": len(catalog.turnos),
            "familias": len(catalog.familias),
            "productos": len(catalog.productos),
            "causas": len(catalog.causas),
            "tecnicos": len(catalog.tecnicos),
            "dias_calendario": len(catalog.dias),
        },
        "coverage": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": args.days,
        },
        **summary,
    }
    if args.escenario == "calibracion":
        manifest["calibracion"] = calibration_manifest()

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _print_summary(manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
