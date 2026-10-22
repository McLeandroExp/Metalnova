"""Inserción idempotente y métricas de ingesta (incremento 004).

Este módulo concentra la escritura en PostgreSQL del simulador de eventos:

- Inserciones por lote dentro de una transacción.
- Idempotencia por clave estable: ``ON CONFLICT (source_system, source_event_id)``
  para eventos y ``ON CONFLICT (id_maquina, inicio_at)`` para paradas.
- Reintentos limitados con *backoff* ante errores de conexión.
- Medición de latencia ``ingested_at − generated_at``.

Nunca se imprimen credenciales ni la cadena de conexión: los mensajes de error se
reducen al tipo de excepción y al número de intento.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Sequence

import psycopg
from psycopg.types.json import Jsonb

from common.db import connect
from event_quality import classify_event, quality_payload

UTC = timezone.utc

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 1.0

INSERT_EVENT_SQL = """
    INSERT INTO fact_evento (
        source_system, source_event_id, tipo_evento, id_maquina,
        event_time, generated_at, ingested_at, run_id, estado,
        temperatura_c, energia_kwh, payload
    )
    VALUES (
        %(source_system)s, %(source_event_id)s, %(tipo_evento)s, %(id_maquina)s,
        %(event_time)s, %(generated_at)s, %(ingested_at)s, %(run_id)s, %(estado)s,
        %(temperatura_c)s, %(energia_kwh)s, %(payload)s
    )
    ON CONFLICT (source_system, source_event_id) DO NOTHING
"""

INSERT_REJECT_SQL = """
    INSERT INTO fact_evento_rechazado (
        source_system, source_event_id, motivo, payload, recibido_at
    )
    VALUES (
        %(source_system)s, %(source_event_id)s, %(motivo)s,
        %(payload)s, %(recibido_at)s
    )
"""

INSERT_STOP_SQL = """
    INSERT INTO fact_parada (
        id_maquina, id_turno, id_tiempo, id_causa, id_mantenimiento,
        inicio_at, fin_at, duracion_min, es_planificada, es_microparada,
        causa_detalle
    )
    VALUES (
        %(id_maquina)s, %(id_turno)s, %(id_tiempo)s, %(id_causa)s, NULL,
        %(inicio_at)s, %(fin_at)s, %(duracion_min)s, %(es_planificada)s,
        %(es_microparada)s, %(causa_detalle)s
    )
    ON CONFLICT (id_maquina, inicio_at) DO NOTHING
