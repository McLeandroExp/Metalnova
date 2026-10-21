"""Simulador de ingesta continua de eventos sintéticos (incremento 004).

Genera eventos **por transición** (arranque/parada) para las 52 máquinas y los
inserta de forma idempotente en PostgreSQL. No muestrea una fila por máquina y
minuto: cada ciclo decide qué máquinas cambian de estado y emite únicamente esos
eventos, más el arranque de las paradas que terminan en el ciclo.

Diseño de idempotencia
----------------------
Cada ciclo se alinea a una rejilla temporal (``slot = floor(t / intervalo)``) y
las decisiones se derivan de una semilla y de ``(máquina, slot)`` mediante
SHA-256. Por eso, repetir un ciclo con el mismo reloj reproduce exactamente los
mismos ``source_event_id`` y ``ON CONFLICT DO NOTHING`` descarta los duplicados.
``--at`` permite fijar el reloj para una prueba reproducible.

Uso típico:

    docker compose run --rm ingestor python src/simulate_events.py
    docker compose run --rm ingestor python src/simulate_events.py --once --at 2026-10-21T00:30:00Z
    docker compose run --rm ingestor python src/simulate_events.py --scenario stop M-001 --once

Todos los datos son sintéticos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import signal
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

from common.catalog import Catalog, Causa, Turno, load_catalog
from ingest import (
    DEFAULT_BASE_DELAY,
    DEFAULT_MAX_ATTEMPTS,
    EventRecord,
    IngestError,
    Ingestor,
    StopRecord,
)

UTC = timezone.utc
VERSION = "1.0.0"

DEFAULT_SEED = 42
DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_INTENSITY = 1.0
DEFAULT_STOP_DURATION_MIN = 20
DEFAULT_LOG_FILE = Path("logs/simulate_events.log")

LOGGER_NAME = "metalinova.sim"
CAUSA_MICRO = "MICRO"
CAUSA_ESCENARIO = "F-MEC"

# Probabilidad de que una máquina inicie una parada en un ciclo, por máquina.
# Con 60 s y 52 máquinas produce ~0,6 paradas/min, coherente con el histórico
# (~2,7 paradas por máquina y turno). `--intensity` la multiplica.
STOP_PROBABILITY = 0.012
MICRO_SHARE = 0.45
MICRO_DURATION_MIN = (1, 4)
FAILURE_DURATION_MIN = (5, 45)

FAILURE_CAUSES = (
    ("F-MEC", 0.35),
    ("F-ELE", 0.25),
    ("F-HID", 0.15),
    ("F-NEU", 0.15),
    ("AJUSTE", 0.10),
)


# --------------------------------------------------------------------------- log
def configure_logging(log_file: Path | None, quiet: bool = False) -> logging.Logger:
    """Log legible en UTC, con archivo opcional. Nunca incluye credenciales."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    )
    formatter.converter = time.gmtime

    if not quiet:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logger.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# ----------------------------------------------------------------------- helpers
def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} debe ser un entero, recibido {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} debe ser numérico, recibido {raw!r}") from exc


