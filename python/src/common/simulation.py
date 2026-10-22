"""Motor de simulación del histórico sintético de MetalNova.

Principios de diseño:

- **Eventos por transición**, no snapshots: cada arranque/parada de estado y cada
  evento de negocio (orden, inspección, intervención, lectura) genera una fila en
  ``fact_evento``. No se muestrea cada minuto por máquina.
- **Reproducibilidad**: toda la aleatoriedad proviene de ``random.Random(semilla)``
  y el recorrido (día → turno → máquina) es estable.
- **Coherencia de tiempos**: se planifican primero las paradas y luego se calcula
  el runtime; se cumplen las invariantes de ``fact_produccion``.
- **Memoria acotada**: las filas se escriben en CSV en streaming.

Todos los datos son sintéticos.

El escenario ``calibracion`` añade factores de planta y perfiles persistentes
por máquina (``dim_maquina.perfil_rendimiento``) para producir una dispersión
visible entre plantas y outliers de máquina. El escenario ``degradado``
original conserva sus parámetros neutros y sigue siendo reproducible.
"""

from __future__ import annotations

import json
import math
import random
import resource
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .catalog import Catalog, Causa, Maquina, Producto, Tecnico, Turno
from .csvio import CsvTable

UTC = timezone.utc

SHIFT_MIN = 480
BREAK_MIN = 30
MIN_RUNTIME_MIN = 45
MICROSTOP_MAX_MIN = 4

HEADERS: dict[str, tuple[str, ...]] = {
    "dim_orden": (
        "id_orden",
        "codigo_orden",
        "id_producto",
        "cantidad_planificada",
        "fecha_plan",
        "estado",
    ),
    "fact_mantenimiento": (
        "codigo_orden_trabajo",
        "id_maquina",
        "id_tecnico",
        "id_causa",
        "id_turno",
        "id_tiempo",
        "tipo",
        "inicio_at",
        "fin_at",
        "duracion_min",
        "costo_estimado_usd",
        "estado",
    ),
    "fact_parada": (
        "id_maquina",
        "id_turno",
        "id_tiempo",
        "id_causa",
        "codigo_orden_trabajo",
        "inicio_at",
        "fin_at",
        "duracion_min",
        "es_planificada",
        "es_microparada",
        "causa_detalle",
    ),
    "fact_produccion": (
        "id_orden",
        "id_maquina",
        "id_producto",
        "id_turno",
        "id_tiempo",
        "inicio_at",
        "fin_at",
        "tiempo_calendario_min",
        "tiempo_planificado_min",
        "downtime_planificado_min",
        "tiempo_operativo_min",
        "downtime_no_planificado_min",
        "total_count",
        "good_count",
        "scrap_count",
        "ciclo_ideal_segundos",
        "energia_kwh",
    ),
    "fact_calidad": (
        "codigo_inspeccion",
        "codigo_lote",
        "id_maquina",
        "id_producto",
        "id_turno",
        "id_tiempo",
        "id_causa",
        "inspeccion_at",
        "unidades_inspeccionadas",
        "unidades_buenas",
        "unidades_defectuosas",
        "unidades_retrabajo",
        "es_retrabajo",
    ),
    "fact_evento": (
        "source_system",
        "source_event_id",
        "tipo_evento",
        "id_maquina",
        "event_time",
        "generated_at",
        "run_id",
        "estado",
        "temperatura_c",
        "energia_kwh",
        "payload",
    ),
}

TABLES = tuple(HEADERS)

# Factores por turno: (rendimiento, multiplicador de fallas, calidad, microparadas)
SHIFT_FACTORS = {
    "A": (0.97, 0.80, 0.997, 0.80),
    "B": (0.94, 1.00, 0.994, 1.00),
    "C": (0.90, 1.30, 0.990, 1.25),
}

CRITICIDAD_FACTOR = {"A": 1.35, "B": 1.00, "C": 0.75}

CALIBRATION_SCENARIO = "calibracion"


