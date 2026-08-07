from datetime import date

import pandas as pd

from data_ingestion.sources.nasa_power import fetch_nasa_power


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _FakeSession:
    """Simula requests.Session sin realizar llamadas de red reales."""

    def __init__(self, payload: dict):
        self._payload = payload
        self.last_request_params: dict | None = None

    def get(self, url: str, params: dict, timeout: int):
        self.last_request_params = params
        return _FakeResponse(self._payload)


def _sample_payload() -> dict:
    return {
        "properties": {
            "parameter": {
                "T2M": {"20260101": 20.5, "20260102": 21.0},
                "RH2M": {"20260101": 60.0, "20260102": 58.0},
                "PRECTOTCORR": {"20260101": 0.0, "20260102": -999.0},
                "ALLSKY_SFC_SW_DWN": {"20260101": 18.2, "20260102": 19.1},
                "WS2M": {"20260101": 3.1, "20260102": 2.8},
            }
        }
    }


def test_fetch_nasa_power_maps_parameters_and_marks_provenance_real():
    session = _FakeSession(_sample_payload())

    df = fetch_nasa_power(
        latitude=-34.6,
        longitude=-58.4,
        start=date(2026, 1, 1),
        end=date(2026, 1, 2),
        session=session,
    )

    assert list(df["temperature"]) == [20.5, 21.0]
    assert (df["origen"] == "real").all()
    assert session.last_request_params["community"] == "AG"


def test_fetch_nasa_power_replaces_fill_value_with_na():
    session = _FakeSession(_sample_payload())

    df = fetch_nasa_power(
        latitude=-34.6,
        longitude=-58.4,
        start=date(2026, 1, 1),
        end=date(2026, 1, 2),
        session=session,
    )

    second_day_precipitation = df.loc[df["timestamp"] == "2026-01-02", "precipitation"].iloc[0]
    assert pd.isna(second_day_precipitation)
