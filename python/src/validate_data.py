"""Validación independiente de las vistas KPI del incremento 005.

Recalcula cada KPI desde las tablas de hechos (sin usar las vistas) y lo
compara con la vista SQL correspondiente. También comprueba:

- que los joins no multipliquen filas ni conteos (AC-504);
- que los porcentajes se agreguen ponderando numeradores/denominadores y no
  promediando porcentajes (AC-501 y AC-503);
- que los casos borde devuelvan NULL solo cuando el denominador es cero y no
  aparezcan NaN (AC-502);
- que las vistas declaradas en el contrato existan (AC-505).

Los datos son sintéticos. No se imprime la cadena de conexión ni credenciales.
"""

from __future__ import annotations

import argparse
import bisect
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable

from psycopg.rows import dict_row

from common.db import connect

DEFAULT_TOLERANCE = 1e-9
TEMPERATURA_UMBRAL_C = 85.0
MICROPARADA_MIN = 5
FALLA_CORTA_MIN = 30

# Contrato de vistas del incremento 005.
EXPECTED_VIEWS = (
    "v_kpi_parametros",
    "v_kpi_produccion",
    "v_kpi_calidad",
    "v_kpi_parada",
    "v_kpi_mantenimiento",
    "v_kpi_oee_planta_dia",
    "v_kpi_oee_linea_dia",
    "v_kpi_oee_maquina_dia",
    "v_kpi_oee_maquina_turno",
    "v_kpi_oee_producto_dia",
    "v_kpi_mantenimiento_maquina_turno",
    "v_kpi_mantenimiento_maquina_dia",
    "v_kpi_mantenimiento_maquina_mes",
    "v_kpi_mantenimiento_planta_dia",
    "v_kpi_calidad_maquina_dia",
    "v_kpi_calidad_producto_dia",
    "v_kpi_confiabilidad_apoyo_maquina_dia",
    "v_loss_tree",
    "v_loss_tree_maquina_mes",
    "v_alerta_maquina_critica",
)


# ---------------------------------------------------------------------------
# Utilidades numéricas y de reporte
# ---------------------------------------------------------------------------
@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


CHECKS: list[Check] = []


def add_check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append(Check(name, ok, detail))


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bool):
        return float(value)
    return float(value)


def safe_div(num: Any, den: Any) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return float(num) / float(den)


def close(a: Any, b: Any, tol: float) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    fa, fb = as_float(a), as_float(b)
    if fa is None or fb is None:
        return False
    if math.isnan(fa) or math.isnan(fb):
        return False
    return abs(fa - fb) <= max(tol, tol * max(abs(fa), abs(fb)))