def _parse_moment(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"fecha/hora inválida: {value!r} (usa ISO-8601, p. ej. 2026-10-21T00:30:00Z)"
        ) from exc
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _slot_time(moment: datetime, interval: int) -> datetime:
    """Inicio de la rejilla temporal que contiene ``moment``."""
    epoch = int(moment.timestamp())
    return datetime.fromtimestamp((epoch // interval) * interval, UTC)


def _machine_rng(seed: int, id_maquina: int, slot_epoch: int) -> random.Random:
    """RNG determinista por (semilla, máquina, slot)."""
    digest = hashlib.sha256(
        f"{seed}|{id_maquina}|{slot_epoch}".encode("utf-8")
    ).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _resolve_shift(turnos: Sequence[Turno], moment: datetime) -> tuple[Turno, date]:
    """Devuelve el turno que contiene ``moment`` y la fecha de su inicio."""
    for turno in turnos:
        for delta in (-1, 0, 1):
            day = moment.date() + timedelta(days=delta)
            start = datetime.combine(day, turno.hora_inicio, tzinfo=UTC)
            end = start + timedelta(minutes=turno.duracion_min)
            if start <= moment < end:
                return turno, day
    raise RuntimeError(f"No hay turno definido para {_iso(moment)}")


def _choose_failure_cause(rng: random.Random, causas: dict[str, Causa]) -> Causa:
    codigos = [codigo for codigo, _ in FAILURE_CAUSES]
    pesos = [peso for _, peso in FAILURE_CAUSES]
    codigo = rng.choices(codigos, weights=pesos, k=1)[0]
    return causas[codigo]


def _event_id(kind: str, id_maquina: int, moment: datetime) -> str:
    return f"sim-{kind}-{id_maquina:03d}-{int(moment.timestamp())}"


# ---------------------------------------------------------------------- simulador
class Simulator:
    """Bucle de simulación y su estado en memoria."""

    def __init__(
        self,
        catalog: Catalog,
        ingestor: Ingestor,
        run_id: str,
        seed: int,
        interval: int,
        intensity: float,
        dry_run: bool,
        logger: logging.Logger,
    ) -> None:
        self.cat = catalog
        self.ingestor = ingestor
        self.run_id = run_id
        self.seed = seed
        self.interval = interval
        self.intensity = intensity
        self.dry_run = dry_run
        self.log = logger

        self.causas = {causa.codigo: causa for causa in catalog.causas}
        self.maquinas = sorted(catalog.maquinas, key=lambda m: m.id_maquina)
        self.turnos = sorted(catalog.turnos, key=lambda t: t.id_turno)
        self._dias: dict[date, int] = {}
        self._planta_por_maquina = {
            maquina.id_maquina: next(
                linea.id_planta
                for linea in catalog.lineas
                if linea.id_linea == maquina.id_linea
            )
            for maquina in catalog.maquinas
        }
        self._maquinas_con_eventos: set[int] = set()
        self._plantas_con_eventos: set[int] = set()
        self.metrics_file: Path | None = None

        self.metrics = {
            "cycles": 0,
            "events_generated": 0,
            "events_inserted": 0,
            "events_duplicated": 0,
            "stops_generated": 0,
            "stops_inserted": 0,
            "stops_duplicated": 0,
            "latency_sum_seconds": 0.0,
            "latency_max_seconds": 0.0,
            "latency_samples": 0,
            "errors": 0,
        }

    # ------------------------------------------------------------------ soporte
    def _id_tiempo(self, day: date) -> int:
        if day not in self._dias:
            rows = self.ingestor.query(
                "SELECT id_tiempo FROM dim_tiempo WHERE fecha = %s", (day,)
            )
            if not rows:
                raise RuntimeError(
                    f"dim_tiempo no cubre {day.isoformat()}. "
                    "Amplía el calendario o ajusta --at."
                )
            self._dias[day] = int(rows[0][0])
        return self._dias[day]

    def _record(self, result) -> None:
        self.metrics["events_generated"] += result.events_generated
        self.metrics["events_inserted"] += result.events_inserted
        self.metrics["events_duplicated"] += result.events_duplicated
        self.metrics["stops_generated"] += result.stops_generated
        self.metrics["stops_inserted"] += result.stops_inserted
        self.metrics["stops_duplicated"] += result.stops_duplicated
        self.metrics["latency_sum_seconds"] += sum(result.latency_seconds)
        self.metrics["latency_max_seconds"] = max(
            self.metrics["latency_max_seconds"], result.latency_max_seconds
        )
        self.metrics["latency_samples"] += len(result.latency_seconds)

    # ------------------------------------------------------------------ ciclo
    def run_cycle(self, cycle_time: datetime) -> None:
        started = time.perf_counter()
        generated_at = datetime.now(UTC)
        window_end = cycle_time + timedelta(seconds=self.interval)

        events: list[EventRecord] = []

        # 1) Arranques de paradas que terminaron dentro de este ciclo.
        finished = self.ingestor.query(
            "SELECT id_maquina, fin_at FROM fact_parada "
            "WHERE fin_at >= %s AND fin_at < %s AND fin_at > inicio_at "
            "ORDER BY fin_at, id_maquina",
            (cycle_time, window_end),
        )
        for id_maquina, fin_at in finished:
            events.append(
                EventRecord(
                    source_system="iot",
                    source_event_id=_event_id("up", int(id_maquina), fin_at),
                    tipo_evento="transicion_estado",
                    id_maquina=int(id_maquina),
                    event_time=fin_at,
                    generated_at=generated_at,
                    estado="RUNNING",
                    payload={
                        "transicion": "RUNNING",
                        "motivo": "fin de parada",
                        "origen": "simulacion_004",
                    },
                )
            )

        # 2) Máquinas con una parada abierta: no se solapan episodios.
        activas = {
            int(row[0])
            for row in self.ingestor.query(
                "SELECT DISTINCT id_maquina FROM fact_parada "
                "WHERE inicio_at <= %s AND (fin_at IS NULL OR fin_at > %s)",
                (cycle_time, cycle_time),
            )
        }

        # 3) Transiciones nuevas, decididas de forma determinista por slot.
        stops: list[StopRecord] = []
        probability = min(1.0, STOP_PROBABILITY * self.intensity)
        for maquina in self.maquinas:
            if maquina.id_maquina in activas:
                continue
            rng = _machine_rng(self.seed, maquina.id_maquina, int(cycle_time.timestamp()))
            if rng.random() >= probability:
                continue

            if rng.random() < MICRO_SHARE:
                duration = rng.randint(*MICRO_DURATION_MIN)
                causa = self.causas[CAUSA_MICRO]
                microparada = True
            else:
                duration = rng.randint(*FAILURE_DURATION_MIN)
                causa = _choose_failure_cause(rng, self.causas)
                microparada = False

            turno, dia_turno = _resolve_shift(self.turnos, cycle_time)
            id_tiempo = self._id_tiempo(dia_turno)

            stops.append(
                StopRecord(
                    id_maquina=maquina.id_maquina,
                    id_turno=turno.id_turno,
                    id_tiempo=id_tiempo,
                    id_causa=causa.id_causa,
                    inicio_at=cycle_time,
                    fin_at=cycle_time + timedelta(minutes=duration),
                    duracion_min=duration,
                    es_planificada=False,
                    es_microparada=microparada,
                    causa_detalle=(
                        "Ingesta 004: "
                        + ("microparada simulada" if microparada else "falla simulada")
                    ),
                )
            )
            self._maquinas_con_eventos.add(maquina.id_maquina)
            self._plantas_con_eventos.add(
                self._planta_por_maquina[maquina.id_maquina]
            )
            events.append(
                EventRecord(
                    source_system="iot",
                    source_event_id=_event_id("down", maquina.id_maquina, cycle_time),
                    tipo_evento="transicion_estado",
                    id_maquina=maquina.id_maquina,
                    event_time=cycle_time,
                    generated_at=generated_at,
                    estado="DOWN",
                    payload={
                        "transicion": "DOWN",
                        "causa": causa.codigo,
                        "origen": "simulacion_004",
                    },
                )
            )
            events.append(
                EventRecord(
                    source_system="iot",
                    source_event_id=_event_id("parada", maquina.id_maquina, cycle_time),
                    tipo_evento="parada",
                    id_maquina=maquina.id_maquina,
                    event_time=cycle_time,
                    generated_at=generated_at,
                    estado="DOWN",
                    payload={
                        "causa": causa.codigo,
                        "duracion_min": duration,
                        "planificada": False,
                        "microparada": microparada,
                        "origen": "simulacion_004",
                    },
                )
            )

        duration_ms = round((time.perf_counter() - started) * 1000, 1)

        if self.dry_run:
            self.metrics["cycles"] += 1
            self.metrics["events_generated"] += len(events)
            self.metrics["stops_generated"] += len(stops)
            self.log.info(
                "ciclo=%d slot=%s dry_run=true eventos=%d paradas=%d duracion_ms=%s",
                self.metrics["cycles"],
                _iso(cycle_time),
                len(events),
                len(stops),
                duration_ms,
            )
            return

        result = self.ingestor.ingest(events, stops)
        self._record(result)
        self.metrics["cycles"] += 1

        self.log.info(
            "ciclo=%d slot=%s eventos=%d paradas=%d insertados=%d duplicados=%d "
            "paradas_insertadas=%d latencia_media_ms=%.1f duracion_ms=%s",
            self.metrics["cycles"],
            _iso(cycle_time),
            result.events_generated,
            result.stops_generated,
            result.events_inserted,
            result.events_duplicated,
            result.stops_inserted,
            result.latency_avg_seconds * 1000,
            duration_ms,
        )

    # --------------------------------------------------------------- escenario
    def apply_scenario(
        self,
        action: str,
        maquina_codigo: str,
        duration_min: int,
        when: datetime,
    ) -> None:
        if action != "stop":
            raise SystemExit(f"Acción de escenario no soportada: {action!r}")
        maquina = next(
            (m for m in self.maquinas if m.codigo.upper() == maquina_codigo.upper()),
            None,
        )
        if maquina is None:
            raise SystemExit(
                f"Máquina {maquina_codigo!r} no encontrada en dim_maquina "
                f"(códigos válidos: {self.maquinas[0].codigo}…{self.maquinas[-1].codigo})"
            )

        when = when.replace(microsecond=0)
        turno, dia_turno = _resolve_shift(self.turnos, when)
        id_tiempo = self._id_tiempo(dia_turno)
        causa = self.causas[CAUSA_ESCENARIO]
        generado = datetime.now(UTC)

        stop = StopRecord(
            id_maquina=maquina.id_maquina,
            id_turno=turno.id_turno,
            id_tiempo=id_tiempo,
            id_causa=causa.id_causa,
            inicio_at=when,
            fin_at=when + timedelta(minutes=duration_min),
            duracion_min=duration_min,
            es_planificada=False,
            es_microparada=False,
            causa_detalle=f"Ingesta 004: escenario stop {maquina.codigo}",
        )
        events = [
            EventRecord(
                source_system="iot",
                source_event_id=_event_id("sc-down", maquina.id_maquina, when),
                tipo_evento="transicion_estado",
                id_maquina=maquina.id_maquina,
                event_time=when,
                generated_at=generado,
                estado="DOWN",
                payload={
                    "transicion": "DOWN",
                    "causa": causa.codigo,
                    "escenario": "stop",
                    "origen": "simulacion_004",
                },
            ),
            EventRecord(
                source_system="iot",
                source_event_id=_event_id("sc-parada", maquina.id_maquina, when),
                tipo_evento="parada",
                id_maquina=maquina.id_maquina,
                event_time=when,
                generated_at=generado,
                estado="DOWN",
                payload={
                    "causa": causa.codigo,
                    "duracion_min": duration_min,
                    "planificada": False,
                    "microparada": False,
                    "escenario": "stop",
                    "origen": "simulacion_004",
                },
            ),
        ]

        existing_prod = self.ingestor.query(
            "SELECT count(*) FROM fact_produccion "
            "WHERE id_maquina = %s AND id_turno = %s AND id_tiempo = %s",
            (maquina.id_maquina, turno.id_turno, id_tiempo),
        )
        if int(existing_prod[0][0]) > 0:
            self.log.warning(
                "escenario stop %s: el turno %s de %s ya tiene producción histórica; "
                "el KPI de downtime prioriza fact_produccion",
                maquina.codigo,
                turno.codigo,
                dia_turno.isoformat(),
            )

        self.log.info(
            "escenario=stop maquina=%s turno=%s fecha=%s inicio=%s duracion_min=%d "
            "causa=%s id_tiempo=%d",
            maquina.codigo,
            turno.codigo,
            dia_turno.isoformat(),
            _iso(when),
            duration_min,
            causa.codigo,
            id_tiempo,
        )

        if self.dry_run:
            self.metrics["stops_generated"] += 1
            self.metrics["events_generated"] += len(events)
            self._maquinas_con_eventos.add(maquina.id_maquina)
            self._plantas_con_eventos.add(self._planta_por_maquina[maquina.id_maquina])
            self.log.info("escenario dry_run=true: no se persistió nada")
            return

        result = self.ingestor.ingest(events, [stop])
        self._record(result)
        insertado = "sí" if result.stops_inserted else "no (ya existía)"
        self.log.info(
            "escenario aplicado maquina=%s parada_insertada=%s eventos=%d "
            "insertados=%d duplicados=%d",
            maquina.codigo,
            insertado,
            result.events_generated,
            result.events_inserted,
            result.events_duplicated,
        )

    # -------------------------------------------------------------------- bucle
    def run(
        self,
        cycles: int,
        once: bool,
        at: datetime | None,
        scenario: tuple[str, str] | None,
        stop_duration_min: int,
    ) -> int:
        exit_code = 0
        interrupted = False
        started = datetime.now(UTC)

        self.log.info(
            "inicio run_id=%s version=%s intervalo_s=%d seed=%s intensidad=%s "
            "maquinas=%d dry_run=%s reloj=%s",
            self.run_id,
            VERSION,
            self.interval,
            self.seed,
            self.intensity,
            len(self.maquinas),
            self.dry_run,
            "fijo" if at else "sistema",
        )

        try:
            if scenario is not None:
                self.apply_scenario(
                    action=scenario[0],
                    maquina_codigo=scenario[1],
                    duration_min=stop_duration_min,
                    when=at or datetime.now(UTC),
                )

            planned_cycles = 1 if once else cycles
            index = 0
            while planned_cycles == 0 or index < planned_cycles:
                base = at + timedelta(seconds=index * self.interval) if at else datetime.now(UTC)
                cycle_time = _slot_time(base, self.interval)
                self.run_cycle(cycle_time)
                index += 1

                if once or (planned_cycles and index >= planned_cycles):
                    break
                if at is None:
                    # Avanza siempre al siguiente slot del ciclo actual: evita
                    # repetir un slot si `sleep` despierta unos milisegundos antes.
                    next_epoch = int(cycle_time.timestamp()) + self.interval
                    wait = next_epoch - time.time() + 0.05
                    if wait > 0:
                        time.sleep(wait)
        except KeyboardInterrupt:
            interrupted = True
            self.log.info("interrupción recibida (Ctrl+C/SIGTERM); cerrando de forma controlada")
        except IngestError as exc:
            self.metrics["errors"] += 1
            exit_code = 2
            self.log.error("ingesta abortada: %s", exc)
        except SystemExit as exc:
            self.metrics["errors"] += 1
            exit_code = exc.code if isinstance(exc.code, int) else 1
            self.log.error("escenario inválido: %s", exc)
        except RuntimeError as exc:
            self.metrics["errors"] += 1
            exit_code = 1
            self.log.error("error de simulación: %s", exc)
        finally:
            finished = datetime.now(UTC)
            metrics = self.metrics_dict(started, finished, interrupted)
            self._write_metrics(metrics)
            self.log.info(
                "fin run_id=%s ciclos=%d eventos=%d insertados=%d duplicados=%d "
                "paradas=%d insertadas=%d latencia_media_ms=%.1f latencia_max_ms=%.1f "
                "errores=%d cobertura_maquinas=%d/%d cobertura_plantas=%d motivo=%s",
                self.run_id,
                metrics["cycles"],
                metrics["events_generated"],
                metrics["events_inserted"],
                metrics["events_duplicated"],
                metrics["stops_generated"],
                metrics["stops_inserted"],
                metrics["latency_avg_seconds"] * 1000,
                metrics["latency_max_seconds"] * 1000,
                metrics["errors"],
                metrics["maquinas_con_eventos"],
                len(self.maquinas),
                metrics["plantas_con_eventos"],
                metrics["exit_reason"],
            )
            self.ingestor.close()

        return exit_code

    # ------------------------------------------------------------------ métricas
    def metrics_dict(
        self, started: datetime, finished: datetime, interrupted: bool
    ) -> dict:
        samples = self.metrics["latency_samples"]
        latency_avg = (
            self.metrics["latency_sum_seconds"] / samples if samples else 0.0
        )
        if interrupted:
            exit_reason = "interrumpido"
        elif self.metrics["errors"]:
            exit_reason = "error"
        else:
            exit_reason = "completado"
        return {
            "version": VERSION,
            "run_id": self.run_id,
            "started_at": _iso(started),
            "finished_at": _iso(finished),
            "duration_seconds": round((finished - started).total_seconds(), 3),
            "interval_seconds": self.interval,
            "seed": self.seed,
            "intensity": self.intensity,
            "dry_run": self.dry_run,
            "cycles": self.metrics["cycles"],
            "events_generated": self.metrics["events_generated"],
            "events_inserted": self.metrics["events_inserted"],
            "events_duplicated": self.metrics["events_duplicated"],
            "stops_generated": self.metrics["stops_generated"],
            "stops_inserted": self.metrics["stops_inserted"],
            "stops_duplicated": self.metrics["stops_duplicated"],
            "latency_avg_seconds": round(latency_avg, 6),
            "latency_max_seconds": round(self.metrics["latency_max_seconds"], 6),
            "errors": self.metrics["errors"],
            "maquinas_con_eventos": len(self._maquinas_con_eventos),
            "plantas_con_eventos": len(self._plantas_con_eventos),
            "exit_reason": exit_reason,
        }

    def _write_metrics(self, metrics: dict) -> None:
        if self.metrics_file is None:
            return
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_file.write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.log.info("métricas escritas en %s", self.metrics_file)


# --------------------------------------------------------------------------- CLI
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simula la ingesta continua de eventos sintéticos en PostgreSQL."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=_env_int("SIM_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS),
        help="segundos entre ciclos (default: SIM_INTERVAL_SECONDS o 60)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=0,
        help="número de ciclos; 0 = indefinido (default: 0)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="ejecuta un solo ciclo y termina (equivalente a --cycles 1 sin esperas)",
    )
    parser.add_argument(
        "--at",
        type=_parse_moment,
        default=None,
        help="reloj fijo ISO-8601 en UTC, para pruebas reproducibles",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=_env_int("SIM_SEED", DEFAULT_SEED),
        help="semilla de las decisiones (default: SIM_SEED o 42)",
    )
    parser.add_argument(
        "--intensity",
        type=float,
        default=_env_float("SIM_INTENSITY", DEFAULT_INTENSITY),
        help="multiplicador de la probabilidad de parada (default: SIM_INTENSITY o 1.0)",
    )
    parser.add_argument(
        "--scenario",
        nargs=2,
        metavar=("ACCION", "MAQUINA"),
        default=None,
        help="escenario reproducible, p. ej. --scenario stop M-001",
    )
    parser.add_argument(
        "--stop-duration-min",
        type=int,
        default=DEFAULT_STOP_DURATION_MIN,
        help=f"duración del escenario stop en minutos (default: {DEFAULT_STOP_DURATION_MIN})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="genera y registra los eventos sin insertarlos",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS,
        help=f"intentos ante error de base (default: {DEFAULT_MAX_ATTEMPTS})",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_BASE_DELAY,
        help=f"espera inicial entre reintentos en segundos (default: {DEFAULT_BASE_DELAY})",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help=f"archivo de log (default: {DEFAULT_LOG_FILE})",
    )
    parser.add_argument(
        "--metrics-file",
        type=Path,
        default=None,
        help="JSON de métricas (default: logs/simulate_events_<run_id>.json)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="no escribe en consola (solo en el archivo de log)",
    )
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> None:
    if args.interval < 5:
        raise SystemExit("--interval debe ser >= 5 segundos")
    if args.cycles < 0:
        raise SystemExit("--cycles debe ser >= 0")
    if args.intensity <= 0:
        raise SystemExit("--intensity debe ser > 0")
    if args.stop_duration_min <= 0:
        raise SystemExit("--stop-duration-min debe ser > 0")
    if args.scenario is not None:
        action, machine = args.scenario
        if action != "stop":
            raise SystemExit("--scenario solo admite la acción 'stop'")
        if not machine.strip():
            raise SystemExit("--scenario requiere el código de máquina, p. ej. M-001")
    if args.at is not None:
        limit = datetime.now(UTC) + timedelta(minutes=5)
        if args.at > limit:
            raise SystemExit(
                "--at no puede estar más de 5 minutos en el futuro "
                "(rango válido de eventos de la Constitución §7.1)"
            )