"""


class IngestError(RuntimeError):
    """Error de base de datos tras agotar los reintentos."""


@dataclass(frozen=True)
class EventRecord:
    """Evento de origen listo para persistir."""

    source_system: str
    source_event_id: str
    tipo_evento: str
    id_maquina: int | None
    event_time: datetime
    generated_at: datetime
    estado: str | None = None
    temperatura_c: float | None = None
    energia_kwh: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StopRecord:
    """Episodio de parada listo para persistir."""

    id_maquina: int
    id_turno: int
    id_tiempo: int
    id_causa: int
    inicio_at: datetime
    fin_at: datetime
    duracion_min: int
    es_planificada: bool
    es_microparada: bool
    causa_detalle: str


@dataclass(frozen=True)
class IngestResult:
    """Resultado de un lote insertado."""

    events_generated: int
    events_inserted: int
    events_duplicated: int
    stops_generated: int
    stops_inserted: int
    stops_duplicated: int
    ingested_at: datetime
    latency_seconds: tuple[float, ...]
    events_rejected: int = 0
    rejection_reasons: tuple[str, ...] = ()

    @property
    def latency_avg_seconds(self) -> float:
        if not self.latency_seconds:
            return 0.0
        return sum(self.latency_seconds) / len(self.latency_seconds)

    @property
    def latency_max_seconds(self) -> float:
        return max(self.latency_seconds, default=0.0)

    def as_dict(self) -> dict[str, Any]:
        return {
            "events_generated": self.events_generated,
            "events_inserted": self.events_inserted,
            "events_duplicated": self.events_duplicated,
            "stops_generated": self.stops_generated,
            "stops_inserted": self.stops_inserted,
            "stops_duplicated": self.stops_duplicated,
            "ingested_at": self.ingested_at.isoformat(),
            "latency_avg_seconds": round(self.latency_avg_seconds, 6),
            "latency_max_seconds": round(self.latency_max_seconds, 6),
            "events_rejected": self.events_rejected,
            "rejection_reasons": list(self.rejection_reasons),
        }


def _error_summary(exc: BaseException) -> str:
    """Describe un error sin exponer credenciales ni la cadena de conexión."""
    return type(exc).__name__


class Ingestor:
    """Escribe eventos y paradas en PostgreSQL con reintentos limitados."""

    def __init__(
        self,
        run_id: str,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        base_delay: float = DEFAULT_BASE_DELAY,
        logger: logging.Logger | None = None,
    ) -> None:
        self.run_id = run_id
        self.max_attempts = max(1, max_attempts)
        self.base_delay = max(0.0, base_delay)
        self.log = logger or logging.getLogger("metalinova.ingest")
        self.conn: psycopg.Connection | None = None
        self._historical_start: datetime | None = None
        self._historical_start_loaded = False
        self._last_event_time: dict[int, datetime] = {}

    # -------------------------------------------------------------- conexión
    def _close_connection(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:  # noqa: BLE001 - cierre defensivo
                pass
            self.conn = None

    def _connect_once(self) -> psycopg.Connection:
        if self.conn is None or self.conn.closed:
            self.conn = connect()
            # Las lecturas no deben dejar una transacción abierta entre ciclos;
            # `ingest()` abre su propia transacción explícita.
            self.conn.autocommit = True
        return self.conn

    def connection(self) -> psycopg.Connection:
        """Devuelve una conexión viva, reintentando con *backoff*."""
        return self._with_retry("conexión", self._connect_once)

    def close(self) -> None:
        self._close_connection()

    def __enter__(self) -> "Ingestor":
        self.connection()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001 - protocolo
        self.close()

    # --------------------------------------------------------------- reintento
    def _with_retry(self, operation: str, fn):
        delay = self.base_delay
        last_error: BaseException | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn()
            except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
                last_error = exc
                self._close_connection()
                if attempt >= self.max_attempts:
                    break
                self.log.warning(
                    "error de base en %s (%s) intento %d/%d; reintento en %.1f s",
                    operation,
                    _error_summary(exc),
                    attempt,
                    self.max_attempts,
                    delay,
                )
                if delay > 0:
                    time.sleep(delay)
                delay *= 2
        raise IngestError(
            f"no se pudo completar {operation} tras {self.max_attempts} intentos "
            f"({_error_summary(last_error) if last_error else 'error desconocido'})"
        ) from last_error

    # ----------------------------------------------------------------- lecturas
    def query(self, sql: str, params: Sequence[Any] = ()) -> list[tuple]:
        """Ejecuta una consulta de solo lectura con la misma política de reintentos."""

        def run() -> list[tuple]:
            conn = self._connect_once()
            with conn.cursor() as cur:
                if params:
                    cur.execute(sql, params)
                else:
                    cur.execute(sql)
                return cur.fetchall()

        return self._with_retry("consulta", run)

    # -------------------------------------------------------- calidad de eventos
    def historical_start(self) -> datetime | None:
        """Primer ``event_time`` del histórico, para el rango válido (§7.1)."""
        if not self._historical_start_loaded:
            rows = self.query(
                "SELECT min(event_time) FROM fact_evento "
                "WHERE run_id LIKE 'hist-%'"
            )
            self._historical_start = rows[0][0] if rows else None
            self._historical_start_loaded = True
        return self._historical_start

    def _last_event_times(self, ids: set[int]) -> dict[int, datetime | None]:
        """Último ``event_time`` conocido por máquina (caché en memoria)."""
        missing = [id_maquina for id_maquina in ids if id_maquina not in self._last_event_time]
        if missing:
            rows = self.query(
                "SELECT id_maquina, max(event_time) FROM fact_evento "
                "WHERE id_maquina = ANY(%s) GROUP BY id_maquina",
                (missing,),
            )
            for id_maquina, last in rows:
                if last is not None:
                    self._last_event_time[int(id_maquina)] = last
        return {id_maquina: self._last_event_time.get(id_maquina) for id_maquina in ids}

    # ---------------------------------------------------------------- escritura
    def ingest(
        self,
        events: Sequence[EventRecord],
        stops: Sequence[StopRecord] = (),
    ) -> IngestResult:
        """Inserta un lote de eventos y paradas en una sola transacción.

        Es seguro reintentar el lote completo: las claves únicas y ``ON CONFLICT
        DO NOTHING`` impiden duplicar filas ya confirmadas.
        """
        ingested_at = datetime.now(UTC)
        historical_start = self.historical_start()
        machine_ids = {
            event.id_maquina for event in events if event.id_maquina is not None
        }
        last_times = self._last_event_times(machine_ids)

        accepted: list[tuple[EventRecord, dict[str, Any]]] = []
        rejected: list[dict[str, Any]] = []
        for event in events:
            quality = classify_event(
                event.event_time,
                ingested_at,
                historical_start=historical_start,
                last_event_time=last_times.get(event.id_maquina),
            )
            if quality.accepted:
                payload = dict(event.payload or {})
                payload["calidad"] = quality_payload(quality)
                accepted.append((event, payload))
            else:
                rejected.append(
                    {
                        "source_system": event.source_system,
                        "source_event_id": event.source_event_id,
                        "motivo": quality.motivo or "rechazado",
                        "payload": Jsonb(
                            {
                                "event_time": (
                                    event.event_time.isoformat()
                                    if event.event_time is not None
                                    else None
                                ),
                                "tipo_evento": event.tipo_evento,
                                "id_maquina": event.id_maquina,
                                "payload_original": event.payload,
                            }
                        ),
                        "recibido_at": ingested_at,
                    }
                )

        event_params = [
            {
                "source_system": event.source_system,
                "source_event_id": event.source_event_id,
                "tipo_evento": event.tipo_evento,
                "id_maquina": event.id_maquina,
                "event_time": event.event_time,
                "generated_at": event.generated_at,
                "ingested_at": ingested_at,
                "run_id": self.run_id,
                "estado": event.estado,
                "temperatura_c": event.temperatura_c,
                "energia_kwh": event.energia_kwh,
                "payload": Jsonb(payload),
            }
            for event, payload in accepted
        ]
        stop_params = [
            {
                "id_maquina": stop.id_maquina,
                "id_turno": stop.id_turno,
                "id_tiempo": stop.id_tiempo,
                "id_causa": stop.id_causa,
                "inicio_at": stop.inicio_at,
                "fin_at": stop.fin_at,
                "duracion_min": stop.duracion_min,
                "es_planificada": stop.es_planificada,
                "es_microparada": stop.es_microparada,
                "causa_detalle": stop.causa_detalle,
            }
            for stop in stops
        ]

        def run() -> tuple[int, int, int]:
            conn = self._connect_once()
            with conn.transaction():
                with conn.cursor() as cur:
                    stops_inserted = 0
                    if stop_params:
                        cur.executemany(INSERT_STOP_SQL, stop_params)
                        stops_inserted = max(cur.rowcount, 0)
                    rejected_inserted = 0
                    if rejected:
                        cur.executemany(INSERT_REJECT_SQL, rejected)
                        rejected_inserted = max(cur.rowcount, 0)
                    events_inserted = 0
                    if event_params:
                        cur.executemany(INSERT_EVENT_SQL, event_params)
                        events_inserted = max(cur.rowcount, 0)
            return events_inserted, stops_inserted, rejected_inserted

        events_inserted, stops_inserted, rejected_inserted = self._with_retry(
            "inserción por lote", run
        )

        # Actualizar la caché de último evento por máquina solo tras confirmar.
        for event, _ in accepted:
            if event.id_maquina is None or event.event_time is None:
                continue
            current = self._last_event_time.get(event.id_maquina)
            if current is None or event.event_time > current:
                self._last_event_time[event.id_maquina] = event.event_time

        latencies = tuple(
            max((ingested_at - event.generated_at).total_seconds(), 0.0)
            for event, _ in accepted
        )
        return IngestResult(
            events_generated=len(events),
            events_inserted=events_inserted,
            events_duplicated=len(event_params) - events_inserted,
            stops_generated=len(stops),
            stops_inserted=stops_inserted,
            stops_duplicated=len(stops) - stops_inserted,
            ingested_at=ingested_at,
            latency_seconds=latencies,
            events_rejected=rejected_inserted,
            rejection_reasons=tuple(
                sorted({item["motivo"] for item in rejected})
            ),
        )

    # ------------------------------------------------------------------ métricas
    def latency_stats(self) -> dict[str, Any]:
        """Latencia media y máxima registrada para este ``run_id``."""
        rows = self.query(
            "SELECT count(*), "
            "       avg(extract(epoch FROM ingested_at - generated_at)), "
            "       max(extract(epoch FROM ingested_at - generated_at)) "
            "FROM fact_evento WHERE run_id = %s",
            (self.run_id,),
        )
        if not rows:
            return {"events": 0, "latency_avg_seconds": 0.0, "latency_max_seconds": 0.0}
        total, avg_s, max_s = rows[0]
        return {
            "events": int(total),
            "latency_avg_seconds": round(float(avg_s or 0.0), 6),
            "latency_max_seconds": round(float(max_s or 0.0), 6),
        }
