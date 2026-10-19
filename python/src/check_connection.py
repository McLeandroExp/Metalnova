"""Prueba de conectividad a PostgreSQL.

Ejecuta SELECT 1 y muestra la versión del servidor.
Nunca imprime credenciales ni la cadena de conexión.
"""

from __future__ import annotations

import logging
import os
import sys

import psycopg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("check_connection")


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


def main() -> int:
    try:
        with psycopg.connect(build_conninfo(), connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                log.info("SELECT 1 -> %s", row[0] if row else None)

                cur.execute("SELECT current_database(), version()")
                dbname, version = cur.fetchone()
                log.info("Base: %s", dbname)
                log.info("Servidor: %s", version.split(",")[0])
        log.info("Conexión OK")
        return 0
    except Exception as exc:  # noqa: BLE001 - se reporta y se sale con código de error
        log.error("Fallo de conexión: %s: %s", type(exc).__name__, exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
