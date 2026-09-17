"""Configuración y validación de una sesión de demostración acelerada
(diseño en `openspec/changes/add-accelerated-sensor-demo/design.md`,
sección 2). Valida fechas, historial y semilla antes de que `prepare`
escriba ningún recurso; no decide por sí sola si el sensor colisiona
con uno existente (ver `scripts.demo_simulation.prepare`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

DEMO_SENSOR_PREFIX = "demo-"
MIN_INTERVAL_SECONDS = 1
MAX_INTERVAL_SECONDS = 60
DEFAULT_INTERVAL_SECONDS = 5


class DemoConfigError(ValueError):
    """Configuración de sesión inválida. `prepare` no debe continuar."""


@dataclass(frozen=True)
class DemoSessionConfig:
    """Parámetros congelados de una sesión (diseño, sección 2). El
    identificador se resuelve aparte (`prepare.generate_session_id`),
    porque no es un parámetro elegido por quien prepara la demo sino
    generado por la herramienta para garantizar exclusividad.
    """

    start_date: date
    days: int
    history_days: int
    seed: int
    backend_url: str
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS
    sensor_id: str | None = None

    @property
    def history_start(self) -> date:
        return self.start_date - timedelta(days=self.history_days)

    @property
    def history_end(self) -> date:
        return self.start_date - timedelta(days=1)

    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.days - 1)


def validate_config(config: DemoSessionConfig, *, today: date, horizon_days: int) -> None:
    """Levanta `DemoConfigError` si `config` es inválida; no escribe
    ningún recurso ni consulta el backend (el horizonte ya debe haberse
    obtenido antes, vía `GET /models/{sensor_id}/active`).
    """
    if not config.sensor_id.startswith(DEMO_SENSOR_PREFIX):
        raise DemoConfigError(
            f"El sensor de demo debe tener el prefijo '{DEMO_SENSOR_PREFIX}' "
            f"(recibido: '{config.sensor_id}')."
        )
    if config.days < 1:
        raise DemoConfigError("La cantidad de días a reproducir debe ser al menos 1.")
    if config.history_days < 1:
        raise DemoConfigError("El historial inicial debe tener al menos 1 día.")
    if config.seed < 0:
        raise DemoConfigError("La semilla debe ser un entero no negativo.")
    if not MIN_INTERVAL_SECONDS <= config.interval_seconds <= MAX_INTERVAL_SECONDS:
        raise DemoConfigError(
            f"El intervalo entre pasos debe estar entre {MIN_INTERVAL_SECONDS} y "
            f"{MAX_INTERVAL_SECONDS} segundos."
        )
    if not isinstance(horizon_days, int) or horizon_days < 1:
        raise DemoConfigError("El horizonte de pronóstico del contrato operativo es inválido.")
    if config.start_date >= today:
        raise DemoConfigError(
            "La fecha de inicio de la reproducción debe ser pasada respecto de hoy (UTC)."
        )
    if config.end_date + timedelta(days=horizon_days) >= today:
        raise DemoConfigError(
            "El período completo, incluido el horizonte de pronóstico "
            f"({horizon_days} días), debe terminar antes de hoy (UTC). "
            "Que la fecha objetivo sea pasada no garantiza que el día ya esté en el dataset."
        )
