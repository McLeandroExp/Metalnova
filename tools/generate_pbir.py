#!/usr/bin/env python3
"""Genera las páginas del informe 006 en formato PBIR.

El modelo semántico se genera aparte con ``tools/generate_tmdl.py``. Este script
escribe ``powerbi/final/MetalNova.Report/definition/pages`` de forma
reproducible: 4 páginas principales, detalle de máquina, detalle de causa y una
página de tooltip.

La página existente ``Modelo validado (T-604)`` se conserva y se oculta.

Uso:
    python tools/generate_pbir.py
    python tools/validate_report.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "powerbi" / "final" / "MetalNova.Report" / "definition"
PAGES = REPORT / "pages"
SCHEMA_VISUAL = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.14.0/schema.json"
)
SCHEMA_PAGE = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/page/2.1.0/schema.json"
)

PAGE_EXECUTIVE = "page_executive_01"
PAGE_OEE = "page_oee_02"
PAGE_MAINTENANCE = "page_maintenance_03"
PAGE_QUALITY = "page_quality_04"
PAGE_MACHINE = "page_detalle_maquina"
PAGE_CAUSA = "page_detalle_causa"
PAGE_TOOLTIP = "page_tooltip_maquina"
VALIDATION_PAGE = "0bf126b4ec1041db"


# ---------------------------------------------------------------------------
# Helpers de expresiones y campos
# ---------------------------------------------------------------------------
def _quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def literal_string(text: str) -> dict:
    return {"expr": {"Literal": {"Value": _quote(text)}}}


def literal_bool(value: bool) -> dict:
    return {"expr": {"Literal": {"Value": "true" if value else "false"}}}


def literal_number(value: float, suffix: str = "D") -> dict:
    return {"expr": {"Literal": {"Value": f"{value}{suffix}"}}}


def literal_raw(value: str) -> dict:
    """Valor literal ya formateado (p. ej. '1D', '2L')."""
    return {"expr": {"Literal": {"Value": value}}}


def column_field(entity: str, prop: str) -> dict:
    return {
        "Column": {
            "Expression": {"SourceRef": {"Entity": entity}},
            "Property": prop,
        }
    }


def measure_field(entity: str, prop: str) -> dict:
    return {
        "Measure": {
            "Expression": {"SourceRef": {"Entity": entity}},
            "Property": prop,
        }
    }


def col(entity: str, prop: str, active: bool = False) -> dict:
    projection = {
        "field": column_field(entity, prop),
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }
    if active:
        projection["active"] = True
    return projection


def meas(entity: str, prop: str) -> dict:
    return {
        "field": measure_field(entity, prop),
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": prop,
    }


def roles(**kwargs) -> dict:
    return {
        role: {"projections": projections}
        for role, projections in kwargs.items()
        if projections
    }


def sort_by(
    entity: str,
    prop: str,
    measure: bool = True,
    direction: str = "Descending",
) -> dict:
    field = measure_field(entity, prop) if measure else column_field(entity, prop)
    return {
        "sort": [{"field": field, "direction": direction}],
        "isDefaultSort": True,
    }


def title_object(text: str) -> dict:
    return {
        "title": [
            {
                "properties": {
                    "show": literal_bool(True),
                    "text": literal_string(text),
                }
            }
        ]
    }


def tooltip_object(section: str) -> dict:
    return {
        "visualTooltip": [
            {
                "properties": {
                    "show": literal_bool(True),
                    "type": literal_string("ReportPage"),
                    "section": literal_string(section),
                }
            }
        ]
    }


# ---------------------------------------------------------------------------
# Plantillas de visuales
# ---------------------------------------------------------------------------
def visual(
    name: str,
    visual_type: str,
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    query_state: dict | None = None,
    sort_definition: dict | None = None,
    title: str | None = None,
    objects: dict | None = None,
    container_objects: dict | None = None,
    sync_group: str | None = None,
    tooltip_page: str | None = None,
    filter_config: dict | None = None,
) -> dict:
    visual_body: dict = {"visualType": visual_type}
    if query_state is not None:
        query: dict = {"queryState": query_state}
        if sort_definition is not None:
            query["sortDefinition"] = sort_definition
        visual_body["query"] = query
    if objects:
        visual_body["objects"] = objects
    container = {}
    if title:
        container.update(title_object(title))
    if tooltip_page:
        container.update(tooltip_object(tooltip_page))
    if container_objects:
        container.update(container_objects)
    if container:
        visual_body["visualContainerObjects"] = container
    if sync_group:
        visual_body["syncGroup"] = {
            "groupName": sync_group,
            "fieldChanges": True,
            "filterChanges": True,
        }
    visual_body["drillFilterOtherVisuals"] = True

    payload: dict = {
        "$schema": SCHEMA_VISUAL,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": 0,
            "width": width,
            "height": height,
            "tabOrder": 0,
        },
        "visual": visual_body,
    }
    if filter_config:
        payload["filterConfig"] = filter_config
    return payload


def card(
    name: str,
    entity: str,
    measure: str,
    x: float,
    y: float,
    width: float = 300,
    height: float = 140,
    title: str | None = None,
    precision: int = 2,
    display_units: str = "1D",
    subtitle: str | None = None,
) -> dict:
    """Tarjeta con formato explícito: sin unidades automáticas y precisión fija.

    ``display_units='1D'`` desactiva el redondeo a miles/millones de Power BI.
    ``precision`` fija los decimales: 0 para conteos, 2 para porcentajes/horas,
    4 para energía por unidad.
    """
    item = visual(
        name,
        "card",
        x,
        y,
        width,
        height,
        query_state=roles(Values=[meas(entity, measure)]),
        title=title or measure,
        objects={
            "labels": [
                {
                    "properties": {
                        "labelDisplayUnits": literal_raw(display_units),
                        "labelPrecision": literal_raw(f"{precision}L"),
                        "fontSize": literal_raw("26D"),
                    }
                }
            ],
            "categoryLabels": [
                {"properties": {"show": literal_bool(False)}}
            ],
        },
    )
    if subtitle:
        item["visual"].setdefault("visualContainerObjects", {})["subTitle"] = [
            {
                "properties": {
                    "show": literal_bool(True),
                    "text": literal_string(subtitle),
                }
            }
        ]
    return item


def textbox(
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    subtitle: str | None = None,
) -> dict:
    paragraphs = [
        {
            "textRuns": [
                {
                    "value": title,
                    "textStyle": {
                        "fontFamily": "'Segoe UI Semibold', helvetica, sans-serif",
                        "fontSize": "22pt",
                        "color": "#1F2933",
                    },
                }
            ]
        }
    ]
    if subtitle:
        paragraphs.append(
            {
                "textRuns": [
                    {
                        "value": subtitle,
                        "textStyle": {
                            "fontFamily": "'Segoe UI', helvetica, sans-serif",
                            "fontSize": "10pt",
                            "color": "#6B7280",
                        },
                    }
                ]
            }
        )
    return visual(
        name,
        "textbox",
        x,
        y,
        width,
        height,
        objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
        container_objects={
            "title": [{"properties": {"show": literal_bool(False)}}],
            "background": [{"properties": {"show": literal_bool(False)}}],
            "border": [{"properties": {"show": literal_bool(False)}}],
        },
    )


def slicer(
    name: str,
    entity: str,
    prop: str,
    x: float,
    y: float,
    width: float,
    title: str,
    mode: str = "Dropdown",
    sync_group: str | None = None,
) -> dict:
    return visual(
        name,
        "slicer",
        x,
        y,
        width,
        90,
        query_state=roles(Values=[col(entity, prop, active=True)]),
        title=title,
        objects={"data": [{"properties": {"mode": literal_string(mode)}}]},
        sync_group=sync_group,
    )


def line_chart(
    name: str,
    category: tuple[str, str],
    measure_specs: list[tuple[str, str]],
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    series: tuple[str, str] | None = None,
    reference_line: tuple[float, str] | None = None,
) -> dict:
    state = roles(
        Category=[col(*category, active=True)],
        Y=[meas(*spec) for spec in measure_specs],
        Series=[col(*series)] if series else [],
    )
    objects = {}
    if reference_line is not None:
        value, color = reference_line
        objects["y1AxisReferenceLine"] = [
            {
                "properties": {
                    "show": literal_bool(True),
                    "value": literal_number(value),
                    "lineColor": {
                        "solid": {"color": literal_string(color)}
                    },
                    "style": literal_string("dashed"),
                    "dataLabelShow": literal_bool(True),
                }
            }
        ]
    return visual(
        name,
        "lineChart",
        x,
        y,
        width,
        height,
        query_state=state,
        title=title,
        objects=objects or None,
    )


def bar_chart(
    name: str,
    category: tuple[str, str],
    measure_spec: tuple[str, str],
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    sort_desc: bool = True,
) -> dict:
    entity, measure = measure_spec
    return visual(
        name,
        "barChart",
        x,
        y,
        width,
        height,
        query_state=roles(
            Category=[col(*category, active=True)],
            Y=[meas(entity, measure)],
        ),
        sort_definition=sort_by(entity, measure) if sort_desc else None,
        title=title,
    )


def table(
    name: str,
    projections: list[dict],
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    sort_definition: dict | None = None,
    tooltip_page: str | None = None,
    totals: bool = True,
) -> dict:
    objects = None
    if not totals:
        # La fila de totales no aporta en tablas de detalle por máquina.
        # El objeto correcto es «total» y la propiedad «totals» (bool).
        objects = {"total": [{"properties": {"totals": literal_bool(False)}}]}
    return visual(
        name,
        "tableEx",
        x,
        y,
        width,
        height,
        query_state=roles(Values=projections),
        sort_definition=sort_definition,
        title=title,
        objects=objects,
        tooltip_page=tooltip_page,
    )


def matrix(
    name: str,
    rows: list[dict],
    values: list[dict],
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    conditional_measure: tuple[str, str] | None = None,
) -> dict:
    objects = {}
    if conditional_measure is not None:
        entity, measure = conditional_measure
        objects["values"] = [
            {
                "properties": {
                    "backColor": {
                        "solid": {
                            "color": {
                                "expr": {
                                    "FillRule": {
                                        "Input": measure_field(entity, measure),
                                        "FillRule": {
                                            "linearGradient3": {
                                                "min": {
                                                    "color": {"Literal": {"Value": "'#F8696B'"}},
                                                    "value": {"Literal": {"Value": "0.55D"}},
                                                },
                                                "mid": {
                                                    "color": {"Literal": {"Value": "'#FFEB84'"}},
                                                    "value": {"Literal": {"Value": "0.70D"}},
                                                },
                                                "max": {
                                                    "color": {"Literal": {"Value": "'#63BE7B'"}},
                                                    "value": {"Literal": {"Value": "0.85D"}},
                                                },
                                                "nullColoringStrategy": {
                                                    "strategy": {
                                                        "Literal": {"Value": "'noColor'"}
                                                    }
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        }
                    }
                },
                "selector": {
                    "data": [{"dataViewWildcard": {"matchingOption": 1}}],
                    "metadata": f"{entity}.{measure}",
                },
            }
        ]
    return visual(
        name,
        "pivotTable",
        x,
        y,
        width,
        height,
        query_state=roles(Rows=rows, Values=values),
        title=title,
        objects=objects or None,
    )


def scatter(
    name: str,
    category: tuple[str, str],
    x_spec: tuple[str, str],
    y_spec: tuple[str, str],
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
) -> dict:
    return visual(
        name,
        "scatterChart",
        x,
        y,
        width,
        height,
        query_state=roles(
            Category=[col(*category, active=True)],
            X=[meas(*x_spec)],
            Y=[meas(*y_spec)],
        ),
        title=title,
    )


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------
def add_header(visuals: list[dict], title: str, subtitle: str) -> None:
    visuals.append(textbox("header_title", 40, 16, 1200, 72, title, subtitle))
    visuals.append(
        textbox(
            "header_warning",
            1480,
            16,
            400,
            48,
            "Datos sintéticos",
            "Prototipo académico · no es telemetría real",
        )
    )


def add_slicers(visuals: list[dict]) -> None:
    visuals.extend(
        [
            slicer(
                "slicer_fecha",
                "dim_tiempo",
                "fecha",
                40,
                100,
                280,
                "Fecha (rango)",
                mode="Between",
                sync_group="sync_fecha",
            ),
            slicer(
                "slicer_planta",
                "v_dim_maquina",
                "planta_nombre",
                340,
                100,
                240,
                "Planta",
                sync_group="sync_planta",
            ),
            slicer(
                "slicer_linea",
                "v_dim_maquina",
                "linea_nombre",
                600,
                100,
                240,
                "Línea",
                sync_group="sync_linea",
            ),
            slicer(
                "slicer_maquina",
                "v_dim_maquina",
                "maquina_codigo",
                860,
                100,
                240,
                "Máquina",
                sync_group="sync_maquina",
            ),
            slicer(
                "slicer_producto",
                "v_dim_producto",
                "producto_nombre",
                1120,
                100,
                300,
                "Producto",
                sync_group="sync_producto",
            ),
            slicer(
                "slicer_turno",
                "dim_turno",
                "codigo",
                1440,
                100,
                200,
                "Turno",
                sync_group="sync_turno",
            ),
        ]
    )


def add_cards(
    visuals: list[dict],
    specs: list[tuple],
) -> None:
    """Añade tarjetas. Cada spec: (entidad, medida, título[, precisión])."""
    for index, spec in enumerate(specs):
        entity, measure, title = spec[:3]
        precision = spec[3] if len(spec) > 3 else 2
        subtitle = spec[4] if len(spec) > 4 else None
        visuals.append(
            card(
                f"card_{index + 1}",
                entity,
                measure,
                40 + index * 310,
                210,
                290,
                135,
                title,
                precision=precision,
                subtitle=subtitle,
            )
        )


def page_executive() -> list[dict]:
    visuals: list[dict] = []
    add_header(
        visuals,
        "01 · Executive Plant Performance",
        "OEE, disponibilidad, rendimiento y calidad por planta · 180 días sintéticos",
    )
    add_slicers(visuals)
    add_cards(
        visuals,
        [
            ("v_loss_tree", "OEE KPI", "OEE global", 2),
            ("v_loss_tree", "OEE Último Mes", "OEE último mes", 2),
            ("v_loss_tree", "Disponibilidad KPI", "Disponibilidad", 2),
            ("v_loss_tree", "Rendimiento KPI", "Rendimiento", 2),
            ("v_loss_tree", "Calidad KPI", "Calidad", 2),
            ("v_alerta_maquina_critica", "Alertas Activas", "Alertas activas", 0),
        ],
    )
    visuals.append(
        line_chart(
            "chart_oee_planta",
            ("v_loss_tree", "anio_mes"),
            [("v_loss_tree", "OEE KPI")],
            40,
            370,
            900,
            315,
            "Tendencia mensual del OEE por planta",
            series=("v_dim_maquina", "planta_codigo"),
            reference_line=(0.85, "#D64550"),
        )
    )
    visuals.append(
        bar_chart(
            "chart_oee_ranking",
            ("v_dim_maquina", "planta_codigo"),
            ("v_loss_tree", "OEE KPI"),
            960,
            370,
            900,
            315,
            "Comparación de OEE entre plantas",
        )
    )
    visuals.append(
        table(
            "table_alertas",
            [
                col("v_dim_maquina", "maquina_codigo"),
                col("v_dim_maquina", "planta_codigo"),
                col("v_alerta_ultimo_turno", "severidad"),
                meas("v_alerta_ultimo_turno", "OEE Alerta"),
                meas("v_alerta_ultimo_turno", "MTBF Alerta (h)"),
                meas("v_alerta_ultimo_turno", "Temperatura Alerta (°C)"),
                col("v_alerta_ultimo_turno", "acciones_sugeridas"),
            ],
            40,
            710,
            1820,
            310,
            "Alertas del último turno · MTBF (h) = horas operativas / fallas del turno; vacío = turno sin fallas. Histórico: página 03",
            sort_definition=sort_by(
                "v_alerta_ultimo_turno",
                "OEE Alerta",
                direction="Ascending",
            ),
            totals=False,
        )
    )
    return visuals


def page_oee() -> list[dict]:
    visuals: list[dict] = []
    add_header(
        visuals,
        "02 · OEE & Loss Tree",
        "Descomposición de pérdidas · tarjetas en horas; tablas y matriz en minutos",
    )
    add_slicers(visuals)
    add_cards(
        visuals,
        [
            ("v_loss_tree", "OEE KPI", "OEE", 2),
            ("v_loss_tree", "Disponibilidad KPI", "Disponibilidad", 2),
            ("v_loss_tree", "Rendimiento KPI", "Rendimiento", 2),
            ("v_loss_tree", "Calidad KPI", "Calidad", 2),
            ("v_loss_tree", "Pérdida Total (h)", "Pérdida total (h)", 2),
            ("v_loss_tree", "Brecha Meta (pp)", "Brecha vs meta (pp)", 2),
        ],
    )
    visuals.append(
        bar_chart(
            "chart_pareto_causas",
            ("dim_causa", "categoria"),
            ("v_kpi_parada", "Downtime por Causa (min)"),
            40,
            370,
            900,
            315,
            "Pareto de downtime no planificado por causa",
        )
    )
    visuals.append(
        matrix(
            "matrix_maquina_turno",
            [
                col("v_dim_maquina", "maquina_codigo", active=True),
                col("dim_turno", "codigo"),
            ],
            [
                meas("v_loss_tree", "OEE KPI"),
                meas("v_loss_tree", "Pérdida Total (min)"),
            ],
            960,
            370,
            900,
            315,
            "Matriz máquina-turno · OEE y pérdida",
            conditional_measure=("v_loss_tree", "OEE KPI"),
        )
    )
    visuals.append(
        bar_chart(
            "chart_perdida_producto",
            ("v_dim_producto", "producto_nombre"),
            ("v_loss_tree", "Pérdida Total (min)"),
            40,
            710,
            900,
            310,
            "Pérdida total por producto",
        )
    )
    visuals.append(
        matrix(
            "matrix_perdida_planta",
            [col("v_dim_maquina", "planta_codigo", active=True)],
            [
                meas("v_loss_tree", "Pérdida Disponibilidad (min)"),
                meas("v_loss_tree", "Pérdida Rendimiento (min)"),
                meas("v_loss_tree", "Pérdida Calidad (min)"),
                meas("v_loss_tree", "Pérdida Total (min)"),
            ],
            960,
            710,
            900,
            310,
            "Loss Tree por planta (minutos equivalentes)",
        )
    )
    return visuals


def page_maintenance() -> list[dict]:
    visuals: list[dict] = []
    add_header(
        visuals,
        "03 · Maintenance Reliability",
        "MTBF, MTTR, fallas cortas y microparadas · tarjetas en horas; tablas en minutos",
    )
    add_slicers(visuals)
    add_cards(
        visuals,
        [
            ("v_kpi_mantenimiento_maquina_turno", "MTBF (h)", "MTBF (h)", 2),
            ("v_kpi_mantenimiento_maquina_turno", "MTTR (h)", "MTTR (h)", 2),
            ("v_kpi_mantenimiento_maquina_turno", "Fallas (conteo)", "Fallas", 0),
            (
                "v_kpi_mantenimiento_maquina_turno",
                "Downtime Mantenimiento (h)",
                "Downtime (h)",
                2,
            ),
            ("v_kpi_mantenimiento", "Intervenciones", "Intervenciones", 0),
            ("v_kpi_mantenimiento", "Costo Mantenimiento (USD)", "Costo (USD)", 2),
        ],
    )
    visuals.append(
        bar_chart(
            "chart_downtime_causa",
            ("dim_causa", "categoria"),
            ("v_kpi_parada", "Downtime por Causa (min)"),
            40,
            370,
            900,
            315,
            "Downtime por causa",
        )
    )
    visuals.append(
        line_chart(
            "chart_mtbf_mensual",
            ("v_kpi_mantenimiento_maquina_turno", "anio_mes"),
            [("v_kpi_mantenimiento_maquina_turno", "MTBF (h)")],
            960,
            370,
            900,
            315,
            "MTBF mensual por planta",
            series=("v_dim_maquina", "planta_codigo"),
        )
    )
    visuals.append(
        table(
            "table_confiabilidad",
            [
                col("v_dim_maquina", "maquina_codigo"),
                col("v_dim_maquina", "planta_codigo"),
                meas("v_kpi_mantenimiento_maquina_turno", "MTBF (h)"),
                meas("v_kpi_mantenimiento_maquina_turno", "MTTR (min)"),
                meas("v_kpi_mantenimiento_maquina_turno", "Fallas (conteo)"),
                meas("v_kpi_mantenimiento_maquina_turno", "Fallas cortas (conteo)"),
                meas("v_kpi_mantenimiento_maquina_turno", "Fallas cortas por 100 h"),
                meas("v_kpi_mantenimiento_maquina_turno", "Microparadas por 100 h"),
                meas("v_kpi_mantenimiento", "Última Intervención"),
            ],
            40,
            710,
            1150,
            310,
            "Confiabilidad por máquina · incluye fallas cortas",
            sort_definition=sort_by(
                "v_kpi_mantenimiento_maquina_turno",
                "MTBF (h)",
                direction="Ascending",
            ),
            tooltip_page=PAGE_TOOLTIP,
        )
    )
    visuals.append(
        scatter(
            "scatter_fallas_cortas",
            ("v_dim_maquina", "maquina_codigo"),
            ("v_kpi_mantenimiento_maquina_turno", "Fallas cortas por 100 h"),
            ("v_kpi_mantenimiento_maquina_turno", "MTBF (h)"),
            1210,
            710,
            650,
            310,
            "MTBF vs fallas cortas por 100 h",
        )
    )
    return visuals


def page_quality() -> list[dict]:
    visuals: list[dict] = []
    add_header(
        visuals,
        "04 · Quality & Energy",
        "Scrap, FPY, retrabajo y energía por unidad buena · calidad por turno y producto",
    )
    add_slicers(visuals)
    add_cards(
        visuals,
        [
            ("v_kpi_calidad_maquina_dia", "FPY KPI", "FPY", 2),
            ("v_kpi_calidad_maquina_dia", "Scrap Rate (Calidad)", "Scrap", 2),
            ("v_kpi_calidad_maquina_dia", "Tasa Defectos", "Defectos", 2),
            ("v_kpi_calidad_maquina_dia", "Tasa Retrabajo", "Retrabajo", 2),
            (
                "v_kpi_calidad_maquina_dia",
                "Energía por Unidad Buena",
                "Energía por Unidad Buena (kWh)",
                4,
            ),
            (
                "v_kpi_calidad_maquina_dia",
                "Energía (kWh)",
                "Energía total (kWh)",
                2,
            ),
        ],
    )
    visuals.append(
        line_chart(
            "chart_calidad_mensual",
            ("v_kpi_calidad_maquina_dia", "anio_mes"),
            [
                ("v_kpi_calidad_maquina_dia", "Scrap Rate (Calidad)"),
                ("v_kpi_calidad_maquina_dia", "FPY KPI"),
            ],
            40,
            370,
            900,
            315,
            "Scrap y FPY por mes",
        )
    )
    visuals.append(
        bar_chart(
            "chart_scrap_planta",
            ("v_dim_maquina", "planta_codigo"),
            ("v_kpi_calidad_maquina_dia", "Scrap Rate (Calidad)"),
            960,
            370,
            900,
            315,
            "Scrap por planta",
        )
    )
    visuals.append(
        bar_chart(
            "chart_scrap_turno",
            ("dim_turno", "codigo"),
            ("v_loss_tree", "Scrap Rate"),
            40,
            710,
            600,
            310,
            "Scrap de producción por turno",
        )
    )
    visuals.append(
        bar_chart(
            "chart_scrap_producto",
            ("v_dim_producto", "producto_nombre"),
            ("v_kpi_calidad_producto_dia", "Scrap Rate (Producto)"),
            660,
            710,
            600,
            310,
            "Scrap por producto",
        )
    )
    visuals.append(
        scatter(
            "scatter_energia_scrap",
            ("v_dim_maquina", "maquina_codigo"),
            ("v_kpi_calidad_maquina_dia", "Energía por Unidad Buena"),
            ("v_kpi_calidad_maquina_dia", "Scrap Rate (Calidad)"),
            1280,
            710,
            580,
            310,
            "Energía vs scrap por máquina",
        )
    )
    return visuals


def page_machine() -> list[dict]:
    visuals: list[dict] = []
    add_header(
        visuals,
        "Detalle de máquina",
        "Historial de OEE, mantenimiento y paradas · se accede por drill-through",
    )
    specs = [
        ("v_loss_tree", "OEE KPI", "OEE", 2),
        ("v_kpi_mantenimiento_maquina_turno", "MTBF (h)", "MTBF (h)", 2),
        ("v_kpi_mantenimiento_maquina_turno", "MTTR (h)", "MTTR (h)", 2),
        ("v_kpi_calidad_maquina_dia", "Scrap Rate (Calidad)", "Scrap", 2),
        ("v_kpi_calidad_maquina_dia", "FPY KPI", "FPY", 2),
    ]
    for index, (entity, measure, title, precision) in enumerate(specs):
        visuals.append(
            card(
                f"card_{index + 1}",
                entity,
                measure,
                40 + index * 370,
                100,
                350,
                130,
                title,
                precision=precision,
            )
        )
    visuals.append(
        line_chart(
            "chart_oee_historial",
            ("v_loss_tree", "anio_mes"),
            [("v_loss_tree", "OEE KPI")],
            40,
            260,
            1200,
            380,
            "OEE mensual de la máquina",
            reference_line=(0.85, "#D64550"),
        )
    )
    visuals.append(
        table(
            "table_intervenciones",
            [
                col("v_kpi_mantenimiento", "inicio_at"),
                col("v_kpi_mantenimiento", "tipo"),
                col("v_kpi_mantenimiento", "estado"),
                col("v_kpi_mantenimiento", "duracion_min"),
                col("v_kpi_mantenimiento", "costo_estimado_usd"),
            ],
            1260,
            260,
            600,
            380,
            "Últimas intervenciones",
        )
    )
    visuals.append(
        table(
            "table_paradas",
            [
                col("v_kpi_parada", "inicio_at"),
                col("v_kpi_parada", "duracion_min"),
                col("v_kpi_parada", "es_planificada"),
                col("v_kpi_parada", "es_microparada_regla"),
                col("v_kpi_parada", "es_falla"),
                col("v_dim_maquina", "planta_codigo"),
            ],
            40,
            660,
            900,
            370,
            "Paradas de la máquina",
        )
    )
    visuals.append(
        table(
            "table_calidad_maquina",
            [
                meas("v_kpi_calidad_maquina_dia", "FPY KPI"),
                meas("v_kpi_calidad_maquina_dia", "Tasa Defectos"),
                meas("v_kpi_calidad_maquina_dia", "Tasa Retrabajo"),
                meas("v_kpi_calidad_maquina_dia", "Scrap Rate (Calidad)"),
                meas(
                    "v_kpi_calidad_maquina_dia",
                    "Energía por Unidad Buena",
                ),
            ],
            960,
            660,
            900,
            370,
            "Calidad y energía de la máquina",
        )
    )
    return visuals


def page_causa() -> list[dict]:
    visuals: list[dict] = []
    add_header(
        visuals,
        "Detalle de causa",
        "Máquinas, turnos y pérdidas asociadas a una causa del Pareto",
    )
    specs = [
        ("v_kpi_parada", "Paradas No Planificadas", "Paradas", 0),
        ("v_kpi_parada", "Downtime por Causa (h)", "Downtime (h)", 2),
        ("v_kpi_parada", "Máquinas con Paradas", "Máquinas afectadas", 0),
        ("v_kpi_parada", "Participación Downtime Causa", "Participación", 2),
    ]
    for index, (entity, measure, title, precision) in enumerate(specs):
        visuals.append(
            card(
                f"card_{index + 1}",
                entity,
                measure,
                40 + index * 460,
                100,
                440,
                130,
                title,
                precision=precision,
            )
        )
    visuals.append(
        table(
            "table_maquinas_causa",
            [
                col("v_dim_maquina", "maquina_codigo"),
                col("v_dim_maquina", "planta_codigo"),
                meas("v_kpi_parada", "Paradas No Planificadas"),
                meas("v_kpi_parada", "Downtime por Causa (min)"),
                meas("v_kpi_mantenimiento_maquina_turno", "MTBF (h)"),
                meas("v_kpi_mantenimiento_maquina_turno", "MTTR (min)"),
            ],
            40,
            260,
            1200,
            770,
            "Máquinas que explican la causa",
            sort_definition=sort_by("v_kpi_parada", "Downtime por Causa (min)"),
            tooltip_page=PAGE_TOOLTIP,
        )
    )
    visuals.append(
        bar_chart(
            "chart_causa_turno",
            ("dim_turno", "codigo"),
            ("v_kpi_parada", "Downtime por Causa (min)"),
            1260,
            260,
            620,
            770,
            "Downtime de la causa por turno",
        )
    )
    return visuals


def page_tooltip() -> list[dict]:
    return [
        visual(
            "tooltip_mtbf",
            "cardVisual",
            10,
            10,
            145,
            100,
            query_state=roles(
                Data=[meas("v_kpi_mantenimiento_maquina_turno", "MTBF (h)")]
            ),
            title="MTBF",
        ),
        visual(
            "tooltip_mttr",
            "cardVisual",
            165,
            10,
            145,
            100,
            query_state=roles(
                Data=[meas("v_kpi_mantenimiento_maquina_turno", "MTTR (min)")]
            ),
            title="MTTR",
        ),
        visual(
            "tooltip_ultima",
            "cardVisual",
            10,
            115,
            300,
            115,
            query_state=roles(
                Data=[meas("v_kpi_mantenimiento", "Última Intervención")]
            ),
            title="Última intervención",
        ),
    ]


# ---------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------
def drillthrough_page(
    filter_name: str,
    binding_name: str,
    parameter_name: str,
    entity: str,
    prop: str,
) -> dict:
    """Página oculta que recibe el contexto de drill-through de un campo.

    Power BI reconoce la página por ``pageBinding`` tipo ``Drillthrough`` y por
    el filtro con ``howCreated = "Drillthrough"``. Sin ambos, el clic derecho
    no ofrece «Obtener detalles» (AC-604).
    """
    field = column_field(entity, prop)
    return {
        "visibility": "HiddenInViewMode",
        "filterConfig": {
            "filters": [
                {
                    "name": filter_name,
                    "field": field,
                    "type": "Categorical",
                    "howCreated": "Drillthrough",
                }
            ]
        },
        "pageBinding": {
            "name": binding_name,
            "type": "Drillthrough",
            "parameters": [
                {
                    "name": parameter_name,
                    "boundFilter": filter_name,
                    "fieldExpr": field,
                }
            ],
        },
    }


PAGE_SPECS = [
    (PAGE_EXECUTIVE, "01 Executive Plant Performance", page_executive, {}),
    (PAGE_OEE, "02 OEE & Loss Tree", page_oee, {}),
    (PAGE_MAINTENANCE, "03 Maintenance Reliability", page_maintenance, {}),
    (PAGE_QUALITY, "04 Quality & Energy", page_quality, {}),
    (
        PAGE_MACHINE,
        "Detalle máquina",
        page_machine,
        drillthrough_page(
            "drill_maquina",
            "binding_detalle_maquina",
            "param_detalle_maquina",
            "v_dim_maquina",
            "maquina_codigo",
        ),
    ),
    (
        PAGE_CAUSA,
        "Detalle causa",
        page_causa,
        drillthrough_page(
            "drill_causa",
            "binding_detalle_causa",
            "param_detalle_causa",
            "dim_causa",
            "categoria",
        ),
    ),
    (
        PAGE_TOOLTIP,
        "Tooltip máquina",
        page_tooltip,
        {
            "type": "Tooltip",
            "displayOption": "ActualSize",
            "width": 320,
            "height": 240,
            "visibility": "HiddenInViewMode",
            "filterConfig": {
                "filters": [
                    {
                        "name": "tooltip_maquina",
                        "field": column_field("v_dim_maquina", "maquina_codigo"),
                        "type": "Categorical",
                        "howCreated": "Drillthrough",
                    }
                ]
            },
            "pageBinding": {
                "name": "binding_tooltip_maquina",
                "type": "Tooltip",
                "parameters": [
                    {
                        "name": "param_tooltip_maquina",
                        "boundFilter": "tooltip_maquina",
                        "fieldExpr": column_field(
                            "v_dim_maquina", "maquina_codigo"
                        ),
                    }
                ],
            },
        },
    ),
]


def write_page(
    page_id: str,
    display_name: str,
    visuals: list[dict],
    extra: dict,
) -> None:
    page_dir = PAGES / page_id
    if page_dir.exists():
        shutil.rmtree(page_dir)
    visuals_dir = page_dir / "visuals"
    visuals_dir.mkdir(parents=True)

    page = {
        "$schema": SCHEMA_PAGE,
        "name": page_id,
        "displayName": display_name,
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920,
        "visibility": "AlwaysVisible",
    }
    page.update(extra)
    if page.get("type") == "Tooltip":
        page.pop("width", None)
        page.pop("height", None)
        page["width"] = extra["width"]
        page["height"] = extra["height"]

    (page_dir / "page.json").write_text(
        json.dumps(page, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    for z_index, item in enumerate(visuals, start=1):
        item["position"]["z"] = z_index * 1000
        item["position"]["tabOrder"] = z_index
        visual_dir = visuals_dir / item["name"]
        visual_dir.mkdir(parents=True, exist_ok=True)
        (visual_dir / "visual.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )


def hide_validation_page() -> None:
    page_file = PAGES / VALIDATION_PAGE / "page.json"
    if not page_file.exists():
        return
    page = json.loads(page_file.read_text(encoding="utf-8"))
    page["visibility"] = "HiddenInViewMode"
    page_file.write_text(
        json.dumps(page, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    if not PAGES.exists():
        raise SystemExit(f"No existe {PAGES}; abre el .pbip una vez en Power BI")

    for page_id, display_name, builder, extra in PAGE_SPECS:
        write_page(page_id, display_name, builder(), extra)

    hide_validation_page()

    order = [page_id for page_id, _, _, _ in PAGE_SPECS] + [VALIDATION_PAGE]
    pages_meta = {
        "$schema": (
            "https://developer.microsoft.com/json-schemas/fabric/item/report/"
            "definition/pagesMetadata/1.1.0/schema.json"
        ),
        "pageOrder": order,
        "activePageName": PAGE_EXECUTIVE,
    }
    (PAGES / "pages.json").write_text(
        json.dumps(pages_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    total = sum(len(builder()) for _, _, builder, _ in PAGE_SPECS)
    print(f"Páginas generadas: {len(PAGE_SPECS)} · Visuales: {total}")
    print(f"Directorio: {PAGES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
