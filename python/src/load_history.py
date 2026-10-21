"""Carga por lotes del histórico sintético en PostgreSQL (incremento 003).

Lee los CSV y el manifiesto producidos por ``generate_history.py`` y carga las
tablas en el orden que respeta las claves foráneas. Es idempotente para una
misma ``run_id``: ``ON CONFLICT DO NOTHING`` evita duplicados.

Si la base ya contiene datos de otra ejecución, el script se detiene y pide
``--reset`` de forma explícita. Nunca borra datos en silencio.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import resource
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path

from common.db import connect

UTC = timezone.utc
DEFAULT_BATCH_SIZE = 10_000


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...]
    insert_sql: str
    extra_temp: tuple[str, ...] = ()


def _standard_insert(name: str, columns: tuple[str, ...]) -> str:
    cols = ", ".join(columns)
    return (
        f"INSERT INTO {name} ({cols}) "
        f"SELECT {cols} FROM {{tmp}} "
        "ON CONFLICT DO NOTHING"
    )


def _build_specs() -> tuple[TableSpec, ...]:
    dim_orden = (
        "id_orden",
        "codigo_orden",
        "id_producto",
        "cantidad_planificada",
        "fecha_plan",
        "estado",
    )
    mantenimiento = (
        "codigo_orden_trabajo",
        "id_maquina",
        "id_tecnico",
        "id_causa",
        "id_turno",
        "id_tiempo",
        "tipo",
        "inicio_at",
        "fin_at",
        "duracion_min",
        "costo_estimado_usd",
        "estado",
    )
    parada = (
        "id_maquina",
        "id_turno",
        "id_tiempo",
        "id_causa",
        "codigo_orden_trabajo",
        "inicio_at",
        "fin_at",
        "duracion_min",
        "es_planificada",
        "es_microparada",
        "causa_detalle",
    )
    produccion = (
        "id_orden",
        "id_maquina",
        "id_producto",
        "id_turno",
        "id_tiempo",
        "inicio_at",
        "fin_at",
        "tiempo_calendario_min",
        "tiempo_planificado_min",
        "downtime_planificado_min",
        "tiempo_operativo_min",
        "downtime_no_planificado_min",
        "total_count",
        "good_count",
        "scrap_count",
        "ciclo_ideal_segundos",
        "energia_kwh",
    )
    calidad = (
        "codigo_inspeccion",
        "codigo_lote",
        "id_maquina",
        "id_producto",
        "id_turno",
        "id_tiempo",
        "id_causa",
        "inspeccion_at",
        "unidades_inspeccionadas",
        "unidades_buenas",
        "unidades_defectuosas",
        "unidades_retrabajo",
        "es_retrabajo",
    )
    evento = (
        "source_system",
        "source_event_id",
        "tipo_evento",
        "id_maquina",
        "event_time",
        "generated_at",
        "run_id",
        "estado",
        "temperatura_c",
        "energia_kwh",
        "payload",
    )

    parada_insert = """
        INSERT INTO fact_parada (
            id_maquina, id_turno, id_tiempo, id_causa, id_mantenimiento,
            inicio_at, fin_at, duracion_min, es_planificada, es_microparada,
            causa_detalle
        )
        SELECT
            t.id_maquina, t.id_turno, t.id_tiempo, t.id_causa, m.id_mantenimiento,
            t.inicio_at, t.fin_at, t.duracion_min, t.es_planificada,
            t.es_microparada, t.causa_detalle
        FROM {tmp} t
        LEFT JOIN fact_mantenimiento m
               ON m.codigo_orden_trabajo = t.codigo_orden_trabajo
        ON CONFLICT DO NOTHING
    """

    return (
        TableSpec("dim_orden", dim_orden, _standard_insert("dim_orden", dim_orden)),
        TableSpec(
            "fact_mantenimiento",
            mantenimiento,
            _standard_insert("fact_mantenimiento", mantenimiento),
        ),
        TableSpec(
            "fact_parada",
            parada,
            parada_insert,
            extra_temp=("codigo_orden_trabajo text",),
        ),
        TableSpec(
            "fact_produccion",
            produccion,
            _standard_insert("fact_produccion", produccion),
        ),
        TableSpec("fact_calidad", calidad, _standard_insert("fact_calidad", calidad)),
        TableSpec("fact_evento", evento, _standard_insert("fact_evento", evento)),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Carga por lotes el histórico sintético en PostgreSQL."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/raw"),
        help="directorio con los CSV (default: data/raw)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/processed/manifest.json"),
        help="manifiesto de la generación (default: data/processed/manifest.json)",
    )
    parser.add_argument(
        "--load-manifest",
        type=Path,
        default=Path("data/processed/load_manifest.json"),
        help="salida con métricas de carga (default: data/processed/load_manifest.json)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"filas por lote (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="vacía los hechos y dim_orden antes de cargar (acción explícita y destructiva)",
    )
    return parser.parse_args(argv)


def _peak_memory_mb() -> float:
    try:
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    except (AttributeError, ValueError):  # pragma: no cover - fuera de Linux
        return 0.0


def _table_count(cur, table: str) -> int:
    cur.execute(f"SELECT count(*) FROM {table}")
    return int(cur.fetchone()[0])


def _check_run(conn, run_tag: str, reset: bool) -> list[str]:
    """Detecta ejecuciones presentes, incluso si la carga quedó a medias.

    Se miran los `run_id` de `fact_evento` y, además, el prefijo de
    `dim_orden.codigo_orden` (formato ``ORD-<run_tag>-...``). Así una carga
    interrumpida antes de insertar eventos tampoco se mezcla con otra ejecución.
    """
    with conn.cursor() as cur:
        # Los run_id de la ingesta simulada (`sim-`) no son ejecuciones del
        # histórico y no deben bloquear una recarga (incremento 004).
        cur.execute(
            "SELECT DISTINCT run_id FROM fact_evento WHERE run_id LIKE 'hist-%'"
        )
        tags = set()
        for row in cur.fetchall():
            value = row[0]
            tags.add(value[5:] if value.startswith("hist-") else value)

        cur.execute(
            "SELECT DISTINCT split_part(codigo_orden, '-', 2) "
            "FROM dim_orden WHERE codigo_orden LIKE 'ORD-%'"
        )
        tags.update(row[0] for row in cur.fetchall() if row[0])

    others = sorted(tag for tag in tags if tag != run_tag)
    if others and not reset:
        joined = ", ".join(others)
        raise SystemExit(
            "La base ya contiene datos de otra ejecución "
            f"({joined}).\n"
            "Para reemplazarlos de forma explícita usa --reset. "
            "Este script no borra datos en silencio."
        )
    return sorted(tags)


def _reset_tables(conn) -> None:
    tables = (
        "fact_produccion",
        "fact_parada",
        "fact_calidad",
        "fact_mantenimiento",
        "fact_evento",
        "dim_orden",
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT " + ", ".join(f"(SELECT count(*) FROM {t})" for t in tables)
        )
        before = cur.fetchone()
        print("Recuentos antes de --reset: " + ", ".join(
            f"{table}={count}" for table, count in zip(tables, before)
        ))
        cur.execute(
            "TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE"
        )
    conn.commit()
    print("Tablas de hechos y dim_orden vaciadas (--reset).")


def _load_chunk(conn, spec: TableSpec, chunk: list[list[str]]) -> int:
    tmp = f"tmp_{spec.name}"
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {tmp}")
            # WITH NO DATA copia columnas y tipos, pero no defaults: así el COPY
            # no consume secuencias de los bigserial de la tabla real.
            cur.execute(
                f"CREATE TEMP TABLE {tmp} ON COMMIT DROP "
                f"AS SELECT * FROM {spec.name} WITH NO DATA"
            )
            for definition in spec.extra_temp:
                cur.execute(f"ALTER TABLE {tmp} ADD COLUMN {definition}")

            cols = ", ".join(spec.columns)
            # psycopg3 serializa write_row() en formato texto (tabulado). Para
            # COPY ... FORMAT csv se envía el lote ya serializado con csv.writer.
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            for row in chunk:
                writer.writerow(row)
            with cur.copy(
                f"COPY {tmp} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '')"
            ) as copy:
                copy.write(buffer.getvalue())

            cur.execute(spec.insert_sql.format(tmp=tmp))
            return max(cur.rowcount, 0)


def _load_table(
    conn,
    spec: TableSpec,
    input_dir: Path,
    batch_size: int,
) -> dict:
    path = input_dir / f"{spec.name}.csv"
    if not path.exists():
        raise SystemExit(f"No existe {path}. Ejecuta primero generate_history.py.")

    started = time.perf_counter()
    rows_read = 0
    inserted = 0
    chunks = 0

    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if tuple(header or ()) != spec.columns:
            raise SystemExit(
                f"Cabecera inesperada en {path.name}:\n"
                f"  esperada: {spec.columns}\n"
                f"  recibida: {tuple(header or ())}"
            )

        while True:
            chunk = [row for row in islice(reader, batch_size) if row]
            if not chunk:
                break
            inserted += _load_chunk(conn, spec, chunk)
            rows_read += len(chunk)
            chunks += 1
            if chunks % 20 == 0:
                print(f"  {spec.name}: {rows_read:,} filas leídas...".replace(",", "."))

    elapsed = round(time.perf_counter() - started, 2)
    return {
        "csv_rows": rows_read,
        "inserted": inserted,
        "skipped": rows_read - inserted,
        "seconds": elapsed,
        "chunks": chunks,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.batch_size < 1:
        raise SystemExit("--batch-size debe ser >= 1")

    if not args.manifest.exists():
        raise SystemExit(
            f"No existe {args.manifest}. Ejecuta primero generate_history.py."
        )
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    run_id = manifest.get("run_id")
    if not run_id:
        raise SystemExit(f"El manifiesto {args.manifest} no contiene run_id.")
    run_tag = manifest.get("run_tag") or run_id.removeprefix("hist-")

    specs = _build_specs()
    started = time.perf_counter()

    with connect() as conn:
        existing = _check_run(conn, run_tag, args.reset)
        if existing:
            print(f"run_tag ya presente en la base: {', '.join(existing)}")
        if args.reset:
            _reset_tables(conn)

        before = {}
        with conn.cursor() as cur:
            for spec in specs:
                before[spec.name] = _table_count(cur, spec.name)
        conn.commit()

        print(f"Cargando run_id={run_id} en lotes de {args.batch_size} filas")
        results = {}
        for spec in specs:
            print(f"- {spec.name}")
            result = _load_table(conn, spec, args.input_dir, args.batch_size)
            conn.commit()
            with conn.cursor() as cur:
                cur.execute(f"ANALYZE {spec.name}")
                result["after"] = _table_count(cur, spec.name)
            conn.commit()
            result["before"] = before[spec.name]
            result["delta"] = result["after"] - result["before"]
            results[spec.name] = result
            print(
                f"  leídas={result['csv_rows']:,} insertadas={result['inserted']:,} "
                f"omitidas={result['skipped']:,} total={result['after']:,} "
                f"({result['seconds']} s)".replace(",", ".")
            )

    elapsed = round(time.perf_counter() - started, 2)
    load_manifest = {
        "run_id": run_id,
        "run_tag": manifest.get("run_tag"),
        "loaded_at": datetime.now(UTC).isoformat(),
        "source_manifest": str(args.manifest).replace("\\", "/"),
        "input_dir": str(args.input_dir).replace("\\", "/"),
        "batch_size": args.batch_size,
        "reset": bool(args.reset),
        "duration_seconds": elapsed,
        "peak_memory_mb": _peak_memory_mb(),
        "tables": results,
    }
    args.load_manifest.parent.mkdir(parents=True, exist_ok=True)
    args.load_manifest.write_text(
        json.dumps(load_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print()
    print("Carga completada")
    print("=" * 68)
    print(f"run_id:   {run_id}")
    print(f"duración: {elapsed} s")
    print(f"memoria:  {load_manifest['peak_memory_mb']} MB")
    print(f"manifiesto de carga: {args.load_manifest}")
    print()
    print("Siguiente paso: python src/verify_history.py  (o sql/validation/02_historico.sql)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
