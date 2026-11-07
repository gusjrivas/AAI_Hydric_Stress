# Datos crudos externos (respaldo)

Copia de respaldo de los cuatro CSV originales que el protocolo `controlled_daily_v4` (ADR-0011) ubica fuera del repositorio, en `C:\Repo\AAI_Hydric_Stress_external_data\raw`. Productos de reanálisis, no mediciones de sensores de campo: ERA5-Land (vía Open-Meteo) y NASA POWER, 2015-2025, sitios Pergamino y Balcarce.

La copia es byte a byte (`.gitattributes` desactiva la conversión de fin de línea para estos archivos). Las rutas externas citadas en la documentación siguen siendo las de referencia; este directorio no las reemplaza.

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `pergamino_era5land_soil_hourly_2015_2025.csv` | 3954003 | `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f` |
| `pergamino_nasa_power_daily_2015_2025.csv` | 127568 | `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b` |
| `balcarce_era5land_soil_hourly_2015_2025.csv` | 3954004 | `838b787f1f6c00b18b5d96dc0cd65b1a38421f46cac7fc6454ad94a80c740f2d` |
| `balcarce_nasa_power_daily_2015_2025.csv` | 127993 | `61293aa07cc9067a5c12f199e18bd4e560a493fa673aa9885e916549451bf65b` |

Los hashes de Pergamino coinciden con los registrados en `docs/design/ensemble-real-enablement-plan.md` y en `docs/design/ensemble-real-execution-report-2026-09-26.md`. Los de Balcarce se calcularon al momento del respaldo (2026-11-07) y no figuran en esos documentos.
