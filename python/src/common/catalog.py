"""Carga del catálogo de referencia desde PostgreSQL.

El catálogo estático (plantas, líneas, máquinas, familias, productos, turnos,
causas, técnicos y calendario) lo siembra `sql/schema/04_catalogo_referencia.sql`.
El generador **lee** ese catálogo en lugar de duplicarlo, para que no existan dos
fuentes de verdad.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

import psycopg


@dataclass(frozen=True)
class Planta:
    id_planta: int
    codigo: str


@dataclass(frozen=True)
class Linea:
    id_linea: int
    id_planta: int


@dataclass(frozen=True)
class Maquina:
    id_maquina: int
    id_linea: int
    id_planta: int
    codigo: str
    tipo: str
    criticidad: str
    perfil_rendimiento: str


@dataclass(frozen=True)
class Turno:
    id_turno: int
    codigo: str
    hora_inicio: time
    hora_fin: time
    duracion_min: int
    cruza_medianoche: bool


@dataclass(frozen=True)
class Familia:
    id_familia: int
    codigo: str


@dataclass(frozen=True)
class Producto:
    id_producto: int
    id_familia: int
    codigo: str


@dataclass(frozen=True)
class Causa:
    id_causa: int
    codigo: str
    es_planificada: bool


@dataclass(frozen=True)
class Tecnico:
    id_tecnico: int
    codigo: str
    especialidad: str


@dataclass(frozen=True)
class Catalog:
    plantas: tuple[Planta, ...]
    lineas: tuple[Linea, ...]
    maquinas: tuple[Maquina, ...]
    turnos: tuple[Turno, ...]
    familias: tuple[Familia, ...]
    productos: tuple[Producto, ...]
    causas: tuple[Causa, ...]
    tecnicos: tuple[Tecnico, ...]
    dias: dict[date, int]

    def causa(self, codigo: str) -> Causa:
        for causa in self.causas:
            if causa.codigo == codigo:
                return causa
        raise KeyError(
            f"Causa '{codigo}' ausente en dim_causa. "
            "Ejecuta sql/apply_all.sql para actualizar el catálogo."
        )

    def productos_de_familia(self, id_familia: int) -> tuple[Producto, ...]:
        productos = tuple(p for p in self.productos if p.id_familia == id_familia)
        if not productos:
            raise RuntimeError(f"La familia {id_familia} no tiene productos en dim_producto.")
        return productos


def load_catalog(
    conn: psycopg.Connection,
    start_date: date,
    end_date: date,
    max_plantas: int = 3,
    max_maquinas: int = 52,
) -> Catalog:
    """Lee el catálogo y lo filtra por número de plantas y de máquinas."""
    with conn.cursor() as cur:
        cur.execute("SELECT id_planta, codigo FROM dim_planta ORDER BY id_planta")
        plantas = [Planta(*row) for row in cur.fetchall()][:max_plantas]

        if not plantas:
            raise RuntimeError("dim_planta está vacía. Ejecuta sql/apply_all.sql.")

        ids_planta = {p.id_planta for p in plantas}

        cur.execute(
            "SELECT id_linea, id_planta FROM dim_linea ORDER BY id_linea"
        )
        lineas = tuple(
            Linea(*row) for row in cur.fetchall() if row[1] in ids_planta
        )

        ids_linea = {linea.id_linea for linea in lineas}
        if not ids_linea:
            raise RuntimeError("No hay líneas para las plantas seleccionadas.")

        cur.execute(
            "SELECT m.id_maquina, m.id_linea, l.id_planta, m.codigo, m.tipo, "
            "       m.criticidad, m.perfil_rendimiento "
            "FROM dim_maquina m "
            "JOIN dim_linea l ON l.id_linea = m.id_linea "
            "ORDER BY m.id_maquina"
        )
        maquinas = tuple(
            Maquina(*row)
            for row in cur.fetchall()
            if row[1] in ids_linea
        )[:max_maquinas]

        if not maquinas:
            raise RuntimeError("No hay máquinas para las plantas seleccionadas.")

        cur.execute(
            "SELECT id_turno, codigo, hora_inicio, hora_fin, duracion_min, cruza_medianoche "
            "FROM dim_turno ORDER BY id_turno"
        )
        turnos = tuple(Turno(*row) for row in cur.fetchall())

        cur.execute("SELECT id_familia, codigo FROM dim_familia ORDER BY id_familia")
        familias = tuple(Familia(*row) for row in cur.fetchall())

        cur.execute(
            "SELECT id_producto, id_familia, codigo FROM dim_producto ORDER BY id_producto"
        )
        productos = tuple(Producto(*row) for row in cur.fetchall())

        cur.execute(
            "SELECT id_causa, codigo, es_planificada FROM dim_causa ORDER BY id_causa"
        )
        causas = tuple(Causa(*row) for row in cur.fetchall())

        cur.execute(
            "SELECT id_tecnico, codigo, especialidad FROM dim_tecnico "
            "WHERE activo ORDER BY id_tecnico"
        )
        tecnicos = tuple(Tecnico(*row) for row in cur.fetchall())

        cur.execute(
            "SELECT id_tiempo, fecha FROM dim_tiempo "
            "WHERE fecha BETWEEN %s AND %s ORDER BY fecha",
            (start_date, end_date),
        )
        dias = {row[1]: row[0] for row in cur.fetchall()}

    if not turnos:
        raise RuntimeError("dim_turno está vacía.")
    if not familias or not productos:
        raise RuntimeError("Familias o productos vacíos en el catálogo.")
    if not causas:
        raise RuntimeError("dim_causa está vacía.")
    if not tecnicos:
        raise RuntimeError("dim_tecnico está vacía o sin técnicos activos.")

    return Catalog(
        plantas=tuple(plantas),
        lineas=lineas,
        maquinas=maquinas,
        turnos=turnos,
        familias=familias,
        productos=productos,
        causas=causas,
        tecnicos=tecnicos,
        dias=dias,
    )
