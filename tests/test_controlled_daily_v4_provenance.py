from __future__ import annotations

from experiment_runner.controlled_daily_v4.config import INPUT_MODE_SCIENTIFIC, INPUT_MODE_SYNTHETIC
from experiment_runner.controlled_daily_v4.provenance import (
    EXPECTED_ERA5_FILENAME,
    EXPECTED_NASA_POWER_FILENAME,
    compute_sha256,
    validate_pergamino_provenance,
)
from tests.controlled_daily_v4_fixtures import (
    drop_nasa_power_column,
    make_synthetic_daily_frame,
    write_manifest_reference_fixture,
    write_synthetic_era5_csv,
    write_synthetic_nasa_power_csv,
    write_synthetic_pergamino_csv_pair,
)


def test_provenance_ok_in_synthetic_mode_on_well_formed_synthetic_pair(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=60, seed=1)
    report = validate_pergamino_provenance(era5, nasa, mode=INPUT_MODE_SYNTHETIC)
    assert report.ok, report.issues
    assert not report.scientific, "el modo sintético nunca puede quedar marcado como científico"
    assert report.n_dates_only_era5 == 0
    assert report.n_dates_only_nasa_power == 0
    assert report.era5_sha256 == compute_sha256(era5)
    assert report.nasa_power_sha256 == compute_sha256(nasa)


def test_provenance_detects_missing_files(tmp_path):
    report = validate_pergamino_provenance(
        tmp_path / "no_existe_era5.csv", tmp_path / "no_existe_nasa.csv", mode=INPUT_MODE_SYNTHETIC
    )
    assert not report.ok
    assert any("no encontrado" in issue for issue in report.issues)


def test_provenance_detects_unexpected_filename(tmp_path):
    daily = make_synthetic_daily_frame(n_days=20, seed=2)
    era5_path = tmp_path / "otro_nombre.csv"
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)
    report = validate_pergamino_provenance(era5_path, nasa_path, mode=INPUT_MODE_SYNTHETIC)
    assert any("nombre inesperado" in issue for issue in report.issues)


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

    report = validate_pergamino_provenance(era5_path, nasa_path, mode=INPUT_MODE_SYNTHETIC)
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

    report = validate_pergamino_provenance(era5_path, nasa_path, mode=INPUT_MODE_SYNTHETIC)
    assert report.nasa_power_declared_date_max == "2099-12-31"
    assert any("rango declarado termina" in issue for issue in report.issues)


def test_provenance_detects_incompatible_era5_metadata_header(tmp_path):
    """Encabezado ERA5 con un campo de metadatos faltante: error controlado,
    no una excepción sin manejar (hallazgo H-01)."""
    daily = make_synthetic_daily_frame(n_days=10, seed=6)
    era5_path = tmp_path / EXPECTED_ERA5_FILENAME
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)

    lines = era5_path.read_text(encoding="utf-8").splitlines()
    lines[0] = "latitude,longitude,elevation,utc_offset_seconds"  # falta timezone*
    era5_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = validate_pergamino_provenance(era5_path, nasa_path, mode=INPUT_MODE_SYNTHETIC)
    assert not report.ok
    assert any("metadatos de encabezado ausentes o inválidos" in issue for issue in report.issues)


def test_provenance_detects_incompatible_nasa_header(tmp_path):
    daily = make_synthetic_daily_frame(n_days=10, seed=7)
    era5_path = tmp_path / EXPECTED_ERA5_FILENAME
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)

    content = nasa_path.read_bytes().decode("ascii")
    corrupted = content.replace("-END HEADER-", "")
    nasa_path.write_bytes(corrupted.encode("ascii"))

    report = validate_pergamino_provenance(era5_path, nasa_path, mode=INPUT_MODE_SYNTHETIC)
    assert not report.ok
    assert any("encabezado o columnas inválidos" in issue for issue in report.issues)


def test_provenance_detects_missing_required_nasa_column_as_a_controlled_error(tmp_path):
    """H-03/columnas: la ausencia de una columna requerida (RH2M) debe
    reportarse como un `issue` controlado -- nunca un `KeyError` sin manejar
    propagado desde `load_nasa_power_daily_raw`."""
    daily = make_synthetic_daily_frame(n_days=10, seed=14)
    era5_path = tmp_path / EXPECTED_ERA5_FILENAME
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)

    drop_nasa_power_column(nasa_path, "RH2M")

    report = validate_pergamino_provenance(era5_path, nasa_path, mode=INPUT_MODE_SYNTHETIC)
    assert not report.ok
    assert any(
        "encabezado o columnas inválidos" in issue and "RH2M" in issue for issue in report.issues
    )


def _write_manifest_matching_pair(tmp_path, era5_path, nasa_path):
    manifest_path = tmp_path / "manifest.yaml"
    write_manifest_reference_fixture(
        manifest_path,
        era5_sha256=compute_sha256(era5_path),
        nasa_sha256=compute_sha256(nasa_path),
    )
    return manifest_path