def _install_signal_handlers() -> None:
    def handler(signum, frame):  # noqa: ANN001 - firma de signal
        raise KeyboardInterrupt

    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):  # pragma: no cover - fuera del hilo principal
                pass


def _write_failure_metrics(
    path: Path,
    run_id: str,
    started: datetime,
    error: BaseException,
    exit_reason: str,
) -> None:
    """Registra una ejecución fallida antes de crear el simulador."""
    payload = {
        "version": VERSION,
        "run_id": run_id,
        "started_at": _iso(started),
        "finished_at": _iso(datetime.now(UTC)),
        "errors": 1,
        "exit_reason": exit_reason,
        "error": f"{type(error).__name__}: {error}",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _validate_args(args)
    _install_signal_handlers()

    logger = configure_logging(args.log_file, quiet=args.quiet)
    run_id = f"sim-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
    reference = args.at or datetime.now(UTC)
    metrics_file = args.metrics_file or Path(f"logs/simulate_events_{run_id}.json")

    ingestor = Ingestor(
        run_id=run_id,
        max_attempts=args.max_attempts,
        base_delay=args.retry_delay,
        logger=logger,
    )

    started = datetime.now(UTC)
    try:
        conn = ingestor.connection()
        catalog = load_catalog(
            conn,
            start_date=reference.date(),
            end_date=reference.date(),
            max_plantas=3,
            max_maquinas=52,
        )
    except IngestError as exc:
        logger.error("no se pudo conectar a PostgreSQL: %s", exc)
        ingestor.close()
        _write_failure_metrics(
            metrics_file, run_id, started, exc, "error_conexion"
        )
        return 2
    except RuntimeError as exc:
        logger.error("configuración inválida: %s", exc)
        ingestor.close()
        _write_failure_metrics(
            metrics_file, run_id, started, exc, "error_configuracion"
        )
        return 1

    simulator = Simulator(
        catalog=catalog,
        ingestor=ingestor,
        run_id=run_id,
        seed=args.seed,
        interval=args.interval,
        intensity=args.intensity,
        dry_run=args.dry_run,
        logger=logger,
    )
    simulator.metrics_file = metrics_file

    logger.info(
        "catálogo cargado plantas=%d lineas=%d maquinas=%d turnos=%d causas=%d",
        len(catalog.plantas),
        len(catalog.lineas),
        len(catalog.maquinas),
        len(catalog.turnos),
        len(catalog.causas),
    )

    return simulator.run(
        cycles=args.cycles,
        once=args.once,
        at=args.at,
        scenario=tuple(args.scenario) if args.scenario else None,
        stop_duration_min=args.stop_duration_min,
    )


if __name__ == "__main__":
    sys.exit(main())