@dataclass(frozen=True)
class FactorSet:
    """Multiplicadores de calibración para una planta o un perfil de máquina.

    Los valores por defecto (1.0) reproducen el escenario degradado original.
    """

    rendimiento: float = 1.0
    fallas: float = 1.0
    calidad: float = 1.0
    energia: float = 1.0
    reparacion: float = 1.0
    microparadas: float = 1.0

    def combine(self, other: "FactorSet") -> "FactorSet":
        return FactorSet(
            rendimiento=self.rendimiento * other.rendimiento,
            fallas=self.fallas * other.fallas,
            calidad=self.calidad * other.calidad,
            energia=self.energia * other.energia,
            reparacion=self.reparacion * other.reparacion,
            microparadas=self.microparadas * other.microparadas,
        )


# Escenario 'calibracion': separa las plantas y añade máquinas outlier
# persistentes. Los valores son parámetros de diseño sintéticos, no telemetría.
PLANT_FACTORS = {
    1: FactorSet(rendimiento=0.934, fallas=0.90, calidad=1.00, energia=1.00),
    2: FactorSet(rendimiento=0.898, fallas=1.00, calidad=0.995, energia=1.05),
    3: FactorSet(rendimiento=0.873, fallas=1.15, calidad=0.985, energia=1.10),
}

PROFILE_FACTORS = {
    "estandar": FactorSet(),
    "desgastada": FactorSet(
        rendimiento=0.87, fallas=1.45, calidad=0.995, energia=1.05,
        reparacion=1.10, microparadas=1.20,
    ),
    "critica": FactorSet(
        rendimiento=0.76, fallas=2.20, calidad=0.990, energia=1.15,
        reparacion=1.40, microparadas=1.50,
    ),
    "calidad": FactorSet(
        rendimiento=0.97, fallas=1.05, calidad=0.94, energia=1.02,
    ),
    "energia": FactorSet(
        rendimiento=0.98, fallas=1.00, calidad=0.997, energia=1.70,
    ),
}

CALIBRATION_GLOBAL_FACTORS = FactorSet(calidad=0.98)
CALIBRATION_QUALITY_DEGRADATION = 0.03
CALIBRATION_PERFORMANCE_DEGRADATION = 0.15
CALIBRATION_FAILURE_DEGRADATION = 0.40
CALIBRATION_ENERGY_DEGRADATION = 0.01
CALIBRATION_PERFORMANCE_FLOOR = 0.45


def calibration_manifest() -> dict[str, Any]:
    """Configuración serializable para el manifiesto de la corrida."""
    return {
        "version": "1.0.0",
        "plantas": {
            str(pid): {
                "rendimiento": f.rendimiento,
                "fallas": f.fallas,
                "calidad": f.calidad,
                "energia": f.energia,
            }
            for pid, f in PLANT_FACTORS.items()
        },
        "perfiles": {
            name: {
                "rendimiento": f.rendimiento,
                "fallas": f.fallas,
                "calidad": f.calidad,
                "energia": f.energia,
                "reparacion": f.reparacion,
                "microparadas": f.microparadas,
            }
            for name, f in PROFILE_FACTORS.items()
        },
        "global": {
            "rendimiento": CALIBRATION_GLOBAL_FACTORS.rendimiento,
            "fallas": CALIBRATION_GLOBAL_FACTORS.fallas,
            "calidad": CALIBRATION_GLOBAL_FACTORS.calidad,
            "energia": CALIBRATION_GLOBAL_FACTORS.energia,
            "quality_degradation": CALIBRATION_QUALITY_DEGRADATION,
            "performance_degradation": CALIBRATION_PERFORMANCE_DEGRADATION,
            "failure_degradation": CALIBRATION_FAILURE_DEGRADATION,
            "energy_degradation": CALIBRATION_ENERGY_DEGRADATION,
            "performance_floor": CALIBRATION_PERFORMANCE_FLOOR,
        },
    }

MACHINE_KW = {
    "CNC": 18.0,
    "Prensa": 25.0,
    "Inyectora": 30.0,
    "Soldadora": 22.0,
    "Rectificadora": 15.0,
}

TEMP_OFFSET = {
    "CNC": 0.0,
    "Prensa": 6.0,
    "Inyectora": 8.0,
    "Soldadora": 5.0,
    "Rectificadora": 2.0,
}

FAILURE_CAUSES = (
    ("F-MEC", 0.35),
    ("F-ELE", 0.25),
    ("F-HID", 0.15),
    ("F-NEU", 0.15),
    ("AJUSTE", 0.10),
)