def test_scientific_mode_passes_when_identity_matches_the_manifest_reference(tmp_path):
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=20, seed=8)
    manifest_path = _write_manifest_matching_pair(tmp_path, era5, nasa)

    report = validate_pergamino_provenance(
        era5, nasa, mode=INPUT_MODE_SCIENTIFIC, manifest_path=manifest_path
    )
    assert report.ok, report.issues
    assert report.scientific


def test_scientific_mode_never_computes_the_hash_reference_from_the_received_files(tmp_path):
    """El hash esperado no puede derivarse de los mismos archivos recibidos:
    si el manifiesto trae un hash distinto, la corrida científica rechaza
    aunque el par de archivos sea internamente consistente (hallazgo H-01)."""
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=20, seed=9)
    manifest_path = tmp_path / "manifest.yaml"
    write_manifest_reference_fixture(
        manifest_path, era5_sha256="0" * 64, nasa_sha256=compute_sha256(nasa)
    )

    report = validate_pergamino_provenance(
        era5, nasa, mode=INPUT_MODE_SCIENTIFIC, manifest_path=manifest_path
    )
    assert not report.ok
    assert not report.scientific
    assert any("SHA-256 no coincide con el manifiesto" in issue for issue in report.issues)


def test_scientific_mode_rejects_era5_coordinates_that_do_not_match_its_own_reference(tmp_path):
    daily = make_synthetic_daily_frame(n_days=10, seed=10)
    era5_path = tmp_path / EXPECTED_ERA5_FILENAME
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)

    # Adversarial: coordenadas de ERA5-Land pisadas por (0, 0).
    content = era5_path.read_text(encoding="utf-8").splitlines()
    content[1] = "0.0,0.0,70.0,-10800,America/Argentina/Buenos_Aires,GMT-3"
    era5_path.write_text("\n".join(content) + "\n", encoding="utf-8")

    manifest_path = _write_manifest_matching_pair(tmp_path, era5_path, nasa_path)
    report = validate_pergamino_provenance(
        era5_path, nasa_path, mode=INPUT_MODE_SCIENTIFIC, manifest_path=manifest_path
    )
    assert not report.ok
    assert any(
        "ERA5-Land" in issue and ("latitud" in issue or "longitud" in issue)
        for issue in report.issues
    )


def test_scientific_mode_rejects_nasa_coordinates_that_do_not_match_its_own_reference(tmp_path):
    daily = make_synthetic_daily_frame(n_days=10, seed=11)
    era5_path = tmp_path / EXPECTED_ERA5_FILENAME
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)

    content = nasa_path.read_bytes().decode("ascii")
    corrupted = content.replace(
        "Location: latitude  -33.891   longitude -60.5746 ",
        "Location: latitude  0.0   longitude 0.0 ",
    )
    nasa_path.write_bytes(corrupted.encode("ascii"))

    manifest_path = _write_manifest_matching_pair(tmp_path, era5_path, nasa_path)
    report = validate_pergamino_provenance(
        era5_path, nasa_path, mode=INPUT_MODE_SCIENTIFIC, manifest_path=manifest_path
    )
    assert not report.ok
    assert any(
        "NASA POWER" in issue and ("latitud" in issue or "longitud" in issue)
        for issue in report.issues
    )


def test_scientific_mode_does_not_require_era5_and_nasa_coordinates_to_match_each_other(tmp_path):
    """ERA5 y NASA POWER devuelven coordenadas distintas por diseño (grillas
    nativas distintas): la validación nunca exige una coordenada común entre
    ambos proveedores (hallazgo H-01)."""
    era5, nasa = write_synthetic_pergamino_csv_pair(tmp_path, n_days=15, seed=12)
    manifest_path = _write_manifest_matching_pair(tmp_path, era5, nasa)

    report = validate_pergamino_provenance(
        era5, nasa, mode=INPUT_MODE_SCIENTIFIC, manifest_path=manifest_path
    )
    assert report.era5_latitude != report.nasa_power_declared_latitude
    assert report.ok, report.issues


def test_provenance_never_reports_a_value_analysis_issue_for_sentinel_presence(tmp_path):
    """H-03: la identidad/provenance nunca cuenta centinelas `-999` sobre el
    archivo completo -- eso pertenece al análisis por etapa, ya recortado."""
    daily = make_synthetic_daily_frame(n_days=10, seed=13)
    era5_path = tmp_path / EXPECTED_ERA5_FILENAME
    nasa_path = tmp_path / EXPECTED_NASA_POWER_FILENAME
    write_synthetic_era5_csv(era5_path, daily)
    write_synthetic_nasa_power_csv(nasa_path, daily)

    content = nasa_path.read_bytes().decode("ascii")
    first_data_line_end = content.index("\r\n", content.index("YEAR,DOY"))
    next_line_start = first_data_line_end + 2
    next_line_end = content.index("\r\n", next_line_start)
    original_line = content[next_line_start:next_line_end]
    parts = original_line.split(",")
    parts[2] = "-999"
    corrupted = content[:next_line_start] + ",".join(parts) + content[next_line_end:]
    nasa_path.write_bytes(corrupted.encode("ascii"))

    report = validate_pergamino_provenance(era5_path, nasa_path, mode=INPUT_MODE_SYNTHETIC)
    assert report.ok, report.issues
    assert not any("centinela" in issue for issue in report.issues)
