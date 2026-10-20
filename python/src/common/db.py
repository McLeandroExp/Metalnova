"""Utilidades de conexión a PostgreSQL.

Nunca se imprimen credenciales ni la cadena de conexión.
"""

from __future__ import annotations

import os

import psycopg


def build_conninfo() -> str:
    """Construye la cadena de conexión a partir de variables de entorno."""
    required = ("POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")

    return psycopg.conninfo.make_conninfo(
        host=os.environ["POSTGRES_HOST"],
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def connect() -> psycopg.Connection:
    """Abre una conexión con tiempo de espera acotado."""
    return psycopg.connect(build_conninfo(), connect_timeout=10)
