#!/usr/bin/env python3
"""Genera una página de validación con tarjetas KPI para el modelo 006.

Se usa mientras se construyen las cuatro páginas definitivas (T-606…T-609).
No sustituye la guía de visuales: solo comprueba que el modelo responde.
"""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "powerbi/final/MetalNova.Report"
PAGES = REPORT / "definition/pages"

CARDS = [
    ("OEE KPI", "v_loss_tree", "OEE global (180 días)"),
    ("OEE Último Mes", "v_loss_tree", "OEE último mes"),
    ("Disponibilidad KPI", "v_loss_tree", "Disponibilidad"),
    ("Rendimiento KPI", "v_loss_tree", "Rendimiento"),
    ("Calidad KPI", "v_loss_tree", "Calidad"),
    ("MTBF (h)", "v_kpi_mantenimiento_maquina_turno", "MTBF (h)"),
    ("MTTR (min)", "v_kpi_mantenimiento_maquina_turno", "MTTR (min)"),
    ("FPY KPI", "v_kpi_calidad_maquina_dia", "FPY"),
    ("Energía por Unidad Buena", "v_kpi_calidad_maquina_dia", "Energía / unidad buena"),
    ("Alertas Activas", "v_alerta_maquina_critica", "Alertas activas"),
]

SCHEMA_VISUAL = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json"
SCHEMA_PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
SCHEMA_PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"


def literal(value: str) -> dict:
    return {"expr": {"Literal": {"Value": f"'{value}'"}}}


def visual_json(name: str, title: str, entity: str, measure: str, x: int, y: int) -> dict:
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": 1000,
            "height": 280,
            "width": 340,
            "tabOrder": 1000,
        },
        "visual": {
            "visualType": "cardVisual",
            "query": {
                "queryState": {
                    "Data": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {
                                            "SourceRef": {"Entity": entity}
                                        },
                                        "Property": measure,
                                    }
                                },
                                "queryRef": f"{entity}.{measure}",
                                "nativeQueryRef": measure,
                            }
                        ]
                    }
                }
            },
            "visualContainerObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {
                                "expr": {"Literal": {"Value": "true"}}
                            },
                            "text": literal(title),
                        }
                    }
                ]
            },
            "drillFilterOtherVisuals": True,
        },
    }


def slicer_json(name: str, entity: str, column: str, title: str, x: int, y: int) -> dict:
    return {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": 1001,
            "height": 140,
            "width": 340,
            "tabOrder": 1001,
        },
        "visual": {
            "visualType": "slicer",
            "query": {
                "queryState": {
                    "Values": {
                        "projections": [
                            {
                                "field": {
                                    "Column": {
                                        "Expression": {
                                            "SourceRef": {"Entity": entity}
                                        },
                                        "Property": column,
                                    }
                                },
                                "queryRef": f"{entity}.{column}",
                                "nativeQueryRef": column,
                                "active": True,
                            }
                        ]
                    }
                }
            },
            "objects": {
                "data": [
                    {
                        "properties": {
                            "mode": {
                                "expr": {"Literal": {"Value": "'Basic'"}}
                            }
                        }
                    }
                ]
            },
            "visualContainerObjects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": literal(title),
                        }
                    }
                ]
            },
        },
    }


def main() -> int:
    if not PAGES.exists():
        raise SystemExit(f"No existe {PAGES}")

    for child in PAGES.iterdir():
        if child.is_dir():
            shutil.rmtree(child)

    page_name = uuid.uuid4().hex[:16]
    page_dir = PAGES / page_name
    (page_dir / "visuals").mkdir(parents=True)

    page = {
        "$schema": SCHEMA_PAGE,
        "name": page_name,
        "displayName": "Modelo validado (T-604)",
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920,
    }
    (page_dir / "page.json").write_text(
        json.dumps(page, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    for index, (measure, entity, title) in enumerate(CARDS):
        column = index % 5
        row = index // 5
        name = uuid.uuid4().hex[:16]
        visual_dir = page_dir / "visuals" / name
        visual_dir.mkdir(parents=True)
        x = 40 + column * 370
        y = 40 + row * 320
        (visual_dir / "visual.json").write_text(
            json.dumps(
                visual_json(name, title, entity, measure, x, y),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    slicer_name = uuid.uuid4().hex[:16]
    slicer_dir = page_dir / "visuals" / slicer_name
    slicer_dir.mkdir(parents=True)
    (slicer_dir / "visual.json").write_text(
        json.dumps(
            slicer_json(
                slicer_name,
                "v_dim_maquina",
                "planta_nombre",
                "Filtro de planta (prueba de relación)",
                40,
                720,
            ),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    pages_meta = {
        "$schema": SCHEMA_PAGES,
        "pageOrder": [page_name],
        "activePageName": page_name,
    }
    (PAGES / "pages.json").write_text(
        json.dumps(pages_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"Página de validación generada: {page_dir}")
    print(f"Tarjetas: {len(CARDS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