SPECIALTY_BY_CAUSE = {
    "F-MEC": "Mecánica",
    "F-ELE": "Eléctrica",
    "F-HID": "Mecánica",
    "F-NEU": "Mecánica",
    "AJUSTE": "Automatización",
}


@dataclass(frozen=True)
class SimParams:
    seed: int
    days: int
    start_date: date
    end_date: date
    escenario: str
    intensidad: float


@dataclass
class Stop:
    """Episodio de parada dentro de un turno."""

    offset: int
    duration: int
    causa: Causa
    planificada: bool
    microparada: bool
    estado: str
    detalle: str
    maintenance: dict[str, Any] | None = None

    @property
    def end_offset(self) -> int:
        return self.offset + self.duration


@dataclass
class DayTotals:
    planned: int = 0
    runtime: int = 0
    ideal_min: float = 0.0
    total_count: int = 0
    good_count: int = 0


def _fmt_dt(value: datetime) -> str:
    return value.isoformat()


def _fmt_dec(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def _fmt_bool(value: bool) -> str:
    return "true" if value else "false"


def _fmt_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _peak_memory_mb() -> float:
    try:
        # En Linux ru_maxrss se expresa en KiB.
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)
    except (AttributeError, ValueError):  # pragma: no cover - fuera de Linux
        return 0.0


