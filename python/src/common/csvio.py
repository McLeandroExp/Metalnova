"""Escritura incremental de CSV para el histórico sintético.

Cada tabla se escribe en streaming (no se mantiene en memoria) y se publica de
forma atómica: primero se vuelca a un archivo temporal y, al cerrar, se renombra
sobre el destino. Si el proceso falla, el CSV anterior no queda corrupto.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence


class CsvTable:
    """Archivo CSV con cabecera fija y contador de filas escritas."""

    def __init__(self, path: Path, header: Sequence[str]) -> None:
        self.path = path
        self.header = tuple(header)
        self.rows = 0
        self.bytes = 0

        path.parent.mkdir(parents=True, exist_ok=True)
        self._tmp_path = path.with_name(path.name + ".tmp")
        self._fh = self._tmp_path.open("w", encoding="utf-8", newline="")
        self._writer = csv.writer(self._fh, lineterminator="\n")
        self._writer.writerow(self.header)

    def write(self, row: Sequence[object]) -> None:
        if len(row) != len(self.header):
            raise ValueError(
                f"{self.path.name}: se esperaban {len(self.header)} columnas y llegaron {len(row)}"
            )
        self._writer.writerow(row)
        self.rows += 1

    def close(self) -> None:
        """Cierra el archivo temporal y lo publica con el nombre definitivo."""
        if self._fh.closed:
            return
        self._fh.flush()
        self._fh.close()
        self._tmp_path.replace(self.path)
        self.bytes = self.path.stat().st_size

    def abort(self) -> None:
        """Cierra y elimina el archivo temporal sin publicar nada."""
        if not self._fh.closed:
            self._fh.close()
        self._tmp_path.unlink(missing_ok=True)

    def __enter__(self) -> "CsvTable":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001 - protocolo de contexto
        if exc_type is None:
            self.close()
        else:
            self.abort()
