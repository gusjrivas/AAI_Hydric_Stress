from datetime import date

import numpy as np
import pandas as pd
import requests
import xarray as xr

from data_ingestion.sources.esa_cci_soil_moisture import fetch_esa_cci_soil_moisture


def _make_netcdf_bytes(tmp_path, day: date, sm_value: float) -> bytes:
    ds = xr.Dataset(
        {"sm": (("time", "lat", "lon"), np.array([[[sm_value]]], dtype="float32"))},
        coords={
            "time": [np.datetime64(day.isoformat())],
            "lat": np.array([-34.92], dtype="float32"),
            "lon": np.array([-57.95], dtype="float32"),
        },
    )
    path = tmp_path / f"{day.isoformat()}.nc"
    ds.to_netcdf(path)
    return path.read_bytes()


class _FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    """Simula requests sin descargar archivos NetCDF reales por red."""

    def __init__(self, content_by_date: dict[date, bytes]):
        self._content_by_date = content_by_date
        self.status_for_missing = 404

    def get(self, url: str, timeout: int):
        for day, content in self._content_by_date.items():
            if day.strftime("%Y%m%d") in url:
                return _FakeResponse(content)
        return _FakeResponse(b"", status_code=self.status_for_missing)


def test_fetch_esa_cci_extracts_nearest_pixel_and_marks_provenance_real(tmp_path):
    day1 = date(2024, 1, 1)
    day2 = date(2024, 1, 2)
    session = _FakeSession(
        {
            day1: _make_netcdf_bytes(tmp_path, day1, 0.25),
            day2: _make_netcdf_bytes(tmp_path, day2, 0.31),
        }
    )

    df = fetch_esa_cci_soil_moisture(
        latitude=-34.92,
        longitude=-57.95,
        start=day1,
        end=day2,
        session=session,
        retry_delay=0,
    )

    assert list(df["soil_moisture"].round(2)) == [0.25, 0.31]
    assert (df["origen"] == "real").all()


def test_fetch_esa_cci_marks_missing_day_as_na(tmp_path):
    day1 = date(2024, 1, 1)
    day2 = date(2024, 1, 2)
    session = _FakeSession({day1: _make_netcdf_bytes(tmp_path, day1, 0.25)})

    df = fetch_esa_cci_soil_moisture(
        latitude=-34.92,
        longitude=-57.95,
        start=day1,
        end=day2,
        session=session,
        retry_delay=0,
    )

    missing_day_value = df.loc[df["timestamp"] == "2024-01-02", "soil_moisture"].iloc[0]
    assert pd.isna(missing_day_value)


def test_fetch_esa_cci_marks_connection_error_day_as_na_without_aborting(tmp_path):
    """Un error de conexión transitorio (no un status HTTP, una excepción de
    requests) tampoco debe abortar la serie: ver falla real observada en
    una segunda corrida de la ingesta de 2024 (RemoteDisconnected)."""

    class _FlakySession(_FakeSession):
        def get(self, url: str, timeout: int):
            if "20240102" in url:
                raise requests.exceptions.ConnectionError("conexión reiniciada por el servidor")
            return super().get(url, timeout=timeout)

    day1 = date(2024, 1, 1)
    day2 = date(2024, 1, 2)
    session = _FlakySession({day1: _make_netcdf_bytes(tmp_path, day1, 0.25)})

    df = fetch_esa_cci_soil_moisture(
        latitude=-34.92,
        longitude=-57.95,
        start=day1,
        end=day2,
        session=session,
        retry_delay=0,
    )

    first_day_value = df.loc[df["timestamp"] == "2024-01-01", "soil_moisture"].iloc[0]
    assert round(first_day_value, 2) == 0.25
    connection_error_day_value = df.loc[df["timestamp"] == "2024-01-02", "soil_moisture"].iloc[0]
    assert pd.isna(connection_error_day_value)


def test_fetch_esa_cci_marks_server_error_day_as_na_without_aborting(tmp_path):
    """Un 500 transitorio en un día puntual no debe abortar toda la serie:
    ver falla real observada en la ingesta de 2024 (día 2024-04-18)."""
    day1 = date(2024, 1, 1)
    day2 = date(2024, 1, 2)
    session = _FakeSession({day1: _make_netcdf_bytes(tmp_path, day1, 0.25)})
    session.status_for_missing = 500

    df = fetch_esa_cci_soil_moisture(
        latitude=-34.92,
        longitude=-57.95,
        start=day1,
        end=day2,
        session=session,
        retry_delay=0,
    )

    first_day_value = df.loc[df["timestamp"] == "2024-01-01", "soil_moisture"].iloc[0]
    assert round(first_day_value, 2) == 0.25
    server_error_day_value = df.loc[df["timestamp"] == "2024-01-02", "soil_moisture"].iloc[0]
    assert pd.isna(server_error_day_value)
