"""Reglas de calidad de eventos IoT (Constitución §7.1).

El módulo concentra las decisiones que separan un evento válido de uno que debe
quedar en cuarentena o marcarse como tardío/reordenado:

- rango válido de ``event_time``: ``[inicio_histórico − 1 día, ahora + 5 min]``;
- ventana de reordenamiento de 5 minutos: un evento que llega después se acepta
  pero se marca ``tardio``;
- evento reordenado: su ``event_time`` es anterior al último evento conocido de
  la misma máquina.

Los eventos fuera de rango **no se descartan en silencio**: se escriben en
``fact_evento_rechazado`` con el motivo y el payload original.

No se inventan lecturas: cuando falta una muestra, la vista
``v_calidad_senal_iot`` marca el hueco como ``unknown`` en lugar de aplicar un
*carry-forward* que fabricaría datos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

# Rango de aceptación de la Constitución §7.1.
RANGO_PASADO = timedelta(days=1)
RANGO_FUTURO = timedelta(minutes=5)

# Ventana de reordenamiento (minutos).
VENTANA_REORDENAMIENTO = timedelta(minutes=5)

# Motivos de rechazo estables (se documentan en DATA_DICTIONARY.md).
MOTIVO_EVENT_TIME_NULO = "event_time_nulo"
MOTIVO_TIMESTAMP_FUTURO = "timestamp_futuro"
MOTIVO_TIMESTAMP_ANTERIOR = "timestamp_anterior_al_rango"


@dataclass(frozen=True)
class EventQuality:
    """Decisión de calidad para un evento de origen."""

    accepted: bool
    tardio: bool = False
    reordenado: bool = False
    motivo: str | None = None

    @property
    def rejected(self) -> bool:
        return not self.accepted


def classify_event(
    event_time: datetime | None,
    ingested_at: datetime,
    *,
    historical_start: datetime | None = None,
    last_event_time: datetime | None = None,
) -> EventQuality:
    """Clasifica un evento según las reglas de la Constitución §7.1.

    ``historical_start`` es el ``event_time`` mínimo del histórico. Si es
    ``None`` solo se aplica el límite futuro. ``last_event_time`` es el último
    evento conocido de esa máquina y permite marcar el desorden.
    """
    if event_time is None:
        return EventQuality(accepted=False, motivo=MOTIVO_EVENT_TIME_NULO)

    event_time = _as_utc(event_time)
    ingested_at = _as_utc(ingested_at)

    if event_time > ingested_at + RANGO_FUTURO:
        return EventQuality(accepted=False, motivo=MOTIVO_TIMESTAMP_FUTURO)

    if historical_start is not None:
        inicio = _as_utc(historical_start)
        if event_time < inicio - RANGO_PASADO:
            return EventQuality(accepted=False, motivo=MOTIVO_TIMESTAMP_ANTERIOR)

    tardio = (ingested_at - event_time) > VENTANA_REORDENAMIENTO
    reordenado = last_event_time is not None and event_time < _as_utc(
        last_event_time
    )

    return EventQuality(accepted=True, tardio=tardio, reordenado=reordenado)


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def quality_payload(quality: EventQuality) -> dict:
    """Metadatos de calidad que se añaden al ``payload`` del evento aceptado."""
    return {
        "tardio": quality.tardio,
        "reordenado": quality.reordenado,
        "ventana_reordenamiento_min": int(
            VENTANA_REORDENAMIENTO.total_seconds() // 60
        ),
    }
