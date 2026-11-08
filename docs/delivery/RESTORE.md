# Restauración del paquete externo de artefactos

Guía portable. No depende de usuarios ni de rutas de una máquina concreta. El paquete **no** está en Git ni en ninguna release: se entrega aparte, con su archivo `.zip.sha256`.

**Estado del paquete: COMPLETE para el alcance definido** (`package_status` en `PACKAGE_MANIFEST.json`): todos los grupos obligatorios —demostración de Pergamino, evidencia de las cifras (ensamble retrospectivo 2023, salidas originales de A/B/C, complemento H) y procedencia de la campaña— están presentes y verifican contra sus hashes y manifiestos históricos. **No equivale a reproducción por reejecución** ni a una validación científica nueva; ver `limitations` en el manifiesto. Los estados científicos (RB-05, `sc-06`, `SC-GOV-025` y GF en FAIL; `sc-08` en PASS) no cambian.

## Contenido por finalidad

| Finalidad | Grupos | Carácter |
| --- | --- | --- |
| Demostración | `demo-datos-pergamino`, `demo-bundles-ensamble` | Obligatorio para arrancar el modo Pergamino |
| Verificación de cifras publicadas | `evidencia-ensamble-retrospectivo-2023`, `evidencia-cierre-gobernanza` | Obligatorio para regenerar las tablas del ensamble y contrastar registros de gobernanza |
| Salidas originales A/B/C | `salidas-crudas-ABC` (instantánea final de la campaña, 93 archivos) | Obligatorio para recalcular las cifras de A/B/C |
| Complemento H | `evidencia-H` (102 archivos, con `manifest/SHA256SUMS` de 100) | Obligatorio para verificar H |
| Procedencia de la campaña | `campana-cierre-entorno-y-codigo` (imagen Docker, código, entorno, entradas, manifiesto) | Obligatorio para la procedencia completa |
| Procedencia adicional | `demo-procedencia-ejecucion`, `ledger-holdout`, `entorno-preejecucion`, `finalizacion-evidencia-2026-09-22` | Opcional, solo lectura |

Versionado en Git (no está en el paquete): `data/external/raw/` (CSV crudos), `docs/research/tables/ensemble-retrospective-2023/`, `docs/research/reference-v3-formal-results.json` y el conjunto de Melchor Romero.

## Entorno compatible

El cargador de bundles (`load_operational_bundle`) exige que el entorno capturado coincida **exactamente** con el declarado en cada `bundle.json`, incluida la versión de parche de Python; con otra versión (p. ej. 3.13.15) rechaza los bundles con `incompatible_environment`. Entorno requerido: **Python 3.13.14**, numpy 2.5.1, pandas 2.3.3, pyarrow 19.0.1, scikit-learn 1.9.0. El modo de demostración con emisiones persistidas arranca igualmente con otro Python porque no carga modelos, pero no sirve para cargar o ejecutar los bundles. Commit de código que generó los bundles: `67eed9d0d3b9657ae43f267e258af549f8c3a9a8`. ## Dos referencias de repositorio distintas

| Referencia | Qué identifica | Valor |
| --- | --- | --- |
| `artifact_base_commit` (en `PACKAGE_MANIFEST.json`) | Estado del repositorio al que corresponden los artefactos (merge del PR #238) | `02b4036eff939d442d63c10af99c0bc433917316` |
| Versión con la herramienta | Primer estado que contiene `scripts/delivery_package.py`, esta guía y `docs/delivery/` | rama `fix/paquete-entrega-artefactos` (PR #239) y, tras su integración, `main` |

El commit `02b4036` **precede** a la herramienta: un clon en ese commit no tiene `delivery_package.py`. El código de la demo y de los cargadores es el mismo en ambas referencias (el PR #239 solo agrega documentación, la herramienta y su prueba), por lo que se usa la versión con la herramienta para todo el procedimiento.

## Copia limpia, de principio a fin

```powershell
git clone https://github.com/gusjrivas/AAI_Hydric_Stress.git aai-restore
cd aai-restore
git checkout fix/paquete-entrega-artefactos      # o `main` una vez integrado el PR #239
git log -1 --format=%H                           # anotar el commit usado
```

Luego seguir los pasos de la sección siguiente. Para un diagnóstico, el primer comando de la herramienta (`verify`) no necesita dependencias de Python más allá de la biblioteca estándar.

## Pasos

En Windows, elegir rutas cortas (p. ej. `C:\aai-art`): los bundles tienen rutas profundas y una ruta de destino larga supera el límite de 260 caracteres.

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
   pip install uv ; uv python install 3.13.14      # o cualquier instalación de Python 3.13.14 exacta
   uv venv --python 3.13.14 .venv ; .\.venv\Scripts\Activate.ps1
   uv pip install -e ".[backend]" numpy==2.5.1 pandas==2.3.3 pyarrow==19.0.1 scikit-learn==1.9.0
   python -c "from src.predictive_modeling.operational_inference import capture_environment as c; print(c())"   # debe mostrar python 3.13.14
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

7. Evidencia de A/B/C y de H: manifiestos y SHA256SUMS históricos, congelados de `sc-08-aux-hitl` y contraste de cifras agregando predicciones ya existentes (no ejecuta modelos; requiere pandas y scikit-learn del entorno anterior):

   ```powershell
   python scripts/verify_delivery_evidence.py --root $env:AAI_ARTIFACT_ROOT
   echo $LASTEXITCODE   # 0 solo si TODAS las comprobaciones obligatorias se ejecutaron y aprobaron
   ```

   Rutas restauradas: `$AAI_ARTIFACT_ROOT/closure-campaign-2026-09-21/evidence-snapshots/final/evidence/{A,A_sensitivity_7_28cm,B,C}` y `$AAI_ARTIFACT_ROOT/hitl-complement-2026-09-21/`. Cada árbol conserva su `SHA256SUMS` para `sha256sum -c`.

## Qué no hacer

No reentrenar, no repetir A/B/C/H, no evaluar sobre el holdout 2024-2025 ni sustituir archivos faltantes por datos sintéticos. Los registros `.sqlite` se abren en solo lectura.

## Alcance

El empaquetado no es una validación científica nueva. Los estados FAIL/PASS/BLOCKED/NOT_APPLICABLE de `openspec/scientific-closure/current-execution-checkpoint.md` no cambian.
