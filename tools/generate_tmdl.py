#!/usr/bin/env python3
"""Genera el TMDL del modelo semántico 006 desde PostgreSQL.

El modelo es un esquema en estrella con dimensiones conformadas:
  v_dim_maquina, v_dim_producto, dim_tiempo, dim_turno, dim_causa
y hechos:
  v_loss_tree, v_kpi_parada, v_kpi_mantenimiento_maquina_turno,
  v_kpi_mantenimiento, v_kpi_calidad_maquina_dia, v_alerta_maquina_critica.

Uso:
    python tools/generate_tmdl.py [ruta_semantic_model]

Requiere Docker con el contenedor metalnova_db en ejecución. No necesita
psycopg: consulta information_schema con psql dentro del contenedor.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

DB_SERVICE = "db"
DB_USER = "metalinova"
DB_NAME = "metalinova"
ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Configuración del modelo
# ---------------------------------------------------------------------------

TABLES = [
    {
        "name": "v_dim_maquina",
        "kind": "dim",
        "key": "id_maquina",
        "hidden": {"id_maquina", "id_linea", "id_planta"},
        "hierarchy": {
            "name": "Ubicación",
            "levels": [
                ("Planta", "planta_nombre"),
                ("Línea", "linea_nombre"),
                ("Máquina", "maquina_nombre"),
            ],
        },
    },
    {
        "name": "v_dim_producto",
        "kind": "dim",
        "key": "id_producto",
        "hidden": {"id_producto", "id_familia"},
        "hierarchy": {
            "name": "Producto",
            "levels": [
                ("Familia", "familia_nombre"),
                ("Producto", "producto_nombre"),
            ],
        },
    },
    {
        "name": "dim_tiempo",
        "kind": "dim",
        "key": "id_tiempo",
        "hidden": {"id_tiempo"},
        "data_category": "Time",
        "hierarchy": {
            "name": "Calendario",
            "levels": [
                ("Año", "anio"),
                ("Trimestre", "trimestre"),
                ("Mes", "mes"),
                ("Día", "fecha"),
            ],
        },
    },
    {
        "name": "dim_turno",
        "kind": "dim",
        "key": "id_turno",
        "hidden": {"id_turno"},
    },
    {
        "name": "dim_causa",
        "kind": "dim",
        "key": "id_causa",
        "hidden": {"id_causa"},
        "hierarchy": {
            "name": "Causa",
            "levels": [
                ("Categoría", "categoria"),
                ("Detalle", "descripcion"),
            ],
        },
    },
    {
        "name": "v_loss_tree",
        "kind": "fact",
        "hidden": {
            "id_produccion",
            "id_orden",
            "fecha",
            "anio_mes",
            "id_planta",
            "planta_codigo",
            "id_linea",
            "linea_codigo",
            "id_maquina",
            "maquina_codigo",
            "maquina_tipo",
            "maquina_criticidad",
            "id_turno",
            "turno_codigo",
            "id_producto",
            "producto_codigo",
            "id_familia",
            "familia_codigo",
        },
    },
    {
        "name": "v_kpi_parada",
        "kind": "fact",
        "hidden": {
            "id_parada",
            "id_maquina",
            "maquina_codigo",
            "maquina_nombre",
            "maquina_tipo",
            "maquina_criticidad",
            "id_planta",
            "planta_codigo",
            "id_linea",
            "linea_codigo",
            "id_turno",
            "turno_codigo",
            "id_tiempo",
            "fecha",
            "anio_mes",
            "id_causa",
            "causa_codigo",
            "causa_categoria",
            "causa_es_planificada",
            "id_mantenimiento",
            "microparada_min",
            "falla_corta_min",
        },
    },
    {
        "name": "v_kpi_mantenimiento_maquina_turno",
        "kind": "fact",
        "hidden": {
            "id_maquina",
            "maquina_codigo",
            "maquina_nombre",
            "maquina_tipo",
            "maquina_criticidad",
            "id_planta",
            "planta_codigo",
            "id_linea",
            "linea_codigo",
            "id_turno",
            "turno_codigo",
            "id_tiempo",
            "fecha",
            "anio_mes",
        },
    },
    {
        "name": "v_kpi_mantenimiento",
        "kind": "fact",
        "hidden": {
            "id_mantenimiento",
            "id_maquina",
            "maquina_codigo",
            "maquina_nombre",
            "maquina_tipo",
            "maquina_criticidad",
            "id_planta",
            "planta_codigo",
            "id_linea",
            "linea_codigo",
            "id_tecnico",
            "id_causa",
            "causa_codigo",
            "id_turno",
            "turno_codigo",
            "id_tiempo",
            "fecha",
            "anio_mes",
        },
    },
    {
        "name": "v_kpi_calidad_maquina_dia",
        "kind": "fact",
        "hidden": {
            "id_maquina",
            "maquina_codigo",
            "maquina_nombre",
            "maquina_tipo",
            "maquina_criticidad",
            "id_planta",
            "planta_codigo",
            "id_linea",
            "linea_codigo",
            "id_tiempo",
            "fecha",
            "anio_mes",
        },
    },
    {
        "name": "v_alerta_maquina_critica",
        "kind": "fact",
        "hidden": {
            "fecha",
            "anio_mes",
            "id_planta",
            "planta_codigo",
            "id_linea",
            "linea_codigo",
            "id_maquina",
            "maquina_codigo",
            "maquina_nombre",
            "maquina_tipo",
            "maquina_criticidad",
            "id_turno",
            "turno_codigo",
            "id_tiempo",
            "turno_inicio_at",
        },
    },
    {
        "name": "v_kpi_parametros",
        "kind": "params",
    },
]

RELATIONSHIPS = [
    ("v_loss_tree", "id_maquina", "v_dim_maquina", "id_maquina"),
    ("v_loss_tree", "id_turno", "dim_turno", "id_turno"),
    ("v_loss_tree", "fecha", "dim_tiempo", "fecha"),
    ("v_loss_tree", "id_producto", "v_dim_producto", "id_producto"),
    ("v_kpi_parada", "id_maquina", "v_dim_maquina", "id_maquina"),
    ("v_kpi_parada", "id_turno", "dim_turno", "id_turno"),
    ("v_kpi_parada", "id_tiempo", "dim_tiempo", "id_tiempo"),
    ("v_kpi_parada", "id_causa", "dim_causa", "id_causa"),
    ("v_kpi_mantenimiento_maquina_turno", "id_maquina", "v_dim_maquina", "id_maquina"),
    ("v_kpi_mantenimiento_maquina_turno", "id_turno", "dim_turno", "id_turno"),
    ("v_kpi_mantenimiento_maquina_turno", "id_tiempo", "dim_tiempo", "id_tiempo"),
    ("v_kpi_mantenimiento", "id_maquina", "v_dim_maquina", "id_maquina"),
    ("v_kpi_mantenimiento", "id_turno", "dim_turno", "id_turno"),
    ("v_kpi_mantenimiento", "id_tiempo", "dim_tiempo", "id_tiempo"),
    ("v_kpi_mantenimiento", "id_causa", "dim_causa", "id_causa"),
    ("v_kpi_calidad_maquina_dia", "id_maquina", "v_dim_maquina", "id_maquina"),
    ("v_kpi_calidad_maquina_dia", "id_tiempo", "dim_tiempo", "id_tiempo"),
    ("v_alerta_maquina_critica", "id_maquina", "v_dim_maquina", "id_maquina"),
    ("v_alerta_maquina_critica", "id_turno", "dim_turno", "id_turno"),
    ("v_alerta_maquina_critica", "id_tiempo", "dim_tiempo", "id_tiempo"),
]

# (tabla, nombre, expresión DAX, formato, carpeta)
MEASURES = [
    # OEE y pérdidas
    ("v_loss_tree", "Disponibilidad KPI",
     "DIVIDE ( SUM ( v_loss_tree[tiempo_operativo_min] ), SUM ( v_loss_tree[tiempo_planificado_min] ) )",
     "0.00%", "01 OEE"),
    ("v_loss_tree", "Rendimiento KPI",
     "DIVIDE ( SUM ( v_loss_tree[minutos_ideales] ), SUM ( v_loss_tree[tiempo_operativo_min] ) )",
     "0.00%", "01 OEE"),
    ("v_loss_tree", "Calidad KPI",
     "DIVIDE ( SUM ( v_loss_tree[good_count] ), SUM ( v_loss_tree[total_count] ) )",
     "0.00%", "01 OEE"),
    ("v_loss_tree", "OEE KPI",
     "[Disponibilidad KPI] * [Rendimiento KPI] * [Calidad KPI]",
     "0.00%", "01 OEE"),
    ("v_loss_tree", "OEE Meta",
     "0.85",
     "0.00%", "01 OEE"),
    ("v_loss_tree", "Brecha Meta (pp)",
     "( [OEE KPI] - [OEE Meta] ) * 100",
     "0.00", "01 OEE"),
    ("v_loss_tree", "OEE Último Mes",
     # El calendario cubre 2025-2027, pero los hechos terminan en 2026-10:
     # MAX(dim_tiempo[anio_mes]) devolvía 2027-12 y la tarjeta quedaba vacía.
     # El máximo se toma del propio hecho, respetando los filtros de fecha.
     "VAR UltimoMes = MAX ( v_loss_tree[anio_mes] )\n"
     "RETURN CALCULATE ( [OEE KPI], v_loss_tree[anio_mes] = UltimoMes )",
     "0.00%", "01 OEE"),
    ("v_loss_tree", "Cumple Meta OEE",
     'IF ( [OEE KPI] >= [OEE Meta], "Sí", "No" )',
     None, "01 OEE"),
    ("v_loss_tree", "Pérdida Disponibilidad (min)",
     "SUM ( v_loss_tree[minutos_perdidos_disponibilidad] )",
     "#,##0", "02 Pérdidas"),
    ("v_loss_tree", "Pérdida Rendimiento (min)",
     "SUM ( v_loss_tree[minutos_perdidos_rendimiento] )",
     "#,##0", "02 Pérdidas"),
    ("v_loss_tree", "Pérdida Calidad (min)",
     "SUM ( v_loss_tree[minutos_perdidos_calidad] )",
     "#,##0", "02 Pérdidas"),
    ("v_loss_tree", "Pérdida Total (min)",
     "SUM ( v_loss_tree[minutos_perdidos_total] )",
     "#,##0", "02 Pérdidas"),
    ("v_loss_tree", "Participación Pérdida Disponibilidad",
     "DIVIDE ( SUM ( v_loss_tree[minutos_perdidos_disponibilidad] ), SUM ( v_loss_tree[minutos_perdidos_total] ) )",
     "0.00%", "02 Pérdidas"),
    ("v_loss_tree", "Participación Pérdida Rendimiento",
     "DIVIDE ( SUM ( v_loss_tree[minutos_perdidos_rendimiento] ), SUM ( v_loss_tree[minutos_perdidos_total] ) )",
     "0.00%", "02 Pérdidas"),
    ("v_loss_tree", "Participación Pérdida Calidad",
     "DIVIDE ( SUM ( v_loss_tree[minutos_perdidos_calidad] ), SUM ( v_loss_tree[minutos_perdidos_total] ) )",
     "0.00%", "02 Pérdidas"),
    ("v_loss_tree", "Scrap Rate",
     "DIVIDE ( SUM ( v_loss_tree[scrap_count] ), SUM ( v_loss_tree[total_count] ) )",
     "0.00%", "03 Calidad y energía"),
    ("v_loss_tree", "Unidades Buenas",
     "SUM ( v_loss_tree[good_count] )",
     "#,##0", "04 Producción"),
    ("v_loss_tree", "Unidades Totales",
     "SUM ( v_loss_tree[total_count] )",
     "#,##0", "04 Producción"),
    # Mantenimiento
    ("v_kpi_mantenimiento_maquina_turno", "MTBF (h)",
     "DIVIDE ( SUM ( v_kpi_mantenimiento_maquina_turno[tiempo_operativo_min] ), SUM ( v_kpi_mantenimiento_maquina_turno[fallas] ) * 60 )",
     "#,##0.00", "05 Mantenimiento"),
    ("v_kpi_mantenimiento_maquina_turno", "MTTR (min)",
     "DIVIDE ( SUM ( v_kpi_mantenimiento_maquina_turno[minutos_reparacion] ), SUM ( v_kpi_mantenimiento_maquina_turno[reparaciones] ) )",
     "#,##0.00", "05 Mantenimiento"),
    ("v_kpi_mantenimiento_maquina_turno", "Fallas (conteo)",
     "SUM ( v_kpi_mantenimiento_maquina_turno[fallas] )",
     "#,##0", "05 Mantenimiento"),
    ("v_kpi_mantenimiento_maquina_turno", "Microparadas (conteo)",
     "SUM ( v_kpi_mantenimiento_maquina_turno[microparadas] )",
     "#,##0", "05 Mantenimiento"),
    ("v_kpi_mantenimiento_maquina_turno", "Duración Media Falla (min)",
     "DIVIDE ( SUM ( v_kpi_mantenimiento_maquina_turno[minutos_fallas] ), SUM ( v_kpi_mantenimiento_maquina_turno[fallas] ) )",
     "#,##0.00", "05 Mantenimiento"),
    ("v_kpi_mantenimiento_maquina_turno", "Fallas por 100 h",
     "DIVIDE ( SUM ( v_kpi_mantenimiento_maquina_turno[fallas] ) * 60, SUM ( v_kpi_mantenimiento_maquina_turno[tiempo_operativo_min] ) ) * 100",
     "#,##0.00", "05 Mantenimiento"),
    ("v_kpi_mantenimiento_maquina_turno", "Downtime Mantenimiento (min)",
     "SUM ( v_kpi_mantenimiento_maquina_turno[downtime_no_planificado_min] )",
     "#,##0", "05 Mantenimiento"),
    ("v_kpi_mantenimiento", "Intervenciones",
     "COUNTROWS ( v_kpi_mantenimiento )",
     "#,##0", "05 Mantenimiento"),
    ("v_kpi_mantenimiento", "Costo Mantenimiento (USD)",
     "SUM ( v_kpi_mantenimiento[costo_estimado_usd] )",
     "$ #,##0", "05 Mantenimiento"),
    ("v_kpi_mantenimiento", "Última Intervención",
     "MAX ( v_kpi_mantenimiento[inicio_at] )",
     "General Date", "05 Mantenimiento"),
    # Calidad
    ("v_kpi_calidad_maquina_dia", "FPY KPI",
     "DIVIDE ( SUM ( v_kpi_calidad_maquina_dia[unidades_inspeccionadas] ) - SUM ( v_kpi_calidad_maquina_dia[unidades_retrabajo] ), SUM ( v_kpi_calidad_maquina_dia[unidades_inspeccionadas] ) )",
     "0.00%", "03 Calidad y energía"),
    ("v_kpi_calidad_maquina_dia", "Tasa Defectos",
     "DIVIDE ( SUM ( v_kpi_calidad_maquina_dia[unidades_defectuosas] ), SUM ( v_kpi_calidad_maquina_dia[unidades_inspeccionadas] ) )",
     "0.00%", "03 Calidad y energía"),
    ("v_kpi_calidad_maquina_dia", "Tasa Retrabajo",
     "DIVIDE ( SUM ( v_kpi_calidad_maquina_dia[unidades_retrabajo] ), SUM ( v_kpi_calidad_maquina_dia[unidades_inspeccionadas] ) )",
     "0.00%", "03 Calidad y energía"),
    ("v_kpi_calidad_maquina_dia", "Energía (kWh)",
     "SUM ( v_kpi_calidad_maquina_dia[energia_kwh] )",
     "#,##0.00", "03 Calidad y energía"),
    ("v_kpi_calidad_maquina_dia", "Energía por Unidad Buena",
     "DIVIDE ( SUM ( v_kpi_calidad_maquina_dia[energia_kwh] ), SUM ( v_kpi_calidad_maquina_dia[good_count] ) )",
     "0.0000", "03 Calidad y energía"),
    ("v_kpi_calidad_maquina_dia", "Scrap Rate (Calidad)",
     "DIVIDE ( SUM ( v_kpi_calidad_maquina_dia[scrap_count] ), SUM ( v_kpi_calidad_maquina_dia[total_count] ) )",
     "0.00%", "03 Calidad y energía"),
    # Paradas y causas
    ("v_kpi_parada", "Downtime por Causa (min)",
     "CALCULATE ( SUM ( v_kpi_parada[duracion_min] ), v_kpi_parada[es_planificada] = FALSE () )",
     "#,##0", "06 Paradas"),
    ("v_kpi_parada", "Paradas No Planificadas",
     "CALCULATE ( COUNTROWS ( v_kpi_parada ), v_kpi_parada[es_planificada] = FALSE () )",
     "#,##0", "06 Paradas"),
    ("v_kpi_parada", "Pareto %",
     "DIVIDE ( [Downtime por Causa (min)], CALCULATE ( [Downtime por Causa (min)], ALLSELECTED ( dim_causa ) ) )",
     "0.00%", "06 Paradas"),
    # Alertas
    ("v_alerta_maquina_critica", "Alertas Activas",
     "CALCULATE ( COUNTROWS ( v_alerta_maquina_critica ), v_alerta_maquina_critica[es_ultimo_turno_maquina] = TRUE (), v_alerta_maquina_critica[tiene_alerta] = TRUE () )",
     "#,##0", "07 Alertas"),
    ("v_alerta_maquina_critica", "Alertas Críticas",
     'CALCULATE ( COUNTROWS ( v_alerta_maquina_critica ), v_alerta_maquina_critica[es_ultimo_turno_maquina] = TRUE (), v_alerta_maquina_critica[tiene_alerta] = TRUE (), v_alerta_maquina_critica[severidad] = "critica" )',
     "#,##0", "07 Alertas"),
    ("v_alerta_maquina_critica", "Máquinas en Alerta",
     "CALCULATE ( DISTINCTCOUNT ( v_alerta_maquina_critica[id_maquina] ), v_alerta_maquina_critica[es_ultimo_turno_maquina] = TRUE (), v_alerta_maquina_critica[tiene_alerta] = TRUE () )",
     "#,##0", "07 Alertas"),
    ("v_alerta_maquina_critica", "Temperatura Máxima (°C)",
     "CALCULATE ( MAX ( v_alerta_maquina_critica[max_temperatura_c] ), v_alerta_maquina_critica[es_ultimo_turno_maquina] = TRUE () )",
     "0.0", "07 Alertas"),
    # Umbrales
    ("v_kpi_parametros", "Umbral OEE Alerta",
     "MIN ( v_kpi_parametros[oee_umbral] )",
     "0.00%", "08 Umbrales"),
    ("v_kpi_parametros", "Umbral MTBF (h)",
     "MIN ( v_kpi_parametros[mtbf_umbral_h] )",
     "#,##0.00", "08 Umbrales"),
    ("v_kpi_parametros", "Umbral Temperatura (°C)",
     "MIN ( v_kpi_parametros[temperatura_umbral_c] )",
     "0.0", "08 Umbrales"),
    ("v_kpi_parametros", "Umbral Downtime (min)",
     "MIN ( v_kpi_parametros[downtime_umbral_min] )",
     "#,##0", "08 Umbrales"),
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

TYPE_MAP = {
    "text": ("string", "nvarchar(max)"),
    "character varying": ("string", "nvarchar(max)"),
    "character": ("string", "nvarchar(max)"),
    "integer": ("int64", "integer"),
    "bigint": ("int64", "bigint"),
    "smallint": ("int64", "smallint"),
    "numeric": ("double", "decimal"),
    "double precision": ("double", "double"),
    "real": ("double", "real"),
    "boolean": ("boolean", "bit"),
    "date": ("dateTime", "date"),
    "timestamp without time zone": ("dateTime", "datetime2"),
    "timestamp with time zone": ("dateTime", "datetime2"),
}


def query_columns(table_name: str) -> list[dict]:
    sql = (
        "SELECT json_agg(json_build_object("
        "'name', column_name, 'type', data_type, 'nullable', is_nullable, "
        "'position', ordinal_position) ORDER BY ordinal_position) "
        "FROM information_schema.columns "
        f"WHERE table_schema = 'public' AND table_name = '{table_name}';"
    )
    cmd = [
        "docker", "compose", "exec", "-T", DB_SERVICE, "psql",
        "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", sql,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", cwd=ROOT
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql falló para {table_name}: {result.stderr}")
    raw = result.stdout.strip()
    if not raw or raw == "null":
        raise RuntimeError(f"La tabla/vista {table_name} no existe o no tiene columnas")
    return json.loads(raw)


def tmdl_value(text: str) -> str:
    """Escapa un valor de cadena TMDL entre comillas dobles."""
    return '"' + text.replace('"', '""') + '"'


def column_tmdl(col: dict, hidden: bool, is_key: bool) -> list[str]:
    name = col["name"]
    pg_type = col["type"].lower()
    data_type, provider = TYPE_MAP.get(pg_type, ("string", "nvarchar(max)"))
    lines = [f"\tcolumn {name}", f"\t\tdataType: {data_type}"]
    if is_key:
        lines.append("\t\tisKey")
    if hidden:
        lines.append("\t\tisHidden")
    if data_type == "dateTime":
        lines.append('\t\tformatString: General Date')
    elif data_type == "int64":
        lines.append("\t\tformatString: 0")
    elif data_type == "double":
        lines.append("\t\tformatString: 0.00")
    lines.extend([
        f"\t\tsourceProviderType: {provider}",
        f"\t\tlineageTag: {uuid.uuid4()}",
        "\t\tsummarizeBy: none",
        f"\t\tsourceColumn: {name}",
    ])
    return lines


def table_tmdl(table: dict) -> str:
    name = table["name"]
    hidden = table.get("hidden", set())
    key = table.get("key")
    lines = [f"table {name}", f"\tlineageTag: {uuid.uuid4()}"]

    if table.get("data_category"):
        lines.append(f"\tdataCategory: {table['data_category']}")

    # Medidas
    for t, m, expr, fmt, folder in MEASURES:
        if t != name:
            continue
        lines.append("")
        lines.append(f"\tmeasure '{m}' =")
        for expr_line in expr.splitlines():
            lines.append(f"\t\t\t{expr_line}")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines.append(f"\t\tdisplayFolder: {folder}")
        lines.append(f"\t\tlineageTag: {uuid.uuid4()}")

    # Columnas
    for col in query_columns(name):
        lines.append("")
        lines.extend(column_tmdl(col, col["name"] in hidden, col["name"] == key))

    # Jerarquía
    hierarchy = table.get("hierarchy")
    if hierarchy:
        lines.append("")
        lines.append(f"\thierarchy '{hierarchy['name']}'")
        lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
        for level, column in hierarchy["levels"]:
            lines.append(f"\t\tlevel '{level}'")
            lines.append(f"\t\t\tlineageTag: {uuid.uuid4()}")
            lines.append(f"\t\t\tcolumn: {column}")

    # Partición DirectQuery
    lines.extend([
        "",
        f"\tpartition {name} = m",
        "\t\tmode: directQuery",
        "\t\tsource =",
        "\t\t\t\tlet",
        '\t\t\t\t    Origen = PostgreSQL.Database("127.0.0.1", "metalinova"),',
        f'\t\t\t\t    public_{name} = Origen{{[Schema="public",Item="{name}"]}}[Data]',
        "\t\t\t\tin",
        f"\t\t\t\t    public_{name}",
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ])
    return "\n".join(lines)


def model_tmdl(table_names: list[str]) -> str:
    query_order = json.dumps(table_names, ensure_ascii=False)
    lines = [
        "model Model",
        "\tculture: es-ES",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: es-EC",
        "\tvalueFilterBehavior: independent",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        # Sin fecha/hora automática: el modelo ya tiene dim_tiempo.
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        f"annotation PBI_QueryOrder = {query_order}",
        "",
        'annotation PBI_ProTooling = ["DevMode"]',
        "",
    ]
    for table_name in table_names:
        lines.append(f"ref table {table_name}")
    lines.extend(["", "ref cultureInfo es-ES", ""])
    return "\n".join(lines)


def relationships_tmdl() -> str:
    lines = []
    for from_table, from_col, to_table, to_col in RELATIONSHIPS:
        lines.append(f"relationship {uuid.uuid4()}")
        lines.append(f"\tfromColumn: {from_table}.{from_col}")
        lines.append(f"\ttoColumn: {to_table}.{to_col}")
        lines.append("")
    return "\n".join(lines)


def measures_dax() -> str:
    lines = [
        "// ============================================================================",
        "// Medidas DAX del modelo 006. Se agregan numeradores y denominadores;",
        "// nunca se promedian porcentajes (Constitución §7 y D-013).",
        "// Generado por tools/generate_tmdl.py; editar allí, no en el TMDL.",
        "// ============================================================================",
        "",
    ]
    current = None
    for table, name, expr, fmt, folder in MEASURES:
        if table != current:
            lines.extend([f"// --- {table} ---", ""])
            current = table
        lines.append(f"// [{folder}] {name}")
        lines.append(f"{name} =")
        for expr_line in expr.splitlines():
            lines.append(f"    {expr_line}")
        if fmt:
            lines.append(f"// formato: {fmt}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "powerbi/final/MetalNova.SemanticModel"
    )
    if not output.is_absolute():
        output = ROOT / output
    definition = output / "definition"
    tables_dir = definition / "tables"
    if not definition.exists():
        raise SystemExit(f"No existe {definition}; crea primero el proyecto .pbip")

    # Limpiar tablas y relaciones anteriores para que el modelo sea reproducible.
    if tables_dir.exists():
        shutil.rmtree(tables_dir)
    tables_dir.mkdir(parents=True)
    for stale in (definition / "relationships.tmdl", output / "diagramLayout.json"):
        if stale.exists():
            stale.unlink()

    table_names = [t["name"] for t in TABLES]
    for table in TABLES:
        (tables_dir / f"{table['name']}.tmdl").write_text(
            table_tmdl(table), encoding="utf-8", newline="\n"
        )

    (definition / "model.tmdl").write_text(
        model_tmdl(table_names), encoding="utf-8", newline="\n"
    )
    (definition / "relationships.tmdl").write_text(
        relationships_tmdl(), encoding="utf-8", newline="\n"
    )
    (output.parent / "measures.dax").write_text(
        measures_dax(), encoding="utf-8", newline="\n"
    )

    print(f"Modelo generado en {definition}")
    print(f"Tablas: {len(TABLES)} · Relaciones: {len(RELATIONSHIPS)} · Medidas: {len(MEASURES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
