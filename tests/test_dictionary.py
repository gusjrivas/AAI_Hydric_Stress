from data_ingestion.dictionary import read_data_dictionary, write_data_dictionary


def test_write_and_read_data_dictionary_roundtrip(tmp_path):
    write_data_dictionary(
        source_name="nasa_power",
        provenance="real",
        license_="Dominio público (NASA POWER Data Use Policy)",
        limitations="No provee humedad de suelo ni ET0 directamente.",
        dictionaries_dir=tmp_path,
    )

    entry = read_data_dictionary("nasa_power", dictionaries_dir=tmp_path)

    assert entry["source_name"] == "nasa_power"
    assert entry["provenance"] == "real"
    assert "generated_at" in entry
