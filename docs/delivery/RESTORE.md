# Restauración del paquete externo de artefactos

Guía portable. No depende de usuarios ni de rutas de una máquina concreta. El paquete **no** está en Git ni en ninguna release: se entrega aparte, con su archivo `.zip.sha256`.

**Estado del paquete: PARCIAL.** Cubre la demostración de Pergamino y la evidencia necesaria para contrastar las cifras de la memoria del ensamble retrospectivo; **no** incluye las salidas crudas de las etapas A/B/C ni la evidencia del complemento H (ver `known_missing` en `PACKAGE_MANIFEST.json`). Por eso no permite reproducir completamente la procedencia de la campaña `controlled_daily_v4_external_pergamino`.

## Contenido por finalidad

| Finalidad | Grupos | Carácter |
| --- | --- | --- |
| Demostración | `demo-datos-pergamino`, `demo-bundles-ensamble` | Obligatorio para arrancar el modo Pergamino |
| Verificación de cifras publicadas | `evidencia-ensamble-retrospectivo-2023`, `evidencia-cierre-gobernanza` | Obligatorio para regenerar las tablas del ensamble y contrastar registros de gobernanza |
| Procedencia | `demo-procedencia-ejecucion`, `ledger-holdout`, `entorno-preejecucion` | Opcional, solo lectura |

Versionado en Git (no está en el paquete): `data/external/raw/` (CSV crudos), `docs/research/tables/ensemble-retrospective-2023/`, `docs/research/reference-v3-formal-results.json` y el conjunto de Melchor Romero.

## Entorno compatible

Los `.joblib` se serializaron con `scikit-learn 1.9.0`. Entorno de los bundles (`run_manifest.json`): Python 3.13.x, numpy 2.5.1, pandas 2.3.3, pyarrow 19.0.1, scikit-learn 1.9.0. Commit de código que generó los bundles: `67eed9d0d3b9657ae43f267e258af549f8c3a9a8`. Commit del repositorio al que corresponde el paquete: el indicado en `repository_commit` del manifiesto.

## Pasos

Variables (PowerShell; en bash usar `export`):

```powershell
$env:AAI_PACKAGE   = "<ruta al .zip del paquete>"
$env:AAI_ARTIFACT_ROOT = "<directorio NUEVO y vacío donde restaurar>"
```

1. Verificar el paquete completo antes de extraer (archivo `.zip.sha256` y contenido):

   ```powershell
   Get-FileHash -Algorithm SHA256 $env:AAI_PACKAGE   # comparar con el .zip.sha256
   python scripts/delivery_package.py verify $env:AAI_PACKAGE
   ```

2. Restaurar (verifica de nuevo, rechaza destinos no vacíos y revalida después de escribir):

   ```powershell
   python scripts/delivery_package.py restore $env:AAI_PACKAGE --target $env:AAI_ARTIFACT_ROOT
   ```

3. Crear el entorno compatible e instalar el proyecto:

   ```powershell
   python -m venv .venv ; .\.venv\Scripts\Activate.ps1
   pip install -e ".[backend]"
   pip install numpy==2.5.1 pandas==2.3.3 pyarrow==19.0.1 scikit-learn==1.9.0
   ```

4. Preparar los datos de la demo en un directorio nuevo dentro de `.demo-defense-data/` (el script comprueba los SHA-256 fijados):

   ```powershell
   ./scripts/prepare_defense_data.ps1 `
     -SourceDataDir "$env:AAI_ARTIFACT_ROOT/demo/pergamino-walkthrough-2023-06-13_17" `
     -DemoDataDir ".demo-defense-data/pergamino-restaurado"
   ```

5. Arrancar la demo con la raíz de bundles restaurada (no agregar `pergamino-ensemble-demo` al final):

   ```powershell
   ./scripts/start_defense_demo.ps1 -Mode pergamino `
     -DataDir ".demo-defense-data/pergamino-restaurado" `
     -BundleRoot "$env:AAI_ARTIFACT_ROOT/demo/pergamino-ensemble-demo-2026-09-26T034114Z"
   ```

6. Tablas del ensamble retrospectivo (solo lee agregados canónicos; no ejecuta inferencia):

   ```powershell
   python scripts/export_ensemble_retrospective_tables.py `
     --source-dir "$env:AAI_ARTIFACT_ROOT/evidence/pergamino-ensemble-retrospective-2023-20260927T062026Z" `
     --output-dir "<directorio nuevo>"
   ```

## Qué no hacer

No reentrenar, no repetir A/B/C/H, no evaluar sobre el holdout 2024-2025 ni sustituir archivos faltantes por datos sintéticos. Los registros `.sqlite` se abren en solo lectura.

## Alcance

El empaquetado no es una validación científica nueva. Los estados FAIL/PASS/BLOCKED/NOT_APPLICABLE de `openspec/scientific-closure/current-execution-checkpoint.md` no cambian.