class HistoryGenerator:
    """Genera el histórico completo y lo vuelca a CSV."""

    def __init__(
        self,
        catalog: Catalog,
        params: SimParams,
        output_dir: Path,
        run_tag: str,
    ) -> None:
        self.cat = catalog
        self.params = params
        self.rng = random.Random(params.seed)
        self.run_tag = run_tag
        self.run_id = f"hist-{run_tag}"

        self.tables: dict[str, CsvTable] = {
            name: CsvTable(output_dir / f"{name}.csv", HEADERS[name]) for name in TABLES
        }

        self.event_seq = 0
        self.order_seq = 0
        self.maintenance_seq = 0
        self.inspection_seq = 0

        self.producto_actual: dict[int, int] = {}
        self.turnos_restantes: dict[int, int] = {}
        self.daily: dict[date, DayTotals] = {}

        self.causas = {c.codigo: c for c in catalog.causas}
        self.turnos = sorted(catalog.turnos, key=lambda t: t.id_turno)
        self.maquinas = sorted(catalog.maquinas, key=lambda m: m.id_maquina)
        self.familias = sorted(catalog.familias, key=lambda f: f.id_familia)

        # Dos líneas por familia (3 familias × 2 líneas en el catálogo sembrado).
        self.familia_por_linea = {
            linea.id_linea: self.familias[(linea.id_linea - 1) // 2 % len(self.familias)]
            for linea in catalog.lineas
        }
        self.tecnicos_por_especialidad: dict[str, list[Tecnico]] = {}
        for tecnico in catalog.tecnicos:
            self.tecnicos_por_especialidad.setdefault(tecnico.especialidad, []).append(tecnico)

        self._validate_catalog()

    # ------------------------------------------------------------------ setup
    def _validate_catalog(self) -> None:
        for codigo in ("DESCANSO", "CAM-PROD", "MANT-PREV", "MICRO"):
            if codigo not in self.causas:
                raise RuntimeError(
                    f"Falta la causa '{codigo}' en dim_causa. "
                    "Ejecuta sql/apply_all.sql antes de generar."
                )
        for linea in self.cat.lineas:
            familia = self.familia_por_linea[linea.id_linea]
            self.cat.productos_de_familia(familia.id_familia)
        faltantes = [d for d in self._fechas() if d not in self.cat.dias]
        if faltantes:
            raise RuntimeError(
                "dim_tiempo no cubre el rango solicitado; faltan fechas como "
                f"{faltantes[0].isoformat()}. Ejecuta sql/apply_all.sql."
            )

    def _fechas(self) -> list[date]:
        return [self.params.start_date + timedelta(days=i) for i in range(self.params.days)]

    # -------------------------------------------------------------------- run
    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            for index, fecha in enumerate(self._fechas()):
                progress = index / max(self.params.days - 1, 1)
                for turno in self.turnos:
                    for maquina in self.maquinas:
                        self._shift(fecha, turno, maquina, progress)
        except Exception:
            # No publicar CSV parciales: se descartan los temporales.
            for table in self.tables.values():
                table.abort()
            raise
        else:
            for table in self.tables.values():
                table.close()
        elapsed = round(time.perf_counter() - started, 2)

        counts = {name: table.rows for name, table in self.tables.items()}
        files = [
            {
                "name": f"{name}.csv",
                "rows": table.rows,
                "bytes": table.bytes,
                "path": str(table.path).replace("\\", "/"),
            }
            for name, table in self.tables.items()
        ]
        daily = self._daily_summary()
        return {
            "counts": counts,
            "files": files,
            "duration_seconds": elapsed,
            "peak_memory_mb": _peak_memory_mb(),
            "daily_oee": daily,
            "oee_first_7d": self._average_oee(daily[:7]),
            "oee_last_7d": self._average_oee(daily[-7:]),
            "total_source_events": counts["fact_evento"],
        }

    @staticmethod
    def _average_oee(days: list[dict[str, Any]]) -> float | None:
        values = [d["oee"] for d in days if d["oee"] is not None]
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    def _daily_summary(self) -> list[dict[str, Any]]:
        summary: list[dict[str, Any]] = []
        for fecha in sorted(self.daily):
            totals = self.daily[fecha]
            availability = totals.runtime / totals.planned if totals.planned else None
            performance = (
                totals.ideal_min / totals.runtime if totals.runtime else None
            )
            quality = (
                totals.good_count / totals.total_count if totals.total_count else None
            )
            oee = None
            if None not in (availability, performance, quality):
                oee = round(availability * performance * quality, 4)  # type: ignore[operator]
            summary.append(
                {
                    "fecha": fecha.isoformat(),
                    "oee": oee,
                    "disponibilidad": round(availability, 4) if availability is not None else None,
                    "rendimiento": round(performance, 4) if performance is not None else None,
                    "calidad": round(quality, 4) if quality is not None else None,
                }
            )
        return summary

    # --------------------------------------------------------------- factores
    def _factors_for(self, maquina: Maquina) -> FactorSet:
        """Factores de calibración; el escenario degradado queda neutro."""
        if self.params.escenario != CALIBRATION_SCENARIO:
            return FactorSet()
        planta = PLANT_FACTORS.get(maquina.id_planta, FactorSet())
        perfil = PROFILE_FACTORS.get(maquina.perfil_rendimiento, FactorSet())
        return planta.combine(perfil).combine(CALIBRATION_GLOBAL_FACTORS)

    # ------------------------------------------------------------------ turno
    def _shift(
        self,
        fecha: date,
        turno: Turno,
        maquina: Maquina,
        progress: float,
    ) -> None:
        id_tiempo = self.cat.dias[fecha]
        shift_start = datetime.combine(fecha, turno.hora_inicio, tzinfo=UTC)
        shift_end = shift_start + timedelta(minutes=turno.duracion_min)

        calibracion = self.params.escenario == CALIBRATION_SCENARIO
        degradation = (
            progress
            if self.params.escenario in ("degradado", CALIBRATION_SCENARIO)
            else progress * 0.15
        )
        perf_shift, fail_mult, quality_shift, micro_mult = SHIFT_FACTORS.get(
            turno.codigo, (0.93, 1.0, 0.993, 1.0)
        )
        factors = self._factors_for(maquina)
        perf_shift *= factors.rendimiento
        fail_mult *= factors.fallas
        quality_shift *= factors.calidad
        micro_mult *= factors.microparadas
        weekend = fecha.weekday() >= 5
        if weekend:
            perf_shift -= 0.015
            fail_mult *= 1.10
            quality_shift -= 0.001

        producto, cambio_producto = self._choose_product(maquina)

        intervals: list[tuple[int, int]] = []
        stops: list[Stop] = []

        # --- Paradas planificadas -----------------------------------------
        break_start = self._place(intervals, BREAK_MIN, 100, 320)
        if break_start is not None:
            stops.append(
                Stop(
                    offset=break_start,
                    duration=BREAK_MIN,
                    causa=self.causas["DESCANSO"],
                    planificada=True,
                    microparada=False,
                    estado="IDLE",
                    detalle="Descanso programado de turno",
                )
            )

        if cambio_producto:
            change_min = self.rng.randint(15, 45)
            change_start = self._place(intervals, change_min, 120, 380)
            if change_start is not None:
                stops.append(
                    Stop(
                        offset=change_start,
                        duration=change_min,
                        causa=self.causas["CAM-PROD"],
                        planificada=True,
                        microparada=False,
                        estado="IDLE",
                        detalle=f"Cambio de producto a {producto.codigo}",
                    )
                )

        if self.rng.random() < 0.008:
            preventive_min = self.rng.randint(60, 120)
            preventive_start = self._place(intervals, preventive_min, 60, 380)
            if preventive_start is not None:
                maintenance = self._new_maintenance(
                    maquina=maquina,
                    turno=turno,
                    id_tiempo=id_tiempo,
                    inicio=shift_start + timedelta(minutes=preventive_start),
                    duration=preventive_min,
                    causa=self.causas["MANT-PREV"],
                    tipo="preventivo",
                )
                stops.append(
                    Stop(
                        offset=preventive_start,
                        duration=preventive_min,
                        causa=self.causas["MANT-PREV"],
                        planificada=True,
                        microparada=False,
                        estado="MAINT",
                        detalle="Mantenimiento preventivo programado",
                        maintenance=maintenance,
                    )
                )

        planned_downtime = sum(stop.duration for stop in stops)
        available = SHIFT_MIN - planned_downtime

        # --- Microparadas y fallas (no planificadas) -----------------------
        unplanned = 0
        micro_lambda = 1.1 * self.params.intensidad * micro_mult * (1 + 0.8 * degradation)
        micro_count = min(4, self._poisson(micro_lambda))
        for _ in range(micro_count):
            duration = self.rng.randint(1, MICROSTOP_MAX_MIN)
            if available - unplanned - duration < MIN_RUNTIME_MIN:
                break
            start = self._place(intervals, duration, 20, 460)
            if start is None:
                break
            stops.append(
                Stop(
                    offset=start,
                    duration=duration,
                    causa=self.causas["MICRO"],
                    planificada=False,
                    microparada=True,
                    estado="DOWN",
                    detalle="Microparada sin orden de trabajo",
                )
            )
            unplanned += duration

        failure_degradation = (
            CALIBRATION_FAILURE_DEGRADATION if calibracion else 2.5
        )
        failure_lambda = (
            0.055
            * self.params.intensidad
            * CRITICIDAD_FACTOR.get(maquina.criticidad, 1.0)
            * fail_mult
            * (1 + failure_degradation * degradation)
        )
        failure_count = min(2, self._poisson(failure_lambda))
        for _ in range(failure_count):
            duration = int(min(180, max(5, self.rng.lognormvariate(2.7, 0.6))))
            duration = int(duration * factors.reparacion)
            duration = min(duration, available - unplanned - MIN_RUNTIME_MIN)
            if duration < 5:
                break
            start = self._place(intervals, duration, 20, 470)
            if start is None:
                break
            causa = self._failure_cause()
            maintenance = self._new_maintenance(
                maquina=maquina,
                turno=turno,
                id_tiempo=id_tiempo,
                inicio=shift_start + timedelta(minutes=start),
                duration=duration,
                causa=causa,
                tipo="correctivo",
            )
            stops.append(
                Stop(
                    offset=start,
                    duration=duration,
                    causa=causa,
                    planificada=False,
                    microparada=False,
                    estado="DOWN",
                    detalle=f"Falla {causa.codigo} atendida por CMMS",
                    maintenance=maintenance,
                )
            )
            unplanned += duration

        runtime = available - unplanned
        if runtime < 0:  # defensa: no debería ocurrir por las comprobaciones previas
            runtime = 0

        # --- Producción y calidad -----------------------------------------
        cycle = self._cycle_seconds(producto)
        performance_degradation = (
            CALIBRATION_PERFORMANCE_DEGRADATION if calibracion else 0.10
        )
        performance = (
            perf_shift
            * (1 - performance_degradation * degradation)
            * (1 + self.rng.uniform(-0.02, 0.02))
        )
        performance_floor = CALIBRATION_PERFORMANCE_FLOOR if calibracion else 0.55
        performance = max(performance_floor, min(0.99, performance))
        total_count = int(runtime * 60 / cycle * performance)

        quality_degradation = (
            CALIBRATION_QUALITY_DEGRADATION if calibracion else 0.05
        )
        quality = (
            quality_shift
            * (1 - quality_degradation * degradation)
            * (1 + self.rng.uniform(-0.002, 0.002))
        )
        quality = max(0.90, min(0.999, quality))
        good_count = int(total_count * quality)
        scrap_count = total_count - good_count

        machine_kw = MACHINE_KW.get(maquina.tipo, 20.0)
        energy_degradation = (
            CALIBRATION_ENERGY_DEGRADATION if calibracion else 0.10
        )
        energy = (
            machine_kw
            * (runtime / 60)
            * (0.75 + 0.25 * performance)
            * (1 + energy_degradation * degradation)
            * factors.energia
        )

        self.order_seq += 1
        id_orden = self.order_seq
        codigo_orden = f"ORD-{self.run_tag}-{id_orden:06d}"
        planned_target = int((SHIFT_MIN - planned_downtime) * 60 / cycle * 0.95)
        cantidad_planificada = max(total_count, planned_target)

        self.tables["dim_orden"].write(
            [
                id_orden,
                codigo_orden,
                producto.id_producto,
                cantidad_planificada,
                fecha.isoformat(),
                "cerrada",
            ]
        )

        self.tables["fact_produccion"].write(
            [
                id_orden,
                maquina.id_maquina,
                producto.id_producto,
                turno.id_turno,
                id_tiempo,
                _fmt_dt(shift_start),
                _fmt_dt(shift_end),
                SHIFT_MIN,
                SHIFT_MIN - planned_downtime,
                planned_downtime,
                runtime,
                unplanned,
                total_count,
                good_count,
                scrap_count,
                _fmt_dec(cycle, 3),
                _fmt_dec(energy, 4),
            ]
        )

        self._accumulate_day(
            fecha=fecha,
            planned=SHIFT_MIN - planned_downtime,
            runtime=runtime,
            ideal_min=cycle * total_count / 60,
            total_count=total_count,
            good_count=good_count,
        )

        # --- Inspección de calidad (una por turno/máquina) -----------------
        self.inspection_seq += 1
        codigo_inspeccion = f"INS-{self.run_tag}-{self.inspection_seq:07d}"
        codigo_lote = f"LOTE-{maquina.id_maquina:03d}-{fecha:%Y%m%d}-{turno.codigo}"
        inspection_at = shift_end - timedelta(minutes=10)
        retrabajo = int(scrap_count * 0.5)
        self.tables["fact_calidad"].write(
            [
                codigo_inspeccion,
                codigo_lote,
                maquina.id_maquina,
                producto.id_producto,
                turno.id_turno,
                id_tiempo,
                None,
                _fmt_dt(inspection_at),
                total_count,
                good_count,
                scrap_count,
                retrabajo,
                _fmt_bool(retrabajo > 0),
            ]
        )

        # --- Órdenes de mantenimiento --------------------------------------
        for stop in sorted(stops, key=lambda s: s.offset):
            if stop.maintenance is None:
                continue
            item = stop.maintenance
            self.tables["fact_mantenimiento"].write(
                [
                    item["codigo"],
                    maquina.id_maquina,
                    item["id_tecnico"],
                    item["id_causa"],
                    turno.id_turno,
                    id_tiempo,
                    item["tipo"],
                    _fmt_dt(item["inicio"]),
                    _fmt_dt(item["fin"]),
                    item["duracion_min"],
                    _fmt_dec(item["costo"], 2),
                    "cerrada",
                ]
            )

        # --- Paradas -------------------------------------------------------
        for stop in sorted(stops, key=lambda s: s.offset):
            self.tables["fact_parada"].write(
                [
                    maquina.id_maquina,
                    turno.id_turno,
                    id_tiempo,
                    stop.causa.id_causa,
                    stop.maintenance["codigo"] if stop.maintenance else None,
                    _fmt_dt(shift_start + timedelta(minutes=stop.offset)),
                    _fmt_dt(shift_start + timedelta(minutes=stop.end_offset)),
                    stop.duration,
                    _fmt_bool(stop.planificada),
                    _fmt_bool(stop.microparada),
                    stop.detalle,
                ]
            )

        # --- Eventos de origen (por transición, no snapshots) --------------
        self._emit_event(
            system="mes",
            tipo="orden_produccion",
            maquina=maquina,
            when=shift_start,
            payload={
                "id_orden": id_orden,
                "codigo_orden": codigo_orden,
                "id_producto": producto.id_producto,
                "cantidad_planificada": cantidad_planificada,
            },
        )
        self._emit_event(
            system="iot",
            tipo="transicion_estado",
            maquina=maquina,
            when=shift_start,
            estado="RUNNING",
            payload={"transicion": "RUNNING", "motivo": "inicio de turno"},
        )

        for stop in sorted(stops, key=lambda s: s.offset):
            stop_start = shift_start + timedelta(minutes=stop.offset)
            stop_end = shift_start + timedelta(minutes=stop.end_offset)
            self._emit_event(
                system="iot",
                tipo="transicion_estado",
                maquina=maquina,
                when=stop_start,
                estado=stop.estado,
                payload={
                    "transicion": stop.estado,
                    "causa": stop.causa.codigo,
                    "planificada": stop.planificada,
                },
            )
            self._emit_event(
                system="iot",
                tipo="parada",
                maquina=maquina,
                when=stop_start,
                estado=stop.estado,
                payload={
                    "causa": stop.causa.codigo,
                    "duracion_min": stop.duration,
                    "planificada": stop.planificada,
                    "microparada": stop.microparada,
                },
            )
            self._emit_event(
                system="iot",
                tipo="transicion_estado",
                maquina=maquina,
                when=stop_end,
                estado="RUNNING",
                payload={"transicion": "RUNNING", "motivo": "fin de parada"},
            )
            if stop.maintenance is not None:
                self._emit_event(
                    system="cmms",
                    tipo="mantenimiento",
                    maquina=maquina,
                    when=stop.maintenance["inicio"],
                    payload={
                        "codigo_orden_trabajo": stop.maintenance["codigo"],
                        "tipo": stop.maintenance["tipo"],
                        "duracion_min": stop.maintenance["duracion_min"],
                    },
                )

        self._emit_event(
            system="iot",
            tipo="transicion_estado",
            maquina=maquina,
            when=shift_end,
            estado="IDLE",
            payload={"transicion": "IDLE", "motivo": "fin de turno"},
        )
        self._emit_event(
            system="calidad",
            tipo="inspeccion",
            maquina=maquina,
            when=inspection_at,
            payload={
                "codigo_inspeccion": codigo_inspeccion,
                "codigo_lote": codigo_lote,
                "unidades_inspeccionadas": total_count,
                "unidades_buenas": good_count,
            },
        )

        # --- Lecturas de proceso (temperatura y energía) -------------------
        base_temp = (
            60
            + TEMP_OFFSET.get(maquina.tipo, 4.0)
            + (4.0 if turno.codigo == "C" else 2.0 if turno.codigo == "B" else 0.0)
            + 14 * degradation
        )
        thermal_probability = (0.005 + 0.05 * degradation) * self.params.intensidad
        thermal = self.rng.random() < thermal_probability
        offsets = [300, 315, 330, 345, 360] if thermal else [90, 300]
        energy_share = energy / len(offsets) if offsets else 0.0
        for offset in offsets:
            if thermal:
                temp = self.rng.uniform(87.0, 96.0)
            else:
                temp = base_temp + self.rng.uniform(-2.5, 2.5)
            temp = max(20.0, min(120.0, temp))
            self._emit_event(
                system="scada",
                tipo="lectura_proceso",
                maquina=maquina,
                when=shift_start + timedelta(minutes=offset),
                temperatura=temp,
                energia=energy_share,
                payload={
                    "temperatura_c": round(temp, 2),
                    "energia_kwh": round(energy_share, 4),
                    "excursion_termica": thermal,
                },
            )

    # -------------------------------------------------------------- helpers
    def _choose_product(self, maquina: Maquina) -> tuple[Producto, bool]:
        familia = self.familia_por_linea[maquina.id_linea]
        productos = self.cat.productos_de_familia(familia.id_familia)
        actual_id = self.producto_actual.get(maquina.id_maquina)

        if actual_id is None:
            producto = self.rng.choice(productos)
            self.producto_actual[maquina.id_maquina] = producto.id_producto
            self.turnos_restantes[maquina.id_maquina] = self.rng.randint(8, 24)
            return producto, False

        if self.turnos_restantes.get(maquina.id_maquina, 0) <= 0:
            alternatives = [p for p in productos if p.id_producto != actual_id]
            producto = self.rng.choice(alternatives) if alternatives else productos[0]
            self.producto_actual[maquina.id_maquina] = producto.id_producto
            self.turnos_restantes[maquina.id_maquina] = self.rng.randint(8, 24)
            return producto, True

        self.turnos_restantes[maquina.id_maquina] -= 1
        producto = next(
            p for p in productos if p.id_producto == actual_id
        )
        return producto, False

    def _place(
        self,
        intervals: list[tuple[int, int]],
        duration: int,
        low: int,
        high: int,
    ) -> int | None:
        low = max(0, low)
        high = min(SHIFT_MIN, high)
        if duration <= 0 or high - low < duration:
            return None
        for _ in range(300):
            start = self.rng.randint(low, high - duration)
            end = start + duration
            if all(end <= a or start >= b for a, b in intervals):
                intervals.append((start, end))
                intervals.sort()
                return start
        return None

    def _poisson(self, lam: float) -> int:
        """Muestreo de Poisson por transformada inversa (Knuth)."""
        if lam <= 0:
            return 0
        limit = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= self.rng.random()
            if p <= limit:
                return k - 1

    def _failure_cause(self) -> Causa:
        codes = [code for code, _ in FAILURE_CAUSES]
        weights = [weight for _, weight in FAILURE_CAUSES]
        code = self.rng.choices(codes, weights=weights, k=1)[0]
        return self.causas[code]

    def _new_maintenance(
        self,
        maquina: Maquina,
        turno: Turno,
        id_tiempo: int,
        inicio: datetime,
        duration: int,
        causa: Causa,
        tipo: str,
    ) -> dict[str, Any]:
        specialty = SPECIALTY_BY_CAUSE.get(causa.codigo)
        candidates = self.tecnicos_por_especialidad.get(specialty or "", [])
        if not candidates:
            candidates = list(self.cat.tecnicos)
        tecnico = self.rng.choice(candidates)

        self.maintenance_seq += 1
        cost = 120.0 + duration * 12.0 + self.rng.uniform(0.0, 320.0)
        return {
            "codigo": f"OT-{self.run_tag}-{self.maintenance_seq:06d}",
            "id_tecnico": tecnico.id_tecnico,
            "id_causa": causa.id_causa,
            "tipo": tipo,
            "inicio": inicio,
            "fin": inicio + timedelta(minutes=duration),
            "duracion_min": duration,
            "costo": cost,
        }

    def _emit_event(
        self,
        system: str,
        tipo: str,
        maquina: Maquina,
        when: datetime,
        estado: str | None = None,
        temperatura: float | None = None,
        energia: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.event_seq += 1
        self.tables["fact_evento"].write(
            [
                system,
                f"{self.run_tag}-{self.event_seq:08d}",
                tipo,
                maquina.id_maquina,
                _fmt_dt(when),
                _fmt_dt(when),
                self.run_id,
                estado,
                _fmt_dec(temperatura, 2) if temperatura is not None else None,
                _fmt_dec(energia, 4) if energia is not None else None,
                _fmt_json(payload or {}),
            ]
        )

    def _accumulate_day(
        self,
        fecha: date,
        planned: int,
        runtime: int,
        ideal_min: float,
        total_count: int,
        good_count: int,
    ) -> None:
        totals = self.daily.setdefault(fecha, DayTotals())
        totals.planned += planned
        totals.runtime += runtime
        totals.ideal_min += ideal_min
        totals.total_count += total_count
        totals.good_count += good_count

    @staticmethod
    def _cycle_seconds(producto: Producto) -> float:
        """Ciclo ideal estable por producto (segundos)."""
        return float(30 + ((producto.id_producto - 1) % 6) * 5)
