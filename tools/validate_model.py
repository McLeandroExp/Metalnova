#!/usr/bin/env python3
"""Comprueba referencias del modelo TMDL contra PostgreSQL.

No valida la sintaxis DAX completa (eso lo hace Power BI al abrir el .pbip),
pero detecta columnas/medidas inexistentes y relaciones con tipos incompatibles.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_tmdl as g  # noqa: E402

TABLE_COLUMNS = {}
for table in g.TABLES:
    TABLE_COLUMNS[table["name"]] = {
        col["name"]: col["type"].lower() for col in g.query_columns(table["name"])
    }

MEASURE_NAMES = {m[1] for m in g.MEASURES}
errors: list[str] = []
warnings: list[str] = []

# Power BI compara nombres de medidas y columnas sin distinguir mayúsculas.
for table, measure, _expr, _fmt, _folder in g.MEASURES:
    cols = {name.casefold() for name in TABLE_COLUMNS.get(table, {})}
    if measure.casefold() in cols:
        errors.append(
            f"{table}.{measure}: el nombre de la medida choca con una columna homónima"
        )

for table, measure, _expr, _fmt, _folder in g.MEASURES:
    same = [m for m in MEASURE_NAMES if m != measure and m.casefold() == measure.casefold()]
    for other in same:
        warnings.append(f"medidas con nombre equivalente: {measure!r} y {other!r}")

COL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]+)\s*\]")
MEASURE_RE = re.compile(r"\[([^\]]+)\]")

for table, measure, expr, _fmt, _folder in g.MEASURES:
    table_refs = set()
    for match in COL_RE.finditer(expr):
        ref_table, ref_col = match.group(1), match.group(2)
        table_refs.add(ref_table)
        if ref_table not in TABLE_COLUMNS:
            errors.append(f"{table}.{measure}: tabla desconocida {ref_table}")
        elif ref_col not in TABLE_COLUMNS[ref_table]:
            errors.append(f"{table}.{measure}: columna inexistente {ref_table}[{ref_col}]")
    for match in MEASURE_RE.finditer(expr):
        ref = match.group(1)
        # Las referencias table[column] ya se validaron arriba.
        if any(ref == m for m in MEASURE_NAMES):
            continue
        # Si el corchete va precedido de un nombre de tabla, es una columna.
        start = match.start()
        prefix = expr[max(0, start - 80):start]
        if COL_RE.search(prefix + "[" + ref + "]"):
            continue
        errors.append(f"{table}.{measure}: medida desconocida [{ref}]")

for from_table, from_col, to_table, to_col in g.RELATIONSHIPS:
    for side, t, c in (("from", from_table, from_col), ("to", to_table, to_col)):
        if t not in TABLE_COLUMNS:
            errors.append(f"relación {from_table}->{to_table}: tabla {t} inexistente")
        elif c not in TABLE_COLUMNS[t]:
            errors.append(f"relación {from_table}->{to_table}: columna {t}[{c}] inexistente")
    if from_table in TABLE_COLUMNS and to_table in TABLE_COLUMNS:
        ft = TABLE_COLUMNS[from_table].get(from_col)
        tt = TABLE_COLUMNS[to_table].get(to_col)
        if ft and tt:
            numeric = {"integer", "bigint", "smallint", "numeric", "double precision", "real"}
            dates = {"date", "timestamp without time zone", "timestamp with time zone"}
            if ft in numeric and tt in numeric:
                pass
            elif ft in dates and tt in dates:
                pass
            elif ft == tt:
                pass
            else:
                errors.append(
                    f"relación {from_table}[{from_col}] ({ft}) -> {to_table}[{to_col}] ({tt}): tipos incompatibles"
                )

if warnings:
    print("ADVERTENCIAS:")
    for warning in warnings:
        print("  -", warning)

if errors:
    print(f"ERRORES ({len(errors)}):")
    for error in errors:
        print("  -", error)
    raise SystemExit(1)

print(
    f"OK: {len(g.MEASURES)} medidas, {len(g.RELATIONSHIPS)} relaciones, "
    f"{len(TABLE_COLUMNS)} tablas; referencias y tipos coherentes."
)
