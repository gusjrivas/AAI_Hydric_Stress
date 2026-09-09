from __future__ import annotations

from experiment_runner.controlled_daily_v4.provenance import (
    EXPECTED_ERA5_FILENAME,
    EXPECTED_NASA_POWER_FILENAME,
    compute_sha256,
    validate_pergamino_provenance,
)
from tests.controlled_daily_v4_fixtures import (
    make_synthetic_daily_frame,
    write_synthetic_era5_csv,
    write_synthetic_nasa_power_csv,
    write_synthetic_pergamino_csv_pair,
)


def test_provenance_ok_on_well_formed_synthetic_pair(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=1)
    report = validate_pergamino_provenance(era5, nasa)
    assert report.ok, report.issues
    assert report.n_dates_only_era5 == 0
    assert report.n_dates_only_nasa_power == 0
    assert report.era5_sha256 == compute_sha256(era5)
    assert report.nasa_power_sha256 == compute_sha256(nasa)


def test_provenance_detects_missing_files(tmp_path):
    report = validate_pergamino_provenance(
        tmp_path / "no_existe_era5.csv", tmp_path / "no_existe_nasa.csv"
    )
    assert not report.ok
    assert any("no encontrado" in issue for issue in report.issues)


def test_provenance_detects_unexpected_filename(tmp_path):
    daily = make_synthetic_daily_frame(n_days=20, seed=2)
    era5_path = tmp_path / "otro_nombre.csv"
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)
    report = validate_pergamino_provenance(era5_path, nasa_path)
    assert any("nombre inesperado" in issue for issue in report.issues)


def test_provenance_detects_sha256_mismatch(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=20, seed=3)
    report = validate_pergamino_provenance(
        era5, nasa, expected_era5_sha256="0" * 64, expected_nasa_power_sha256=None
    )
    assert not report.ok
    assert any("SHA-256 no coincide" in issue for issue in report.issues)


def test_provenance_detects_duplicated_era5_timestamps(tmp_path):
    daily = make_synthetic_daily_frame(n_days=10, seed=4)
    era5_path = tmp_path / EXPECTED_ERA5_FILENAME
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)

    # Duplica manualmente la última línea de datos (mismo timestamp dos veces).
    content = era5_path.read_text(encoding="utf-8").splitlines()
    content.append(content[-1])
    era5_path.write_text("\n".join(content) + "\n", encoding="utf-8")

    report = validate_pergamino_provenance(era5_path, nasa_path)
    assert report.era5_n_duplicated_timestamps == 1
    assert any("timestamps duplicados" in issue for issue in report.issues)


def test_provenance_reports_declared_date_range_mismatch(tmp_path):
    daily = make_synthetic_daily_frame(n_days=20, seed=5)
    era5_path = tmp_path / EXPECTED_ERA5_FILENAME
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)

    content = nasa_path.read_bytes().decode("ascii")
    corrupted = content.replace(f"through {daily.index.max():%m/%d/%Y}", "through 12/31/2099")
    nasa_path.write_bytes(corrupted.encode("ascii"))

    report = validate_pergamino_provenance(era5_path, nasa_path)
    assert report.nasa_power_declared_date_max == "2099-12-31"
    assert any("rango declarado termina" in issue for issue in report.issues)