def fetch(conn, sql: str, params: tuple | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        return cur.fetchall()


def fetch_one(conn, sql: str):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# Carga de hechos y dimensiones
# ---------------------------------------------------------------------------
def load_data(conn) -> dict[str, Any]:
    return {
        "plantas": fetch(conn, "SELECT id_planta, codigo, nombre FROM dim_planta"),
        "lineas": fetch(
            conn, "SELECT id_linea, id_planta, codigo, nombre FROM dim_linea"
        ),
        "maquinas": fetch(
            conn,
            "SELECT id_maquina, id_linea, codigo, nombre, tipo, criticidad "
            "FROM dim_maquina",
        ),
        "familias": fetch(
            conn, "SELECT id_familia, codigo, nombre FROM dim_familia"
        ),
        "productos": fetch(
            conn,
            "SELECT id_producto, id_familia, codigo, nombre FROM dim_producto",
        ),
        "turnos": fetch(
            conn,
            "SELECT id_turno, codigo, nombre, hora_inicio FROM dim_turno",
        ),
        "tiempos": fetch(
            conn, "SELECT id_tiempo, fecha, anio_mes FROM dim_tiempo"
        ),
        "produccion": fetch(
            conn,
            """
            SELECT id_produccion, id_orden, id_maquina, id_producto, id_turno,
                   id_tiempo, inicio_at, fin_at, tiempo_calendario_min,
                   tiempo_planificado_min, downtime_planificado_min,
                   tiempo_operativo_min, downtime_no_planificado_min,
                   total_count, good_count, scrap_count, ciclo_ideal_segundos,
                   energia_kwh
            FROM fact_produccion
            """,
        ),
        "calidad": fetch(
            conn,
            """
            SELECT id_calidad, id_maquina, id_producto, id_turno, id_tiempo,
                   unidades_inspeccionadas, unidades_buenas,
                   unidades_defectuosas, unidades_retrabajo, es_retrabajo
            FROM fact_calidad
            """,
        ),
        "paradas": fetch(
            conn,
            """
            SELECT id_parada, id_maquina, id_turno, id_tiempo, duracion_min,
                   es_planificada, es_microparada, id_mantenimiento
            FROM fact_parada
            """,
        ),
        "mantenimiento": fetch(
            conn,
            """
            SELECT id_mantenimiento, id_maquina, id_turno, id_tiempo, tipo,
                   estado, duracion_min, costo_estimado_usd
            FROM fact_mantenimiento
            """,
        ),
        "eventos": fetch(
            conn,
            """
            SELECT id_maquina, event_time, temperatura_c
            FROM fact_evento
            WHERE tipo_evento = 'lectura_proceso'
              AND temperatura_c IS NOT NULL
            """,
        ),
        "parametros": fetch(conn, "SELECT * FROM v_kpi_parametros")[0],
    }


def build_maps(data: dict[str, Any]) -> dict[str, Any]:
    maquina_linea = {r["id_maquina"]: r["id_linea"] for r in data["maquinas"]}
    linea_planta = {r["id_linea"]: r["id_planta"] for r in data["lineas"]}
    maquina_planta = {
        id_maquina: linea_planta[id_linea]
        for id_maquina, id_linea in maquina_linea.items()
    }
    return {
        "maquina_linea": maquina_linea,
        "linea_planta": linea_planta,
        "maquina_planta": maquina_planta,
        "producto_familia": {
            r["id_producto"]: r["id_familia"] for r in data["productos"]
        },
        "tiempo_fecha": {r["id_tiempo"]: r["fecha"] for r in data["tiempos"]},
        "tiempo_mes": {r["id_tiempo"]: r["anio_mes"] for r in data["tiempos"]},
        "turno_hora_inicio": {
            r["id_turno"]: r["hora_inicio"] for r in data["turnos"]
        },
        "planta_codigo": {r["id_planta"]: r["codigo"] for r in data["plantas"]},
        "linea_codigo": {r["id_linea"]: r["codigo"] for r in data["lineas"]},
        "maquina_codigo": {
            r["id_maquina"]: r["codigo"] for r in data["maquinas"]
        },
        "producto_codigo": {
            r["id_producto"]: r["codigo"] for r in data["productos"]
        },
        "familia_codigo": {
            r["id_familia"]: r["codigo"] for r in data["familias"]
        },
        "turno_codigo": {r["id_turno"]: r["codigo"] for r in data["turnos"]},
    }


# ---------------------------------------------------------------------------
# Agregación de producción
# ---------------------------------------------------------------------------
def empty_prod() -> dict[str, Any]:
    return {
        "filas": 0,
        "calendario": 0,
        "planificado": 0,
        "downtime_plan": 0,
        "operativo": 0,
        "downtime": 0,
        "total": 0,
        "good": 0,
        "scrap": 0,
        "ideal": 0.0,
        "energia": 0.0,
        "turnos": set(),
    }


def build_production(data: dict[str, Any], maps: dict[str, Any]) -> dict[str, Any]:
    names = ("total", "planta", "linea", "maquina", "maquina_turno", "producto")
    stores: dict[str, defaultdict] = {
        name: defaultdict(empty_prod) for name in names
    }

    for row in data["produccion"]:
        id_maquina = row["id_maquina"]
        id_turno = row["id_turno"]
        id_tiempo = row["id_tiempo"]
        id_producto = row["id_producto"]
        id_linea = maps["maquina_linea"][id_maquina]
        id_planta = maps["linea_planta"][id_linea]
        fecha = maps["tiempo_fecha"][id_tiempo]

        keys = (
            ("total", ()),
            ("planta", (fecha, id_planta)),
            ("linea", (fecha, id_linea)),
            ("maquina", (fecha, id_maquina)),
            ("maquina_turno", (fecha, id_maquina, id_turno)),
            ("producto", (fecha, id_producto)),
        )

        ideal = (
            float(row["ciclo_ideal_segundos"]) * int(row["total_count"]) / 60.0
        )
        energia = float(row["energia_kwh"])

        for name, key in keys:
            agg = stores[name][key]
            agg["filas"] += 1
            agg["calendario"] += int(row["tiempo_calendario_min"])
            agg["planificado"] += int(row["tiempo_planificado_min"])
            agg["downtime_plan"] += int(row["downtime_planificado_min"])
            agg["operativo"] += int(row["tiempo_operativo_min"])
            agg["downtime"] += int(row["downtime_no_planificado_min"])
            agg["total"] += int(row["total_count"])
            agg["good"] += int(row["good_count"])
            agg["scrap"] += int(row["scrap_count"])
            agg["ideal"] += ideal
            agg["energia"] += energia
            agg["turnos"].add((id_maquina, id_turno))

    return stores


def prod_metrics(agg: dict[str, Any], include_turnos: bool = True) -> dict[str, Any]:
    disponibilidad = safe_div(agg["operativo"], agg["planificado"])
    rendimiento = safe_div(agg["ideal"], agg["operativo"])
    calidad = safe_div(agg["good"], agg["total"])
    oee = (
        disponibilidad * rendimiento * calidad
        if None not in (disponibilidad, rendimiento, calidad)
        else None
    )
    metrics = {
        "tiempo_calendario_min": agg["calendario"],
        "tiempo_planificado_min": agg["planificado"],
        "downtime_planificado_min": agg["downtime_plan"],
        "tiempo_operativo_min": agg["operativo"],
        "downtime_no_planificado_min": agg["downtime"],
        "total_count": agg["total"],
        "good_count": agg["good"],
        "scrap_count": agg["scrap"],
        "minutos_ideales": agg["ideal"],
        "energia_kwh": agg["energia"],
        "filas_produccion": agg["filas"],
        "disponibilidad": disponibilidad,
        "rendimiento": rendimiento,
        "calidad": calidad,
        "oee": oee,
        "scrap_rate": safe_div(agg["scrap"], agg["total"]),
        "energia_por_unidad_buena": safe_div(agg["energia"], agg["good"]),
        "downtime_no_planificado_pct": safe_div(
            agg["downtime"], agg["planificado"]
        ),
    }
    if include_turnos:
        metrics["turnos_maquina"] = len(agg["turnos"])
    return metrics


def build_production_metrics(stores: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {
            key: prod_metrics(
                agg,
                include_turnos=name != "maquina_turno",
            )
            for key, agg in store.items()
        }
        for name, store in stores.items()
    }


# ---------------------------------------------------------------------------
# Agregación de calidad
# ---------------------------------------------------------------------------
def empty_cal() -> dict[str, Any]:
    return {
        "inspecciones": 0,
        "insp": 0,
        "good": 0,
        "defect": 0,
        "retrabajo": 0,
        "con_retrabajo": 0,
    }


def build_quality(data: dict[str, Any], maps: dict[str, Any]) -> dict[str, Any]:
    names = ("total", "maquina", "producto")
    stores: dict[str, defaultdict] = {
        name: defaultdict(empty_cal) for name in names
    }
    for row in data["calidad"]:
        id_maquina = row["id_maquina"]
        id_producto = row["id_producto"]
        id_tiempo = row["id_tiempo"]
        fecha = maps["tiempo_fecha"][id_tiempo]
        keys = (
            ("total", ()),
            ("maquina", (fecha, id_maquina)),
            ("producto", (fecha, id_producto)),
        )
        for name, key in keys:
            agg = stores[name][key]
            agg["inspecciones"] += 1
            agg["insp"] += int(row["unidades_inspeccionadas"])
            agg["good"] += int(row["unidades_buenas"])
            agg["defect"] += int(row["unidades_defectuosas"])
            agg["retrabajo"] += int(row["unidades_retrabajo"])
            if row["es_retrabajo"]:
                agg["con_retrabajo"] += 1
    return {
        name: {key: cal_metrics(agg) for key, agg in store.items()}
        for name, store in stores.items()
    }


def cal_metrics(agg: dict[str, Any]) -> dict[str, Any]:
    return {
        "inspecciones": agg["inspecciones"],
        "unidades_inspeccionadas": agg["insp"],
        "unidades_buenas_inspeccion": agg["good"],
        "unidades_defectuosas": agg["defect"],
        "unidades_retrabajo": agg["retrabajo"],
        "inspecciones_con_retrabajo": agg["con_retrabajo"],
        "tasa_defectos": safe_div(agg["defect"], agg["insp"]),
        "tasa_retrabajo": safe_div(agg["retrabajo"], agg["insp"]),
        "fpy": safe_div(agg["insp"] - agg["retrabajo"], agg["insp"]),
    }


# ---------------------------------------------------------------------------
# Agregación de confiabilidad / mantenimiento
# ---------------------------------------------------------------------------
def empty_rel() -> dict[str, Any]:
    return {
        "has_prod": False,
        "calendario": 0,
        "planificado": 0,
        "downtime_plan": 0,
        "operativo": 0,
        "downtime_prod": 0,
        "total": 0,
        "good": 0,
        "inicio": None,
        "fin": None,
        "paradas": 0,
        "minutos_parada": 0,
        "fallas": 0,
        "minutos_fallas": 0,
        "micro": 0,
        "minutos_micro": 0,
        "fallas_cortas": 0,
        "minutos_fallas_cortas": 0,
        "reparaciones": 0,
        "minutos_reparacion": 0,
        "intervenciones": 0,
        "minutos_intervencion": 0,
        "costo": 0.0,
    }


def build_rel(data: dict[str, Any]) -> dict[tuple, dict[str, Any]]:
    rel: defaultdict[tuple, dict[str, Any]] = defaultdict(empty_rel)
    for row in data["produccion"]:
        key = (row["id_maquina"], row["id_turno"], row["id_tiempo"])
        agg = rel[key]
        agg["has_prod"] = True
        agg["calendario"] += int(row["tiempo_calendario_min"])
        agg["planificado"] += int(row["tiempo_planificado_min"])
        agg["downtime_plan"] += int(row["downtime_planificado_min"])
        agg["operativo"] += int(row["tiempo_operativo_min"])
        agg["downtime_prod"] += int(row["downtime_no_planificado_min"])
        agg["total"] += int(row["total_count"])
        agg["good"] += int(row["good_count"])
        start, end = row["inicio_at"], row["fin_at"]
        agg["inicio"] = start if agg["inicio"] is None else min(agg["inicio"], start)
        agg["fin"] = end if agg["fin"] is None else max(agg["fin"], end)

    for row in data["paradas"]:
        key = (row["id_maquina"], row["id_turno"], row["id_tiempo"])
        agg = rel[key]
        duracion = int(row["duracion_min"])
        planificada = bool(row["es_planificada"])
        tiene_cmms = row["id_mantenimiento"] is not None
        micro = (not planificada) and duracion < MICROPARADA_MIN and not tiene_cmms
        falla = (not planificada) and not micro
        if not planificada:
            agg["paradas"] += 1
            agg["minutos_parada"] += duracion
        if falla:
            agg["fallas"] += 1
            agg["minutos_fallas"] += duracion
        if micro:
            agg["micro"] += 1
            agg["minutos_micro"] += duracion
        if falla and duracion < FALLA_CORTA_MIN:
            agg["fallas_cortas"] += 1
            agg["minutos_fallas_cortas"] += duracion

    for row in data["mantenimiento"]:
        key = (row["id_maquina"], row["id_turno"], row["id_tiempo"])
        agg = rel[key]
        duracion = int(row["duracion_min"])
        agg["intervenciones"] += 1
        agg["minutos_intervencion"] += duracion
        agg["costo"] += float(row["costo_estimado_usd"])
        if row["tipo"] == "correctivo" and row["estado"] == "cerrada":
            agg["reparaciones"] += 1
            agg["minutos_reparacion"] += duracion

    return dict(rel)


def rel_metrics(agg: dict[str, Any]) -> dict[str, Any]:
    runtime = agg["operativo"]
    downtime = agg["downtime_prod"] if agg["has_prod"] else agg["minutos_parada"]
    runtime_h = runtime / 60.0
    return {
        "tiempo_calendario_min": agg["calendario"],
        "tiempo_planificado_min": agg["planificado"],
        "downtime_planificado_min": agg["downtime_plan"],
        "tiempo_operativo_min": runtime,
        "downtime_no_planificado_min": downtime,
        "total_count": agg["total"],
        "good_count": agg["good"],
        "paradas_no_planificadas": agg["paradas"],
        "minutos_no_planificados_parada": agg["minutos_parada"],
        "fallas": agg["fallas"],
        "minutos_fallas": agg["minutos_fallas"],
        "microparadas": agg["micro"],
        "minutos_microparadas": agg["minutos_micro"],
        "fallas_cortas": agg["fallas_cortas"],
        "minutos_fallas_cortas": agg["minutos_fallas_cortas"],
        "reparaciones": agg["reparaciones"],
        "minutos_reparacion": agg["minutos_reparacion"],
        "intervenciones": agg["intervenciones"],
        "minutos_intervencion": agg["minutos_intervencion"],
        "costo_mantenimiento_usd": agg["costo"],
        "tiempo_operativo_h": runtime_h,
        "mtbf_h": (
            runtime_h / agg["fallas"]
            if runtime > 0 and agg["fallas"] > 0
            else None
        ),
        "mttr_min": safe_div(agg["minutos_reparacion"], agg["reparaciones"]),
        "downtime_no_planificado_pct": safe_div(downtime, agg["planificado"]),
        "mtbf_corto_h": (
            runtime_h / agg["fallas_cortas"]
            if runtime > 0 and agg["fallas_cortas"] > 0
            else None
        ),
        "fallas_cortas_por_100h": (
            100.0 * agg["fallas_cortas"] / runtime_h if runtime > 0 else None
        ),
        "microparadas_por_100h": (
            100.0 * agg["micro"] / runtime_h if runtime > 0 else None
        ),
        "duracion_media_micro_min": safe_div(
            agg["minutos_micro"], agg["micro"]
        ),
        "duracion_media_falla_min": safe_div(
            agg["minutos_fallas"], agg["fallas"]
        ),
    }


def empty_rel_group() -> dict[str, Any]:
    return {
        "entradas": 0,
        "dias": set(),
        "maquinas_con_fallas": set(),
        "maquinas_con_microparadas": set(),
        "calendario": 0,
        "planificado": 0,
        "downtime_plan": 0,
        "operativo": 0,
        "downtime": 0,
        "total": 0,
        "good": 0,
        "paradas": 0,
        "minutos_parada": 0,
        "fallas": 0,
        "minutos_fallas": 0,
        "micro": 0,
        "minutos_micro": 0,
        "fallas_cortas": 0,
        "minutos_fallas_cortas": 0,
        "reparaciones": 0,
        "minutos_reparacion": 0,
        "intervenciones": 0,
        "minutos_intervencion": 0,
        "costo": 0.0,
    }


def aggregate_rel(
    rel: dict[tuple, dict[str, Any]],
    maps: dict[str, Any],
    key_func: Callable[[int, int, int], tuple],
) -> dict[tuple, dict[str, Any]]:
    groups: defaultdict[tuple, dict[str, Any]] = defaultdict(empty_rel_group)
    for (id_maquina, id_turno, id_tiempo), agg in rel.items():
        fecha = maps["tiempo_fecha"][id_tiempo]
        key = key_func(id_maquina, id_turno, id_tiempo)
        group = groups[key]
        group["entradas"] += 1
        group["dias"].add(fecha)
        group["calendario"] += agg["calendario"]
        group["planificado"] += agg["planificado"]
        group["downtime_plan"] += agg["downtime_plan"]
        group["operativo"] += agg["operativo"]
        group["downtime"] += (
            agg["downtime_prod"] if agg["has_prod"] else agg["minutos_parada"]
        )
        group["total"] += agg["total"]
        group["good"] += agg["good"]
        group["paradas"] += agg["paradas"]
        group["minutos_parada"] += agg["minutos_parada"]
        group["fallas"] += agg["fallas"]
        group["minutos_fallas"] += agg["minutos_fallas"]
        group["micro"] += agg["micro"]
        group["minutos_micro"] += agg["minutos_micro"]
        group["fallas_cortas"] += agg["fallas_cortas"]
        group["minutos_fallas_cortas"] += agg["minutos_fallas_cortas"]
        group["reparaciones"] += agg["reparaciones"]
        group["minutos_reparacion"] += agg["minutos_reparacion"]
        group["intervenciones"] += agg["intervenciones"]
        group["minutos_intervencion"] += agg["minutos_intervencion"]
        group["costo"] += agg["costo"]
        if agg["fallas"] > 0:
            group["maquinas_con_fallas"].add(id_maquina)
        if agg["micro"] > 0:
            group["maquinas_con_microparadas"].add(id_maquina)
    return dict(groups)


def rel_group_metrics(group: dict[str, Any]) -> dict[str, Any]:
    runtime = group["operativo"]
    runtime_h = runtime / 60.0
    return {
        "tiempo_calendario_min": group["calendario"],
        "tiempo_planificado_min": group["planificado"],
        "downtime_planificado_min": group["downtime_plan"],
        "tiempo_operativo_min": runtime,
        "downtime_no_planificado_min": group["downtime"],
        "total_count": group["total"],
        "good_count": group["good"],
        "paradas_no_planificadas": group["paradas"],
        "minutos_no_planificados_parada": group["minutos_parada"],
        "fallas": group["fallas"],
        "minutos_fallas": group["minutos_fallas"],
        "microparadas": group["micro"],
        "minutos_microparadas": group["minutos_micro"],
        "fallas_cortas": group["fallas_cortas"],
        "minutos_fallas_cortas": group["minutos_fallas_cortas"],
        "reparaciones": group["reparaciones"],
        "minutos_reparacion": group["minutos_reparacion"],
        "intervenciones": group["intervenciones"],
        "minutos_intervencion": group["minutos_intervencion"],
        "costo_mantenimiento_usd": group["costo"],
        "turnos_maquina": group["entradas"],
        "dias_con_datos": len(group["dias"]),
        "maquinas_con_fallas": len(group["maquinas_con_fallas"]),
        "maquinas_con_microparadas": len(group["maquinas_con_microparadas"]),
        "tiempo_operativo_h": runtime_h,
        "mtbf_h": (
            runtime_h / group["fallas"]
            if runtime > 0 and group["fallas"] > 0
            else None
        ),
        "mttr_min": safe_div(group["minutos_reparacion"], group["reparaciones"]),
        "downtime_no_planificado_pct": safe_div(
            group["downtime"], group["planificado"]
        ),
        "mtbf_corto_h": (
            runtime_h / group["fallas_cortas"]
            if runtime > 0 and group["fallas_cortas"] > 0
            else None
        ),
        "fallas_cortas_por_100h": (
            100.0 * group["fallas_cortas"] / runtime_h if runtime > 0 else None
        ),
        "microparadas_por_100h": (
            100.0 * group["micro"] / runtime_h if runtime > 0 else None
        ),
        "duracion_media_micro_min": safe_div(
            group["minutos_micro"], group["micro"]
        ),
        "duracion_media_falla_min": safe_div(
            group["minutos_fallas"], group["fallas"]
        ),
    }


def build_rel_metrics(
    rel: dict[tuple, dict[str, Any]],
    maps: dict[str, Any],
) -> dict[str, Any]:
    turno = {
        (maps["tiempo_fecha"][id_tiempo], id_maquina, id_turno): rel_metrics(agg)
        for (id_maquina, id_turno, id_tiempo), agg in rel.items()
    }
    dia_groups = aggregate_rel(
        rel, maps, lambda m, t, d: (maps["tiempo_fecha"][d], m)
    )
    dia = {
        key: rel_group_metrics(group) for key, group in dia_groups.items()
    }
    mes_groups = aggregate_rel(
        rel, maps, lambda m, t, d: (maps["tiempo_mes"][d], m)
    )
    mes = {
        key: rel_group_metrics(group) for key, group in mes_groups.items()
    }
    planta_groups = aggregate_rel(
        rel,
        maps,
        lambda m, t, d: (maps["tiempo_fecha"][d], maps["maquina_planta"][m]),
    )
    planta = {
        key: rel_group_metrics(group) for key, group in planta_groups.items()
    }
    return {"turno": turno, "dia": dia, "mes": mes, "planta": planta}


# ---------------------------------------------------------------------------
# Comparaciones genéricas vista ↔ Python
# ---------------------------------------------------------------------------
def compare_view(
    conn,
    label: str,
    sql: str,
    python_by_key: dict[tuple, dict[str, Any]],
    key_fields: tuple[str, ...],
    metrics: tuple[str, ...],
    tol: float,
    *,
    extra_checks: Callable[[dict], None] | None = None,
) -> None:
    rows = fetch(conn, sql)
    seen: set[tuple] = set()
    mismatches: list[str] = []
    max_diffs: dict[str, float] = {}
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        seen.add(key)
        expected = python_by_key.get(key)
        if expected is None:
            mismatches.append(f"fila extra {key}")
            continue
        if extra_checks is not None:
            extra_checks(row)
        for metric in metrics:
            actual = row[metric]
            wanted = expected.get(metric)
            if not close(actual, wanted, tol):
                if len(mismatches) < 5:
                    mismatches.append(
                        f"{key} {metric}: vista={actual!r} python={wanted!r}"
                    )
            elif actual is not None and not isinstance(actual, (bool, str)):
                diff = abs(as_float(actual) - float(wanted))
                max_diffs[metric] = max(max_diffs.get(metric, 0.0), diff)
    missing = len(set(python_by_key) - seen)
    ok = not mismatches and missing == 0
    detail = f"{len(rows)} filas; faltantes={missing}"
    if max_diffs:
        worst = max(max_diffs.items(), key=lambda item: item[1])
        detail += f"; dif. máx={worst[0]} {worst[1]:.3e}"
    if mismatches:
        detail += "; " + " | ".join(mismatches[:3])
    add_check(label, ok, detail)


def sum_rows(rows: list[dict], field: str) -> float:
    return sum(as_float(r[field]) or 0.0 for r in rows)


def check_additivity(
    label: str,
    rows: list[dict],
    fields: tuple[str, ...],
    expected: dict[str, Any],
    tol: float,
) -> None:
    mismatches = []
    for field in fields:
        total = sum_rows(rows, field)
        wanted = expected.get(field)
        if not close(total, wanted, tol):
            mismatches.append(f"{field}: vista={total!r} python={wanted!r}")
    add_check(
        label,
        not mismatches,
        "sumas aditivas OK" if not mismatches else "; ".join(mismatches),
    )


# ---------------------------------------------------------------------------
# Cálculos auxiliares: calidad combinada, loss tree y alertas
# ---------------------------------------------------------------------------
def zero_prod_metrics() -> dict[str, Any]:
    return {
        "tiempo_calendario_min": 0,
        "tiempo_planificado_min": 0,
        "downtime_planificado_min": 0,
        "tiempo_operativo_min": 0,
        "downtime_no_planificado_min": 0,
        "total_count": 0,
        "good_count": 0,
        "scrap_count": 0,
        "minutos_ideales": 0.0,
        "energia_kwh": 0.0,
        "filas_produccion": 0,
        "disponibilidad": None,
        "rendimiento": None,
        "calidad": None,
        "oee": None,
        "scrap_rate": None,
        "energia_por_unidad_buena": None,
        "downtime_no_planificado_pct": None,
    }


def zero_cal_metrics() -> dict[str, Any]:
    return {
        "inspecciones": 0,
        "unidades_inspeccionadas": 0,
        "unidades_buenas_inspeccion": 0,
        "unidades_defectuosas": 0,
        "unidades_retrabajo": 0,
        "inspecciones_con_retrabajo": 0,
        "tasa_defectos": None,
        "tasa_retrabajo": None,
        "fpy": None,
    }


def build_calidad_combined(
    prod: dict[tuple, dict[str, Any]],
    quality: dict[tuple, dict[str, Any]],
) -> dict[tuple, dict[str, Any]]:
    combined: dict[tuple, dict[str, Any]] = {}
    for key in set(prod) | set(quality):
        p = prod.get(key, zero_prod_metrics())
        q = quality.get(key, zero_cal_metrics())
        combined[key] = {
            "tiempo_planificado_min": p["tiempo_planificado_min"],
            "tiempo_operativo_min": p["tiempo_operativo_min"],
            "downtime_no_planificado_min": p["downtime_no_planificado_min"],
            "total_count": p["total_count"],
            "good_count": p["good_count"],
            "scrap_count": p["scrap_count"],
            "energia_kwh": p["energia_kwh"],
            "scrap_rate": p["scrap_rate"],
            "energia_por_unidad_buena": p["energia_por_unidad_buena"],
            "downtime_no_planificado_pct": p["downtime_no_planificado_pct"],
            **q,
        }
    return combined


def build_loss(
    data: dict[str, Any], maps: dict[str, Any]
) -> tuple[dict[int, dict[str, Any]], dict[tuple, dict[str, Any]]]:
    rows: dict[int, dict[str, Any]] = {}
    months: defaultdict[tuple, dict[str, Any]] = defaultdict(
        lambda: {
            "planificado": 0,
            "operativo": 0,
            "ideal": 0.0,
            "total": 0,
            "good": 0,
            "scrap": 0,
            "loss_dispo": 0.0,
            "loss_rend": 0.0,
            "loss_cal": 0.0,
            "loss_total": 0.0,
            "potencial": 0.0,
            "no_producidas": 0.0,
            "filas": 0,
            "dias": set(),
        }
    )
    for row in data["produccion"]:
        planned = int(row["tiempo_planificado_min"])
        runtime = int(row["tiempo_operativo_min"])
        total = int(row["total_count"])
        good = int(row["good_count"])
        scrap = int(row["scrap_count"])
        cycle = float(row["ciclo_ideal_segundos"])
        ideal = cycle * total / 60.0
        potential = runtime * 60.0 / cycle if cycle > 0 else None
        loss_dispo = float(row["downtime_no_planificado_min"])
        loss_rend = max(runtime - ideal, 0.0)
        loss_cal = scrap * cycle / 60.0
        loss_total = loss_dispo + loss_rend + loss_cal
        A = safe_div(runtime, planned)
        P = safe_div(ideal, runtime)
        Q = safe_div(good, total)
        oee = A * P * Q if None not in (A, P, Q) else None
        no_producidas = max(potential - total, 0.0) if potential is not None else 0.0
        metrics = {
            "tiempo_planificado_min": planned,
            "tiempo_operativo_min": runtime,
            "total_count": total,
            "good_count": good,
            "scrap_count": scrap,
            "minutos_ideales": ideal,
            "oee": oee,
            "minutos_perdidos_disponibilidad": loss_dispo,
            "minutos_perdidos_rendimiento": loss_rend,
            "minutos_perdidos_calidad": loss_cal,
            "minutos_perdidos_total": loss_total,
            "unidades_potenciales": potential or 0.0,
            "unidades_no_producidas": no_producidas,
            "unidades_scrap": scrap,
            "participacion_disponibilidad": safe_div(loss_dispo, loss_total),
            "participacion_rendimiento": safe_div(loss_rend, loss_total),
            "participacion_calidad": safe_div(loss_cal, loss_total),
        }
        rows[row["id_produccion"]] = metrics

        id_tiempo = row["id_tiempo"]
        key = (maps["tiempo_mes"][id_tiempo], row["id_maquina"])
        month = months[key]
        month["planificado"] += planned
        month["operativo"] += runtime
        month["ideal"] += ideal
        month["total"] += total
        month["good"] += good
        month["scrap"] += scrap
        month["loss_dispo"] += loss_dispo
        month["loss_rend"] += loss_rend
        month["loss_cal"] += loss_cal
        month["loss_total"] += loss_total
        month["potencial"] += potential or 0.0
        month["no_producidas"] += no_producidas
        month["filas"] += 1
        month["dias"].add(maps["tiempo_fecha"][id_tiempo])

    monthly: dict[tuple, dict[str, Any]] = {}
    for key, m in months.items():
        A = safe_div(m["operativo"], m["planificado"])
        P = safe_div(m["ideal"], m["operativo"])
        Q = safe_div(m["good"], m["total"])
        oee = A * P * Q if None not in (A, P, Q) else None
        monthly[key] = {
            "tiempo_planificado_min": m["planificado"],
            "tiempo_operativo_min": m["operativo"],
            "minutos_ideales": m["ideal"],
            "total_count": m["total"],
            "good_count": m["good"],
            "scrap_count": m["scrap"],
            "minutos_perdidos_disponibilidad": m["loss_dispo"],
            "minutos_perdidos_rendimiento": m["loss_rend"],
            "minutos_perdidos_calidad": m["loss_cal"],
            "minutos_perdidos_total": m["loss_total"],
            "unidades_potenciales": m["potencial"],
            "unidades_no_producidas": m["no_producidas"],
            "unidades_scrap": m["scrap"],
            "filas_produccion": m["filas"],
            "dias_con_datos": len(m["dias"]),
            "disponibilidad": A,
            "rendimiento": P,
            "calidad": Q,
            "oee": oee,
            "participacion_disponibilidad": safe_div(
                m["loss_dispo"], m["loss_total"]
            ),
            "participacion_rendimiento": safe_div(
                m["loss_rend"], m["loss_total"]
            ),
            "participacion_calidad": safe_div(m["loss_cal"], m["loss_total"]),
        }
    return rows, monthly


def build_alerts(
    data: dict[str, Any],
    maps: dict[str, Any],
    rel: dict[tuple, dict[str, Any]],
    rel_by_turno: dict[tuple, dict[str, Any]],
    prod_turno: dict[tuple, dict[str, Any]],
) -> dict[tuple, dict[str, Any]]:
    # Rangos de turno por máquina para mapear las lecturas de temperatura.
    ranges: defaultdict[int, list[tuple]] = defaultdict(list)
    for (id_maquina, id_turno, id_tiempo), agg in rel.items():
        if not agg["has_prod"] or agg["inicio"] is None or agg["fin"] is None:
            continue
        ranges[id_maquina].append(
            (agg["inicio"], agg["fin"], id_turno, id_tiempo)
        )
    starts: dict[int, list[datetime]] = {}
    for id_maquina, items in ranges.items():
        items.sort(key=lambda item: item[0])
        dedup: list[tuple] = []
        for item in items:
            if dedup and dedup[-1][2:] == item[2:]:
                prev = dedup[-1]
                dedup[-1] = (
                    min(prev[0], item[0]),
                    max(prev[1], item[1]),
                    item[2],
                    item[3],
                )
            else:
                dedup.append(item)
        ranges[id_maquina] = dedup
        starts[id_maquina] = [item[0] for item in dedup]

    temp: defaultdict[tuple, list[float]] = defaultdict(list)
    for row in data["eventos"]:
        id_maquina = row["id_maquina"]
        if id_maquina not in ranges:
            continue
        when = row["event_time"]
        index = bisect.bisect_right(starts[id_maquina], when) - 1
        if index < 0:
            continue
        inicio, fin, id_turno, id_tiempo = ranges[id_maquina][index]
        if not (inicio <= when < fin):
            continue
        temp[(id_maquina, id_turno, id_tiempo)].append(
            float(row["temperatura_c"])
        )

    latest: dict[int, tuple] = {}
    for (id_maquina, id_turno, id_tiempo), agg in rel.items():
        fecha = maps["tiempo_fecha"][id_tiempo]
        inicio = datetime.combine(
            fecha, maps["turno_hora_inicio"][id_turno]
        )
        candidate = (fecha, inicio)
        if id_maquina not in latest or candidate > latest[id_maquina]:
            latest[id_maquina] = candidate

    alerts: dict[tuple, dict[str, Any]] = {}
    for (id_maquina, id_turno, id_tiempo), agg in rel.items():
        fecha = maps["tiempo_fecha"][id_tiempo]
        turno_key = (fecha, id_maquina, id_turno)
        metrics = rel_by_turno[turno_key]
        production = prod_turno.get(turno_key)
        oee = production["oee"] if production is not None else None
        lecturas = temp.get((id_maquina, id_turno, id_tiempo), [])
        altas = sum(1 for value in lecturas if value > TEMPERATURA_UMBRAL_C)
        max_temp = max(lecturas) if lecturas else 0.0
        mtbf = metrics["mtbf_h"]
        downtime = metrics["downtime_no_planificado_min"]
        cumple_oee = oee is not None and oee < 0.55
        cumple_mtbf = mtbf is not None and mtbf < 20
        cumple_temp = altas >= 2
        cumple_downtime = downtime > 120
        condiciones = sum(
            (cumple_oee, cumple_mtbf, cumple_temp, cumple_downtime)
        )
        severidad = (
            "sin_alerta"
            if condiciones == 0
            else "alerta"
            if condiciones == 1
            else "critica"
        )
        inicio = datetime.combine(
            fecha, maps["turno_hora_inicio"][id_turno]
        )
        alerts[turno_key] = {
            "oee": oee,
            "disponibilidad": production["disponibilidad"] if production else None,
            "rendimiento": production["rendimiento"] if production else None,
            "calidad": production["calidad"] if production else None,
            "mtbf_h": mtbf,
            "mttr_min": metrics["mttr_min"],
            "downtime_no_planificado_min": downtime,
            "lecturas_temp_alta": altas,
            "max_temperatura_c": max_temp,
            "minutos_temp_alta_estimados": altas * 15,
            "cumple_oee": cumple_oee,
            "cumple_mtbf": cumple_mtbf,
            "cumple_temperatura": cumple_temp,
            "cumple_downtime": cumple_downtime,
            "condiciones_cumplidas": condiciones,
            "severidad": severidad,
            "es_ultimo_turno_maquina": latest[id_maquina] == (fecha, inicio),
        }
    return alerts


# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------
def validate_contract(conn) -> None:
    rows = fetch(
        conn,
        "SELECT table_name FROM information_schema.views "
        "WHERE table_schema = 'public' AND (table_name LIKE 'v_kpi%' "
        "OR table_name IN ('v_loss_tree', 'v_loss_tree_maquina_mes', "
        "'v_alerta_maquina_critica'))",
    )
    existing = {r["table_name"] for r in rows}
    missing = sorted(set(EXPECTED_VIEWS) - existing)
    add_check(
        "AC-505 contrato de vistas KPI presente",
        not missing,
        f"{len(existing)} vistas; faltantes={missing or 'ninguna'}",
    )
    params = fetch(conn, "SELECT * FROM v_kpi_parametros")[0]
    expected = {
        "microparada_min": 5,
        "falla_corta_min": 30,
        "mtbf_umbral_h": 20,
        "oee_umbral": 0.55,
        "downtime_umbral_min": 120,
        "temperatura_umbral_c": 85,
        "temperatura_ventana_min": 15,
        "temperatura_lecturas_min": 2,
    }
    bad = [
        f"{key}={params[key]!r}"
        for key, value in expected.items()
        if not close(params[key], value, 0)
    ]
    add_check(
        "Parámetros de reglas alineados con la Constitución",
        not bad,
        "OK" if not bad else "; ".join(bad),
    )


def validate_raw_views(
    conn, data: dict[str, Any], maps: dict[str, Any], tol: float
) -> None:
    # --- v_kpi_produccion: métricas por fila --------------------------------
    python = {}
    for row in data["produccion"]:
        cycle = float(row["ciclo_ideal_segundos"])
        total = int(row["total_count"])
        good = int(row["good_count"])
        scrap = int(row["scrap_count"])
        runtime = int(row["tiempo_operativo_min"])
        planned = int(row["tiempo_planificado_min"])
        ideal = cycle * total / 60.0
        A = safe_div(runtime, planned)
        P = safe_div(ideal, runtime)
        Q = safe_div(good, total)
        python[(row["id_produccion"],)] = {
            "disponibilidad": A,
            "rendimiento": P,
            "calidad": Q,
            "oee": A * P * Q if None not in (A, P, Q) else None,
            "scrap_rate": safe_div(scrap, total),
            "energia_por_unidad_buena": safe_div(
                float(row["energia_kwh"]), good
            ),
            "downtime_no_planificado_pct": safe_div(
                int(row["downtime_no_planificado_min"]), planned
            ),
            "minutos_ideales": ideal,
            "unidades_potenciales": runtime * 60.0 / cycle if cycle else None,
        }
    compare_view(
        conn,
        "AC-501 v_kpi_produccion (A/P/Q/OEE por fila)",
        "SELECT id_produccion, disponibilidad, rendimiento, calidad, oee, "
        "scrap_rate, energia_por_unidad_buena, downtime_no_planificado_pct, "
        "minutos_ideales, unidades_potenciales FROM v_kpi_produccion",
        python,
        ("id_produccion",),
        (
            "disponibilidad",
            "rendimiento",
            "calidad",
            "oee",
            "scrap_rate",
            "energia_por_unidad_buena",
            "downtime_no_planificado_pct",
            "minutos_ideales",
            "unidades_potenciales",
        ),
        tol,
    )

    # --- v_kpi_calidad: FPY y tasas por inspección --------------------------
    python = {}
    for row in data["calidad"]:
        insp = int(row["unidades_inspeccionadas"])
        retrabajo = int(row["unidades_retrabajo"])
        python[(row["id_calidad"],)] = {
            "tasa_defectos": safe_div(
                int(row["unidades_defectuosas"]), insp
            ),
            "tasa_retrabajo": safe_div(retrabajo, insp),
            "fpy": safe_div(insp - retrabajo, insp),
        }
    compare_view(
        conn,
        "AC-501 v_kpi_calidad (FPY por inspección)",
        "SELECT id_calidad, tasa_defectos, tasa_retrabajo, fpy "
        "FROM v_kpi_calidad",
        python,
        ("id_calidad",),
        ("tasa_defectos", "tasa_retrabajo", "fpy"),
        tol,
    )

    # --- v_kpi_parada: regla G6 --------------------------------------------
    python = {}
    for row in data["paradas"]:
        planificada = bool(row["es_planificada"])
        duracion = int(row["duracion_min"])
        tiene_cmms = row["id_mantenimiento"] is not None
        micro = (not planificada) and duracion < MICROPARADA_MIN and not tiene_cmms
        falla = (not planificada) and not micro
        python[(row["id_parada"],)] = {
            "es_microparada_regla": micro,
            "es_falla": falla,
            "es_falla_corta": falla and duracion < FALLA_CORTA_MIN,
            "clasificacion": (
                "planificada" if planificada else "microparada" if micro else "falla"
            ),
        }
    compare_view(
        conn,
        "AC-501 v_kpi_parada (regla G6)",
        "SELECT id_parada, es_microparada_regla, es_falla, es_falla_corta, "
        "clasificacion FROM v_kpi_parada",
        python,
        ("id_parada",),
        ("es_microparada_regla", "es_falla", "es_falla_corta", "clasificacion"),
        tol,
    )

    # --- v_kpi_mantenimiento: correctivo cerrado ---------------------------
    python = {
        (row["id_mantenimiento"],): {
            "es_correctivo_cerrado": (
                row["tipo"] == "correctivo" and row["estado"] == "cerrada"
            )
        }
        for row in data["mantenimiento"]
    }
    compare_view(
        conn,
        "AC-501 v_kpi_mantenimiento (correctivo cerrado)",
        "SELECT id_mantenimiento, es_correctivo_cerrado FROM v_kpi_mantenimiento",
        python,
        ("id_mantenimiento",),
        ("es_correctivo_cerrado",),
        tol,
    )


def validate_oee(
    conn,
    prod: dict[str, dict[tuple, dict[str, Any]]],
    tol: float,
) -> None:
    specs = (
        (
            "planta",
            "v_kpi_oee_planta_dia",
            ("fecha", "id_planta"),
            ("fecha", "id_planta"),
        ),
        (
            "linea",
            "v_kpi_oee_linea_dia",
            ("fecha", "id_linea"),
            ("fecha", "id_linea"),
        ),
        (
            "maquina",
            "v_kpi_oee_maquina_dia",
            ("fecha", "id_maquina"),
            ("fecha", "id_maquina"),
        ),
        (
            "maquina_turno",
            "v_kpi_oee_maquina_turno",
            ("fecha", "id_maquina", "id_turno"),
            ("fecha", "id_maquina", "id_turno"),
        ),
        (
            "producto",
            "v_kpi_oee_producto_dia",
            ("fecha", "id_producto"),
            ("fecha", "id_producto"),
        ),
    )
    common_metrics = (
        "tiempo_calendario_min",
        "tiempo_planificado_min",
        "downtime_planificado_min",
        "tiempo_operativo_min",
        "downtime_no_planificado_min",
        "total_count",
        "good_count",
        "scrap_count",
        "minutos_ideales",
        "energia_kwh",
        "filas_produccion",
        "disponibilidad",
        "rendimiento",
        "calidad",
        "oee",
        "scrap_rate",
        "energia_por_unidad_buena",
        "downtime_no_planificado_pct",
    )
    total = prod["total"][()]
    for label, view, key_fields, _ in specs:
        rows = fetch(conn, f"SELECT * FROM {view}")
        compare_view(
            conn,
            f"AC-501 {view}",
            f"SELECT * FROM {view}",
            prod[label],
            key_fields,
            common_metrics
            + (("turnos_maquina",) if label != "maquina_turno" else ()),
            tol,
        )
        check_additivity(
            f"AC-503/504 {view} sumas aditivas",
            rows,
            (
                "tiempo_planificado_min",
                "tiempo_operativo_min",
                "downtime_no_planificado_min",
                "total_count",
                "good_count",
                "scrap_count",
                "minutos_ideales",
                "energia_kwh",
            ),
            total,
            tol,
        )
    # El total global no debe depender de filtrar por planta.
    check_additivity(
        "AC-503 OEE global = suma ponderada de plantas",
        fetch(conn, "SELECT * FROM v_kpi_oee_planta_dia"),
        (
            "tiempo_planificado_min",
            "tiempo_operativo_min",
            "total_count",
            "good_count",
            "minutos_ideales",
        ),
        total,
        tol,
    )


def validate_mantenimiento(
    conn,
    rel: dict[tuple, dict[str, Any]],
    rel_metrics: dict[str, dict[tuple, dict[str, Any]]],
    maps: dict[str, Any],
    tol: float,
) -> None:
    metrics = (
        "tiempo_calendario_min",
        "tiempo_planificado_min",
        "downtime_planificado_min",
        "tiempo_operativo_min",
        "downtime_no_planificado_min",
        "total_count",
        "good_count",
        "paradas_no_planificadas",
        "minutos_no_planificados_parada",
        "fallas",
        "minutos_fallas",
        "microparadas",
        "minutos_microparadas",
        "fallas_cortas",
        "minutos_fallas_cortas",
        "reparaciones",
        "minutos_reparacion",
        "intervenciones",
        "minutos_intervencion",
        "costo_mantenimiento_usd",
        "tiempo_operativo_h",
        "mtbf_h",
        "mttr_min",
        "downtime_no_planificado_pct",
        "mtbf_corto_h",
        "fallas_cortas_por_100h",
        "microparadas_por_100h",
        "duracion_media_micro_min",
        "duracion_media_falla_min",
    )
    rows = fetch(conn, "SELECT * FROM v_kpi_mantenimiento_maquina_turno")
    compare_view(
        conn,
        "AC-501 v_kpi_mantenimiento_maquina_turno (MTBF/MTTR)",
        "SELECT * FROM v_kpi_mantenimiento_maquina_turno",
        rel_metrics["turno"],
        ("fecha", "id_maquina", "id_turno"),
        metrics,
        tol,
    )
    compare_view(
        conn,
        "AC-501 v_kpi_mantenimiento_maquina_dia",
        "SELECT * FROM v_kpi_mantenimiento_maquina_dia",
        rel_metrics["dia"],
        ("fecha", "id_maquina"),
        metrics + ("turnos_maquina",),
        tol,
    )
    compare_view(
        conn,
        "AC-501 v_kpi_mantenimiento_maquina_mes",
        "SELECT * FROM v_kpi_mantenimiento_maquina_mes",
        rel_metrics["mes"],
        ("anio_mes", "id_maquina"),
        metrics + ("turnos_maquina", "dias_con_datos"),
        tol,
    )
    compare_view(
        conn,
        "AC-501 v_kpi_mantenimiento_planta_dia",
        "SELECT * FROM v_kpi_mantenimiento_planta_dia",
        rel_metrics["planta"],
        ("fecha", "id_planta"),
        metrics
        + (
            "turnos_maquina",
            "maquinas_con_fallas",
            "maquinas_con_microparadas",
        ),
        tol,
    )
    # Sumas de control: los agregados no pierden ni duplican minutos/fallas.
    expected_sums = {
        "tiempo_operativo_min": sum(a["operativo"] for a in rel.values()),
        "fallas": sum(a["fallas"] for a in rel.values()),
        "microparadas": sum(a["micro"] for a in rel.values()),
        "minutos_fallas": sum(a["minutos_fallas"] for a in rel.values()),
        "minutos_microparadas": sum(a["minutos_micro"] for a in rel.values()),
        "fallas_cortas": sum(a["fallas_cortas"] for a in rel.values()),
        "reparaciones": sum(a["reparaciones"] for a in rel.values()),
        "minutos_reparacion": sum(
            a["minutos_reparacion"] for a in rel.values()
        ),
    }
    for view in (
        "v_kpi_mantenimiento_maquina_turno",
        "v_kpi_mantenimiento_maquina_dia",
        "v_kpi_mantenimiento_maquina_mes",
        "v_kpi_mantenimiento_planta_dia",
    ):
        check_additivity(
            f"AC-504 {view} sumas aditivas",
            fetch(conn, f"SELECT * FROM {view}"),
            tuple(expected_sums),
            expected_sums,
            tol,
        )
    # Vista de apoyo (microparadas y fallas cortas).
    # Se construye desde el agregado diario, que ya tiene todas las medidas.
    support = {
        key: {
            "tiempo_operativo_min": value["tiempo_operativo_min"],
            "microparadas": value["microparadas"],
            "minutos_microparadas": value["minutos_microparadas"],
            "fallas": value["fallas"],
            "minutos_fallas": value["minutos_fallas"],
            "fallas_cortas": value["fallas_cortas"],
            "minutos_fallas_cortas": value["minutos_fallas_cortas"],
            "mtbf_corto_h": value["mtbf_corto_h"],
            "fallas_cortas_por_100h": value["fallas_cortas_por_100h"],
            "microparadas_por_100h": value["microparadas_por_100h"],
            "duracion_media_micro_min": value["duracion_media_micro_min"],
        }
        for key, value in rel_metrics["dia"].items()
    }
    compare_view(
        conn,
        "AC-501 v_kpi_confiabilidad_apoyo_maquina_dia",
        "SELECT * FROM v_kpi_confiabilidad_apoyo_maquina_dia",
        support,
        ("fecha", "id_maquina"),
        (
            "tiempo_operativo_min",
            "microparadas",
            "minutos_microparadas",
            "fallas",
            "minutos_fallas",
            "fallas_cortas",
            "minutos_fallas_cortas",
            "mtbf_corto_h",
            "fallas_cortas_por_100h",
            "microparadas_por_100h",
            "duracion_media_micro_min",
        ),
        tol,
    )


def validate_calidad(
    conn,
    data: dict[str, Any],
    prod: dict[str, dict[tuple, dict[str, Any]]],
    quality: dict[str, dict[tuple, dict[str, Any]]],
    maps: dict[str, Any],
    tol: float,
) -> None:
    combined_machine = build_calidad_combined(
        prod["maquina"], quality["maquina"]
    )
    combined_product = build_calidad_combined(
        prod["producto"], quality["producto"]
    )
    common = (
        "tiempo_planificado_min",
        "tiempo_operativo_min",
        "downtime_no_planificado_min",
        "total_count",
        "good_count",
        "scrap_count",
        "energia_kwh",
        "inspecciones",
        "unidades_inspeccionadas",
        "unidades_buenas_inspeccion",
        "unidades_defectuosas",
        "unidades_retrabajo",
        "inspecciones_con_retrabajo",
        "scrap_rate",
        "energia_por_unidad_buena",
        "downtime_no_planificado_pct",
        "tasa_defectos",
        "tasa_retrabajo",
        "fpy",
    )
    compare_view(
        conn,
        "AC-501 v_kpi_calidad_maquina_dia (Scrap/FPY/Energía)",
        "SELECT * FROM v_kpi_calidad_maquina_dia",
        combined_machine,
        ("fecha", "id_maquina"),
        common,
        tol,
    )
    compare_view(
        conn,
        "AC-501 v_kpi_calidad_producto_dia (Scrap/FPY/Energía)",
        "SELECT * FROM v_kpi_calidad_producto_dia",
        combined_product,
        ("fecha", "id_producto"),
        common,
        tol,
    )
    # Sumas de control frente a los hechos crudos.
    check_additivity(
        "AC-504 v_kpi_calidad_maquina_dia sumas aditivas",
        fetch(conn, "SELECT * FROM v_kpi_calidad_maquina_dia"),
        (
            "total_count",
            "good_count",
            "scrap_count",
            "energia_kwh",
            "unidades_inspeccionadas",
            "unidades_retrabajo",
        ),
        {
            "total_count": sum(
                int(r["total_count"]) for r in data["produccion"]
            ),
            "good_count": sum(
                int(r["good_count"]) for r in data["produccion"]
            ),
            "scrap_count": sum(
                int(r["scrap_count"]) for r in data["produccion"]
            ),
            "energia_kwh": sum(
                float(r["energia_kwh"]) for r in data["produccion"]
            ),
            "unidades_inspeccionadas": sum(
                int(r["unidades_inspeccionadas"]) for r in data["calidad"]
            ),
            "unidades_retrabajo": sum(
                int(r["unidades_retrabajo"]) for r in data["calidad"]
            ),
        },
        tol,
    )


def validate_loss(
    conn, data: dict[str, Any], maps: dict[str, Any], tol: float
) -> None:
    rows, monthly = build_loss(data, maps)
    compare_view(
        conn,
        "AC-501 v_loss_tree (descomposición por fila)",
        "SELECT * FROM v_loss_tree",
        {(key,): value for key, value in rows.items()},
        ("id_produccion",),
        (
            "tiempo_planificado_min",
            "tiempo_operativo_min",
            "total_count",
            "good_count",
            "scrap_count",
            "minutos_ideales",
            "oee",
            "minutos_perdidos_disponibilidad",
            "minutos_perdidos_rendimiento",
            "minutos_perdidos_calidad",
            "minutos_perdidos_total",
            "unidades_potenciales",
            "unidades_no_producidas",
            "unidades_scrap",
            "participacion_disponibilidad",
            "participacion_rendimiento",
            "participacion_calidad",
        ),
        tol,
    )
    compare_view(
        conn,
        "AC-501 v_loss_tree_maquina_mes (Loss Tree por activo)",
        "SELECT * FROM v_loss_tree_maquina_mes",
        monthly,
        ("anio_mes", "id_maquina"),
        (
            "tiempo_planificado_min",
            "tiempo_operativo_min",
            "minutos_ideales",
            "total_count",
            "good_count",
            "scrap_count",
            "minutos_perdidos_disponibilidad",
            "minutos_perdidos_rendimiento",
            "minutos_perdidos_calidad",
            "minutos_perdidos_total",
            "unidades_potenciales",
            "unidades_no_producidas",
            "unidades_scrap",
            "filas_produccion",
            "dias_con_datos",
            "disponibilidad",
            "rendimiento",
            "calidad",
            "oee",
            "participacion_disponibilidad",
            "participacion_rendimiento",
            "participacion_calidad",
        ),
        tol,
    )
    expected = {
        "minutos_perdidos_disponibilidad": sum(
            v["minutos_perdidos_disponibilidad"] for v in rows.values()
        ),
        "minutos_perdidos_rendimiento": sum(
            v["minutos_perdidos_rendimiento"] for v in rows.values()
        ),
        "minutos_perdidos_calidad": sum(
            v["minutos_perdidos_calidad"] for v in rows.values()
        ),
        "minutos_perdidos_total": sum(
            v["minutos_perdidos_total"] for v in rows.values()
        ),
    }
    check_additivity(
        "AC-504 v_loss_tree sumas aditivas",
        fetch(conn, "SELECT * FROM v_loss_tree"),
        tuple(expected),
        expected,
        tol,
    )


def validate_alerts(
    conn,
    rel: dict[tuple, dict[str, Any]],
    rel_metrics: dict[str, dict[tuple, dict[str, Any]]],
    prod: dict[str, dict[tuple, dict[str, Any]]],
    data: dict[str, Any],
    maps: dict[str, Any],
    tol: float,
) -> None:
    alerts = build_alerts(
        data, maps, rel, rel_metrics["turno"], prod["maquina_turno"]
    )
    compare_view(
        conn,
        "AC-501 v_alerta_maquina_critica (regla §8)",
        "SELECT * FROM v_alerta_maquina_critica",
        alerts,
        ("fecha", "id_maquina", "id_turno"),
        (
            "oee",
            "disponibilidad",
            "rendimiento",
            "calidad",
            "mtbf_h",
            "mttr_min",
            "downtime_no_planificado_min",
            "lecturas_temp_alta",
            "max_temperatura_c",
            "minutos_temp_alta_estimados",
            "cumple_oee",
            "cumple_mtbf",
            "cumple_temperatura",
            "cumple_downtime",
            "condiciones_cumplidas",
            "severidad",
            "es_ultimo_turno_maquina",
        ),
        tol,
    )
    rows = fetch(
        conn,
        "SELECT severidad, count(*) AS n FROM v_alerta_maquina_critica "
        "GROUP BY severidad",
    )
    detail = ", ".join(f"{r['severidad']}={r['n']}" for r in rows)
    total = sum(r["n"] for r in rows)
    add_check(
        "Distribución de alertas calculada",
        total == len(alerts),
        f"{detail}; total={total} esperado={len(alerts)}",
    )


def validate_row_counts(conn, data: dict[str, Any]) -> None:
    expectations = (
        ("v_kpi_produccion", len(data["produccion"])),
        ("v_kpi_calidad", len(data["calidad"])),
        ("v_kpi_parada", len(data["paradas"])),
        ("v_kpi_mantenimiento", len(data["mantenimiento"])),
        ("v_loss_tree", len(data["produccion"])),
    )
    for view, expected in expectations:
        actual = fetch_one(conn, f"SELECT count(*) FROM {view}")
        add_check(
            f"AC-504 {view} sin multiplicación de filas",
            actual == expected,
            f"vista={actual} hechos={expected}",
        )


def validate_nulls(conn) -> None:
    checks = (
        (
            "AC-502 v_kpi_produccion: NULL solo con denominador cero",
            """
            SELECT count(*) FROM v_kpi_produccion
            WHERE (tiempo_planificado_min > 0 AND disponibilidad IS NULL)
               OR (tiempo_operativo_min > 0 AND rendimiento IS NULL)
               OR (total_count > 0 AND calidad IS NULL)
               OR (total_count > 0 AND scrap_rate IS NULL)
               OR (good_count > 0 AND energia_por_unidad_buena IS NULL)
               OR (tiempo_planificado_min > 0
                   AND downtime_no_planificado_pct IS NULL)
               OR (tiempo_planificado_min > 0 AND tiempo_operativo_min > 0
                   AND total_count > 0 AND oee IS NULL)
            """,
        ),
        (
            "AC-502 v_kpi_mantenimiento_maquina_turno: MTBF/MTTR definidos",
            """
            SELECT count(*) FROM v_kpi_mantenimiento_maquina_turno
            WHERE (tiempo_operativo_min > 0 AND fallas > 0 AND mtbf_h IS NULL)
               OR (reparaciones > 0 AND mttr_min IS NULL)
               OR (tiempo_operativo_min > 0 AND fallas_cortas > 0
                   AND mtbf_corto_h IS NULL)
            """,
        ),
        (
            "AC-502 v_kpi_calidad_maquina_dia: FPY definido",
            """
            SELECT count(*) FROM v_kpi_calidad_maquina_dia
            WHERE unidades_inspeccionadas > 0 AND fpy IS NULL
            """,
        ),
        (
            "AC-502 v_kpi_confiabilidad_apoyo_maquina_dia: tasas definidas",
            """
            SELECT count(*) FROM v_kpi_confiabilidad_apoyo_maquina_dia
            WHERE (tiempo_operativo_min > 0 AND fallas_cortas_por_100h IS NULL)
               OR (tiempo_operativo_min > 0 AND microparadas_por_100h IS NULL)
               OR (microparadas > 0 AND duracion_media_micro_min IS NULL)
            """,
        ),
        (
            "AC-502 v_alerta_maquina_critica: severidad y conteo válidos",
            """
            SELECT count(*) FROM v_alerta_maquina_critica
            WHERE severidad IS NULL
               OR condiciones_cumplidas NOT BETWEEN 0 AND 4
               OR (severidad = 'sin_alerta' AND condiciones_cumplidas <> 0)
               OR (severidad = 'alerta' AND condiciones_cumplidas <> 1)
               OR (severidad = 'critica' AND condiciones_cumplidas < 2)
            """,
        ),
        (
            "AC-502 v_loss_tree: participaciones suman 1",
            """
            SELECT count(*) FROM v_loss_tree
            WHERE minutos_perdidos_total > 0
              AND abs(participacion_disponibilidad
                    + participacion_rendimiento
                    + participacion_calidad - 1) > 1e-9
            """,
        ),
        (
            "AC-502 v_kpi_oee_*: OEE dentro de [0, 1]",
            """
            SELECT count(*) FROM v_kpi_oee_maquina_turno
            WHERE oee < 0 OR oee > 1.0000001
            """,
        ),
    )
    for label, sql in checks:
        value = fetch_one(conn, sql)
        add_check(label, value == 0, f"incidencias={value}")


def validate_edge_cases(conn) -> None:
    """Prueba denominadores cero y parada sin producción en una transacción."""
    try:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("SELECT id_causa FROM dim_causa WHERE codigo = 'F-MEC'")
            id_causa = cur.fetchone()[0]
            cur.execute(
                """
                INSERT INTO dim_orden (
                    id_orden, codigo_orden, id_producto, cantidad_planificada,
                    fecha_plan, estado
                ) VALUES (
                    999999999, 'EDGE-TEST-005', 1, 0, DATE '2026-10-18', 'cerrada'
                )
                """
            )
            cur.execute(
                """
                INSERT INTO fact_produccion (
                    id_orden, id_maquina, id_producto, id_turno, id_tiempo,
                    inicio_at, fin_at, tiempo_calendario_min,
                    tiempo_planificado_min, downtime_planificado_min,
                    tiempo_operativo_min, downtime_no_planificado_min,
                    total_count, good_count, scrap_count,
                    ciclo_ideal_segundos, energia_kwh
                ) VALUES (
                    999999999, 1, 1, 1, 20261018,
                    TIMESTAMPTZ '2026-10-18 06:00:00+00',
                    TIMESTAMPTZ '2026-10-18 14:00:00+00',
                    0, 0, 0, 0, 0, 0, 0, 0, 30, 0
                )
                """
            )
            cur.execute(
                """
                SELECT disponibilidad, rendimiento, calidad, oee, scrap_rate,
                       energia_por_unidad_buena, downtime_no_planificado_pct
                FROM v_kpi_produccion
                WHERE id_orden = 999999999
                """
            )
            row = cur.fetchone()
            expected_null = all(value is None for value in row)
            add_check(
                "AC-502 caso borde: división por cero devuelve NULL",
                expected_null,
                f"valores={row}",
            )

            cur.execute(
                """
                INSERT INTO fact_parada (
                    id_maquina, id_turno, id_tiempo, id_causa,
                    id_mantenimiento, inicio_at, fin_at, duracion_min,
                    es_planificada, es_microparada, causa_detalle
                ) VALUES (
                    1, 1, 20261019, %s, NULL,
                    TIMESTAMPTZ '2026-10-19 07:00:00+00',
                    TIMESTAMPTZ '2026-10-19 07:20:00+00',
                    20, false, false, 'Caso borde 005: parada sin producción'
                )
                """,
                (id_causa,),
            )
            cur.execute(
                """
                SELECT tiempo_operativo_min, fallas, mtbf_h,
                       downtime_no_planificado_min,
                       downtime_no_planificado_pct
                FROM v_kpi_mantenimiento_maquina_turno
                WHERE id_maquina = 1 AND id_turno = 1 AND id_tiempo = 20261019
                """
            )
            row = cur.fetchone()
            ok = (
                row is not None
                and row[0] == 0
                and row[1] == 1
                and row[2] is None
                and row[3] == 20
                and row[4] is None
            )
            add_check(
                "AC-502 caso borde: parada sin producción (MTBF NULL)",
                ok,
                f"fila={row}",
            )

            cur.execute(
                """
                SELECT severidad, condiciones_cumplidas, oee, mtbf_h,
                       downtime_no_planificado_min
                FROM v_alerta_maquina_critica
                WHERE id_maquina = 1 AND id_turno = 1 AND id_tiempo = 20261019
                """
            )
            row = cur.fetchone()
            ok = (
                row is not None
                and row[0] == "sin_alerta"
                and row[1] == 0
                and row[2] is None
                and row[3] is None
                and row[4] == 20
            )
            add_check(
                "AC-502 caso borde: alerta sin producción no inventa OEE/MTBF",
                ok,
                f"fila={row}",
            )
    except Exception as exc:  # pragma: no cover - defensa
        add_check("AC-502 casos borde", False, f"error: {exc}")
    finally:
        conn.rollback()


def print_summary(
    prod: dict[str, Any],
    rel_metrics: dict[str, dict[tuple, dict[str, Any]]],
) -> None:
    """Resumen global recalculado desde los hechos (evidencia AC-501)."""
    total = prod["total"][()]
    turnos = list(rel_metrics["turno"].values())
    runtime = sum(item["tiempo_operativo_min"] for item in turnos)
    fallas = sum(item["fallas"] for item in turnos)
    reparaciones = sum(item["reparaciones"] for item in turnos)
    minutos_reparacion = sum(item["minutos_reparacion"] for item in turnos)
    mtbf = runtime / 60.0 / fallas if runtime > 0 and fallas > 0 else None
    mttr = (
        minutos_reparacion / reparaciones if reparaciones > 0 else None
    )
    print("Resumen global recalculado por Python")
    print("=" * 72)
    print(f"Disponibilidad: {total['disponibilidad']:.4f}")
    print(f"Rendimiento:    {total['rendimiento']:.4f}")
    print(f"Calidad:        {total['calidad']:.4f}")
    print(f"OEE:            {total['oee']:.4f}")
    print(
        "Unidades:       "
        f"{total['total_count']:,} totales, "
        f"{total['good_count']:,} buenas, "
        f"{total['scrap_count']:,} scrap"
    )
    print(f"MTBF:           {mtbf:.2f} h ({fallas:,} fallas)")
    print(f"MTTR:           {mttr:.2f} min ({reparaciones:,} reparaciones)")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida las vistas KPI del incremento 005 contra los hechos."
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"tolerancia relativa/absoluta (default: {DEFAULT_TOLERANCE})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print("Validación de vistas KPI (incremento 005)")
    print("=" * 72)
    print(f"Tolerancia: {args.tolerance:.1e} (objetivo del spec: 0,1 %)")
    print()

    with connect() as conn:
        data = load_data(conn)
        maps = build_maps(data)
        prod_stores = build_production(data, maps)
        prod = build_production_metrics(prod_stores)
        quality = build_quality(data, maps)
        rel = build_rel(data)
        rel_metrics = build_rel_metrics(rel, maps)

        validate_contract(conn)
        validate_raw_views(conn, data, maps, args.tolerance)
        validate_oee(conn, prod, args.tolerance)
        validate_mantenimiento(
            conn, rel, rel_metrics, maps, args.tolerance
        )
        validate_calidad(
            conn, data, prod, quality, maps, args.tolerance
        )
        validate_loss(conn, data, maps, args.tolerance)
        validate_alerts(
            conn,
            rel,
            rel_metrics,
            prod,
            data,
            maps,
            args.tolerance,
        )
        validate_row_counts(conn, data)
        validate_nulls(conn)
        validate_edge_cases(conn)
        print_summary(prod, rel_metrics)

    failed = [check for check in CHECKS if not check.ok]
    print("Comprobaciones")
    print("=" * 72)
    for check in CHECKS:
        print(f"[{'OK' if check.ok else 'FALLA'}] {check.name}")
        if check.detail:
            print(f"       {check.detail}")
    print()
    print(
        f"Resultado: {len(CHECKS) - len(failed)}/{len(CHECKS)} "
        "comprobaciones OK"
    )
    if failed:
        print()
        print("Fallos:")
        for check in failed:
            print(f"- {check.name}: {check.detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
