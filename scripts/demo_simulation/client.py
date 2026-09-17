"""Cliente HTTP delgado hacia el backend real (spec `alerting-ui`). Cada
función hace exactamente una llamada; no reintenta ni interpreta un
timeout como cancelación (diseño, sección 5) — eso queda a cargo de
quien llama (`scripts.demo_simulation.worker`), que decide si bloquear
la sesión.
"""

from __future__ import annotations

from typing import Any

import requests

DEFAULT_TIMEOUT_SECONDS = 30


class DemoBackendError(RuntimeError):
    """El backend respondió, pero con un error explícito (4xx/5xx). No
    implica que el efecto no haya ocurrido — quien llama decide.
    """

    def __init__(self, message: str, status_code: int, detail: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class DemoBackendUncertain(RuntimeError):
    """No se pudo determinar si el request llegó a aplicarse (timeout,
    error de conexión). Nunca debe interpretarse como "no se aplicó".
    """


def _request(method: str, url: str, *, timeout: int, **kwargs) -> requests.Response:
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
    except requests.exceptions.Timeout as error:
        raise DemoBackendUncertain(
            f"Timeout esperando respuesta de {method} {url}; no se puede asumir que el "
            "request no se aplicó."
        ) from error
    except requests.exceptions.ConnectionError as error:
        raise DemoBackendUncertain(
            f"Error de conexión en {method} {url}; no se puede asumir que el request no "
            "se aplicó."
        ) from error
    return response


def get_active_contract(
    backend_url: str, sensor_id: str, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> dict[str, Any]:
    """`GET /models/{sensor_id}/active`. Válido incluso antes de que el
    sensor tenga datos: solo se usa para leer el contrato operativo
    vigente (p. ej. `horizon_days`), nunca modelo o historial del sensor.
    """
    response = _request("GET", f"{backend_url}/models/{sensor_id}/active", timeout=timeout)
    if response.status_code != 200:
        raise DemoBackendError(
            f"No se pudo obtener el contrato operativo (status {response.status_code}).",
            response.status_code,
            _safe_json(response),
        )
    return response.json()


def post_reading(
    backend_url: str,
    sensor_id: str,
    payload: dict[str, Any],
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """`POST /sensors/{sensor_id}/readings`."""
    response = _request(
        "POST", f"{backend_url}/sensors/{sensor_id}/readings", json=payload, timeout=timeout
    )
    if response.status_code != 200:
        raise DemoBackendError(
            f"La ingesta falló (status {response.status_code}).",
            response.status_code,
            _safe_json(response),
        )
    return response.json()


def get_quality(
    backend_url: str, sensor_id: str, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> dict[str, Any] | None:
    """`GET /quality/{sensor_id}`. Devuelve `None` si el backend todavía
    no tiene dataset para `sensor_id` (404), sin tratarlo como error.
    """
    response = _request("GET", f"{backend_url}/quality/{sensor_id}", timeout=timeout)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise DemoBackendError(
            f"No se pudo consultar la calidad del dataset (status {response.status_code}).",
            response.status_code,
            _safe_json(response),
        )
    return response.json()


def run_forecast(
    backend_url: str, sensor_id: str, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> dict[str, Any]:
    """`POST /forecast/{sensor_id}/run`. Un 422 (sin historial
    entrenable) se propaga como `DemoBackendError`: nunca se fabrica un
    veredicto local.
    """
    response = _request("POST", f"{backend_url}/forecast/{sensor_id}/run", timeout=timeout)
    if response.status_code != 200:
        raise DemoBackendError(
            f"El pronóstico falló (status {response.status_code}).",
            response.status_code,
            _safe_json(response),
        )
    return response.json()


def get_feedback(
    backend_url: str, sensor_id: str, timeout: int = DEFAULT_TIMEOUT_SECONDS
) -> dict[str, Any] | None:
    """`GET /feedback/{sensor_id}`. Devuelve `None` si todavía no corrió
    ningún pronóstico (404), sin tratarlo como error.
    """
    response = _request("GET", f"{backend_url}/feedback/{sensor_id}", timeout=timeout)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise DemoBackendError(
            f"No se pudo consultar el registro de pronósticos (status {response.status_code}).",
            response.status_code,
            _safe_json(response),
        )
    return response.json()


def _safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text
