"""Validación del manejo de calidad de eventos IoT (G5 / Constitución §7.1).

Comprueba dos capas:

1. La función pura ``classify_event`` con casos fijos.
2. El camino real de ingesta: un lote con un evento válido, uno futuro y uno
   anterior al rango; después un evento tardío que debe quedar marcado como
   reordenado. Verifica ``fact_evento_rechazado`` y ``v_calidad_senal_iot``.

Los eventos de prueba llevan ``source_event_id`` con prefijo ``test-iot-`` y se
eliminan al final, de modo que la base queda igual que antes.

Uso:
    docker compose --profile tools run --rm ingestor python src/validate_iot.py
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone

from common.db import connect
from event_quality import (
    MOTIVO_EVENT_TIME_NULO,
    MOTIVO_TIMESTAMP_ANTERIOR,
    MOTIVO_TIMESTAMP_FUTURO,
    classify_event,
)
from ingest import EventRecord, Ingestor

UTC = timezone.utc


class Checks:
    def __init__(self) -> None:
        self.items: list[tuple[str, bool, str]] = []

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.items.append((name, ok, detail))

    def report(self) -> int:
        print("Validación de calidad IoT (G5)")
        print("=" * 72)
        for name, ok, detail in self.items:
            print(f"[{'OK' if ok else 'FALLA'}] {name}")
            if detail:
                print(f"       {detail}")
        failed = [item for item in self.items if not item[1]]
        print()
        print(f"Resultado: {len(self.items) - len(failed)}/{len(self.items)} comprobaciones OK")
        return 0 if not failed else 1


def validate_pure(checks: Checks) -> None:
    now = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
    historico = datetime(2026, 4, 22, 0, 0, tzinfo=UTC)

    checks.add(
        "event_time nulo se rechaza",
        classify_event(None, now).motivo == MOTIVO_EVENT_TIME_NULO,
    )
    checks.add(
        "timestamp futuro se rechaza",
        classify_event(now + timedelta(hours=1), now).motivo
        == MOTIVO_TIMESTAMP_FUTURO,
    )
    checks.add(
        "timestamp anterior al histórico se rechaza",
        classify_event(
            historico - timedelta(days=2), now, historical_start=historico
        ).motivo
        == MOTIVO_TIMESTAMP_ANTERIOR,
    )
    normal = classify_event(
        now - timedelta(minutes=1), now, historical_start=historico
    )
    checks.add(
        "evento normal se acepta sin marcas",
        normal.accepted and not normal.tardio and not normal.reordenado,
    )
    tardio = classify_event(
        now - timedelta(minutes=10),
        now,
        historical_start=historico,
        last_event_time=now - timedelta(minutes=1),
    )
    checks.add(
        "evento tardío se acepta y se marca tardío/reordenado",
        tardio.accepted and tardio.tardio and tardio.reordenado,
    )


def validate_ingest(checks: Checks) -> None:
    run_id = f"test-iot-{uuid.uuid4().hex[:8]}"
    prefix = f"test-iot-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).replace(microsecond=0)
    clean_ok = False

    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id_maquina FROM dim_maquina ORDER BY id_maquina LIMIT 1")
            id_maquina = int(cur.fetchone()[0])

        ingestor = Ingestor(run_id=run_id, max_attempts=2, base_delay=0.2)
        try:
            def event(kind: str, when: datetime) -> EventRecord:
                return EventRecord(
                    source_system="iot",
                    source_event_id=f"{prefix}-{kind}",
                    tipo_evento="transicion_estado",
                    id_maquina=id_maquina,
                    event_time=when,
                    generated_at=now,
                    estado="RUNNING",
                    payload={"origen": "validacion_iot"},
                )

            first = ingestor.ingest(
                [
                    event("normal", now - timedelta(minutes=1)),
                    event("futuro", now + timedelta(hours=1)),
                    event("antiguo", now - timedelta(days=400)),
                ]
            )
            checks.add(
                "lote con futuro y antiguo deja 2 rechazos",
                first.events_rejected == 2
                and set(first.rejection_reasons)
                == {MOTIVO_TIMESTAMP_FUTURO, MOTIVO_TIMESTAMP_ANTERIOR},
                f"rechazados={first.events_rejected} motivos={first.rejection_reasons}",
            )

            second = ingestor.ingest([event("tardio", now - timedelta(minutes=10))])
            checks.add(
                "evento tardío se inserta (no se rechaza)",
                second.events_inserted == 1 and second.events_rejected == 0,
                f"insertados={second.events_inserted}",
            )

            rows = ingestor.query(
                "SELECT source_event_id, motivo FROM fact_evento_rechazado "
                "WHERE source_event_id LIKE %s ORDER BY source_event_id",
                (f"{prefix}%",),
            )
            motivos = {row[0].rsplit("-", 1)[-1]: row[1] for row in rows}
            checks.add(
                "cuarentena conserva motivo y payload",
                motivos.get("futuro") == MOTIVO_TIMESTAMP_FUTURO
                and motivos.get("antiguo") == MOTIVO_TIMESTAMP_ANTERIOR,
                f"filas={motivos}",
            )

            flags = ingestor.query(
                "SELECT payload->'calidad'->>'tardio', "
                "       payload->'calidad'->>'reordenado' "
                "FROM fact_evento WHERE source_event_id = %s",
                (f"{prefix}-tardio",),
            )
            checks.add(
                "payload del evento tardío marca tardio/reordenado",
                bool(flags) and flags[0] == ("true", "true"),
                f"flags={flags}",
            )

            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM v_calidad_senal_iot")
                total = int(cur.fetchone()[0])
                cur.execute(
                    "SELECT count(*) FROM v_calidad_senal_iot "
                    "WHERE estado_senal NOT IN ('ok', 'unknown', 'sin_datos') "
                    "   OR lecturas < 0 OR lecturas_esperadas < 0"
                )
                invalidos = int(cur.fetchone()[0])
            checks.add(
                "v_calidad_senal_iot devuelve filas y estados válidos",
                total > 0 and invalidos == 0,
                f"filas={total} inválidas={invalidos}",
            )
        finally:
            ingestor.close()
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM fact_evento_rechazado "
                    "WHERE source_event_id LIKE %s",
                    (f"{prefix}%",),
                )
                cur.execute(
                    "DELETE FROM fact_evento WHERE source_event_id LIKE %s",
                    (f"{prefix}%",),
                )
            conn.commit()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM fact_evento WHERE source_event_id LIKE %s",
                    (f"{prefix}%",),
                )
                clean_ok = int(cur.fetchone()[0]) == 0

    checks.add("los datos de prueba se limpian", clean_ok)


def main() -> int:
    checks = Checks()
    validate_pure(checks)
    validate_ingest(checks)
    return checks.report()


if __name__ == "__main__":
    sys.exit(main())
