#!/usr/bin/env python3
"""Valida el informe PBIR generado contra el modelo TMDL.

Comprueba que cada campo referenciado por un visual existe en el modelo, que las
páginas y visuales están dentro del lienzo, que los slicers sincronizados usan
el mismo campo y que las páginas ocultas de drill-through/tooltip están bien
formadas.

Uso:
    python tools/validate_report.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "powerbi" / "final" / "MetalNova.SemanticModel" / "definition" / "tables"
PAGES = ROOT / "powerbi" / "final" / "MetalNova.Report" / "definition" / "pages"

MAIN_PAGES = {
    "page_executive_01",
    "page_oee_02",
    "page_maintenance_03",
    "page_quality_04",
}


def load_model() -> dict[str, dict[str, set[str]]]:
    model: dict[str, dict[str, set[str]]] = {}
    for path in sorted(MODEL.glob("*.tmdl")):
        table = None
        columns: set[str] = set()
        measures: set[str] = set()
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if line.startswith("table "):
                table = line[len("table ") :].strip()
            elif line.startswith("\tcolumn "):
                columns.add(line[len("\tcolumn ") :].strip())
            elif line.startswith("\tmeasure '"):
                name = line[len("\tmeasure '") :]
                if "'" in name:
                    name = name[: name.index("'")]
                    measures.add(name)
        if table:
            model[table] = {"columns": columns, "measures": measures}
    return model


def field_refs(node, output: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for key in ("Column", "Measure"):
            if key in node and isinstance(node[key], dict):
                expression = node[key].get("Expression", {})
                source = expression.get("SourceRef", {})
                entity = source.get("Entity")
                prop = node[key].get("Property")
                if entity and prop:
                    output.append((entity, prop))
        for value in node.values():
            field_refs(value, output)
    elif isinstance(node, list):
        for item in node:
            field_refs(item, output)


def overlaps(a: dict, b: dict) -> bool:
    ax, ay = a["x"], a["y"]
    bx, by = b["x"], b["y"]
    return not (
        ax + a["width"] <= bx
        or bx + b["width"] <= ax
        or ay + a["height"] <= by
        or by + b["height"] <= ay
    )


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    model = load_model()

    pages_meta = json.loads((PAGES / "pages.json").read_text(encoding="utf-8"))
    order = pages_meta.get("pageOrder", [])
    if not order:
        errors.append("pages.json no tiene pageOrder")

    page_names: set[str] = set()
    slicer_groups: dict[str, tuple[str, str]] = {}
    tooltip_pages: set[str] = set()
    drillthrough_pages: set[str] = set()
    visual_count_total = 0

    for page_id in order:
        page_dir = PAGES / page_id
        page_file = page_dir / "page.json"
        if not page_file.exists():
            errors.append(f"{page_id}: falta page.json")
            continue
        page = json.loads(page_file.read_text(encoding="utf-8"))
        name = page.get("name", "")
        if name in page_names:
            errors.append(f"{page_id}: nombre de página duplicado")
        page_names.add(name)
        if len(name) > 50:
            errors.append(f"{page_id}: nombre de página > 50 caracteres")
        if page.get("type") == "Tooltip":
            tooltip_pages.add(name)

        binding = page.get("pageBinding") or {}
        filters = page.get("filterConfig", {}).get("filters", [])
        filter_names = {item.get("name") for item in filters}
        if binding.get("type") == "Drillthrough":
            drillthrough_pages.add(name)
            if not any(
                item.get("howCreated") == "Drillthrough" for item in filters
            ):
                errors.append(
                    f"{page_id}: pageBinding Drillthrough sin filtro "
                    "howCreated=Drillthrough"
                )
            for parameter in binding.get("parameters", []):
                if parameter.get("boundFilter") not in filter_names:
                    errors.append(
                        f"{page_id}: parámetro {parameter.get('name')!r} "
                        "apunta a un filtro inexistente"
                    )
        if page.get("type") == "Tooltip" and binding.get("type") != "Tooltip":
            errors.append(f"{page_id}: página Tooltip sin pageBinding Tooltip")
        if binding.get("type") == "Tooltip" and page.get("type") != "Tooltip":
            errors.append(f"{page_id}: pageBinding Tooltip sin type Tooltip")

        width = float(page.get("width", 1920))
        height = float(page.get("height", 1080))
        visuals: list[dict] = []
        visuals_dir = page_dir / "visuals"
        if visuals_dir.exists():
            for visual_file in sorted(visuals_dir.glob("*/visual.json")):
                data = json.loads(visual_file.read_text(encoding="utf-8"))
                visuals.append(data)

        if not visuals:
            errors.append(f"{page_id}: no tiene visuales")
        if page_id in MAIN_PAGES and len(visuals) < 8:
            errors.append(
                f"{page_id}: solo {len(visuals)} visuales; se esperaban >= 8"
            )

        for data in visuals:
            visual_count_total += 1
            label = f"{page_id}/{data.get('name')}"
            position = data.get("position", {})
            if (
                position.get("x", 0) < 0
                or position.get("y", 0) < 0
                or position.get("x", 0) + position.get("width", 0) > width
                or position.get("y", 0) + position.get("height", 0) > height
            ):
                errors.append(f"{label}: fuera del lienzo")

            refs: list[tuple[str, str]] = []
            field_refs(data.get("visual", {}).get("query", {}), refs)
            field_refs(data.get("filterConfig", {}), refs)
            for entity, prop in refs:
                if entity not in model:
                    errors.append(f"{label}: tabla inexistente {entity!r}")
                    continue
                if prop not in model[entity]["columns"] and prop not in model[entity]["measures"]:
                    errors.append(f"{label}: campo inexistente {entity}.{prop}")

            visual_type = data.get("visual", {}).get("visualType")
            if visual_type == "slicer":
                sync = data.get("visual", {}).get("syncGroup")
                if sync:
                    group = sync.get("groupName")
                    field = refs[0] if refs else None
                    if group and field:
                        previous = slicer_groups.get(group)
                        if previous and previous != field:
                            errors.append(
                                f"{label}: grupo {group} con campos distintos "
                                f"{previous} vs {field}"
                            )
                        slicer_groups[group] = field

            tooltip = (
                data.get("visual", {})
                .get("visualContainerObjects", {})
                .get("visualTooltip")
            )
            if tooltip:
                for item in tooltip:
                    props = item.get("properties", {})
                    section = (
                        props.get("section", {})
                        .get("expr", {})
                        .get("Literal", {})
                        .get("Value", "")
                    )
                    if section and section.strip("'") not in {
                        p.get("name") for p in (
                            json.loads((PAGES / pid / "page.json").read_text(encoding="utf-8"))
                            for pid in order
                            if (PAGES / pid / "page.json").exists()
                        )
                    }:
                        errors.append(f"{label}: tooltip apunta a página inexistente")

        for index, first in enumerate(visuals):
            for second in visuals[index + 1 :]:
                if overlaps(first.get("position", {}), second.get("position", {})):
                    warnings.append(
                        f"{page_id}: solapan {first.get('name')} y {second.get('name')}"
                    )

    for page_id in (MAIN_PAGES | {"page_detalle_maquina", "page_detalle_causa"}):
        if page_id not in order:
            errors.append(f"falta la página obligatoria {page_id}")

    if "page_tooltip_maquina" not in tooltip_pages:
        errors.append("la página de tooltip no está marcada como Tooltip")
    if "page_detalle_maquina" not in drillthrough_pages:
        errors.append(
            "la página de detalle de máquina no tiene pageBinding Drillthrough"
        )

    print("Validación del informe PBIR")
    print("=" * 72)
    print(f"Páginas: {len(order)} · Visuales: {visual_count_total}")
    print(f"Tablas del modelo: {len(model)}")
    if warnings:
        print()
        for warning in warnings:
            print(f"[AVISO] {warning}")
    if errors:
        print()
        for error in errors:
            print(f"[FALLA] {error}")
        print()
        print(f"Resultado: {len(errors)} errores")
        return 1
    print()
    print("Resultado: OK · todas las referencias y páginas son coherentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
