# Informe de verificación del paquete de entrega

HU7/HU8 · capacidad `experiment-runner` (solo cierre técnico de la entrega) · fase CRISP-DM Deployment. Sin impacto en hipótesis, alcance, arquitectura ni configuración experimental. No es una validación científica nueva ni repite A/B/C/H.

## Identidad

- Base de los artefactos: `02b4036eff939d442d63c10af99c0bc433917316` (merge del PR #238; su CI completo está en éxito, run 42439030794).
- Versión del repositorio con la herramienta: rama `fix/paquete-entrega-artefactos` (PR #239). `02b4036` precede a `delivery_package.py`.
- Verificación sobre un clon limpio y aislado del commit `d7475cbee79bc564d21503a2f8bc81912767323d` (herramienta y `RESTORE.md` que contiene el paquete; los commits posteriores solo agregan este informe), con Python 3.13.14, numpy 2.5.1, pandas 2.3.3, pyarrow 19.0.1 y scikit-learn 1.9.0.
- **Paquete vigente (v2):** `aai-hydric-stress-delivery-package-02b4036-v2.zip`, 263 215 921 bytes, 314 archivos (276 878 344 bytes sin comprimir), SHA-256 `f91f1ad73853bd056cd0c2844cdb0eea345124eaf48d047d8ad455725fc6dd95`, estado **COMPLETE para el alcance definido** (`scope_definition` y `limitations` en el manifiesto).
- Paquetes anteriores, conservados fuera del repositorio: v1 de la primera versión (SHA 89e63917, `d5ccd777…`) y la versión parcial con correcciones de rutas (SHA e6997168, `d3c88874…`).

## Respaldo recibido

`backup_AAI_Hydric_strees-20261108T152637Z-1-001.zip`, 271 034 253 bytes, SHA-256 `b41b762e9eb65ecffe5ec89f8306b813a1527cfcab06edbd9a80d297305abced`. Contiene tres ZIP anidados completos (no es multiparte; ningún nombre sugiere otra parte y la prueba de integridad de los cuatro archivos pasa): `AAI_Hydric_Stress.zip` (campañas de cierre y H, finalización de evidencia), `AAI_Hydric_Stress_ensemble_demo_backup.zip` y `AAI_Hydric_Stress_ensemble_retrospective_backup.zip`. El original no se modificó (hash idéntico antes y después). Se extrajo a una carpeta nueva, validando antes rutas (sin absolutas, `..`, enlaces ni colisiones) y sin ejecutar nada; la correspondencia ruta en el ZIP → archivo extraído → SHA-256 queda en el registro local de auditoría.

Tres planos de integridad, separados:

| Plano | Resultado |
| --- | --- |
| (a) ZIP recibido | PASS: prueba de integridad ZIP en el externo y en los tres anidados. Su hash de hoy acredita solo la recepción. |
| (b) Archivos extraídos | PASS: coinciden con los SHA256SUMS propios que traen (campaña 14/14; H 100/100; finalización 25/25; instantánea final 91/91; `C/integrity_manifest.json` 18/18). |
| (c) Coincidencia con lo canónico | PASS parcial: ver abajo. |

## Coincidencia con las evidencias históricas canónicas

| Comprobación | Resultado |
| --- | --- |
| H: `contract_sha256`, `package_sha256` (forma canónica recomputada), `response_sha256` y transcripción 1 contra los congelados de `sc-08-aux-hitl` | PASS |
| H: contrato, congelados y 6 informes de revisión idénticos a los blobs de Git (el árbol de trabajo en Windows es CRLF; la comparación es contra el blob o sin CR) | PASS |
| A/B/C: los 16 archivos legibles de WSL (gobernanza, ledgers, identidad de entorno, custodia de B) idénticos byte a byte a los de la instantánea final | PASS |
| A/B/C: nombres y tamaños de los 76 archivos de `A`, `A_sensitivity_7_28cm`, `B` y `C` de WSL idénticos a los de la instantánea final | PASS (solo nombre y tamaño) |
| A/B/C: los 75 archivos de WSL con modo 0600 y propietario `root` no se leyeron; no hay comparación de hash contra ellos | NOT_RUN. No se ejecutó la copia con privilegios porque el respaldo resolvió A/B/C (condición fijada para no ejecutarla) |
| Instantáneas intermedias (`after-A`, `after-B`, `after-B-with-governance`, `after-C-corrected`, `after-C-final`): archivos A/B/C idénticos a los de `final` en todos los casos | PASS (no hay copias divergentes; solo difieren registros de gobernanza posteriores) |
| Respaldos de demo y retrospectivo del ZIP contra las copias locales | PASS: 45/45 y 16/16 archivos comunes idénticos byte a byte; el respaldo no tiene `httpdata` ni `walkthrough` |

Discrepancia sin impacto numérico: el ZIP de Drive no demuestra ser copia exacta del disco USB 1 (serie 8986451183503575922); solo se verifica por sus manifiestos internos.

## Cifras contrastadas (agregación de predicciones originales; sin ejecutar modelos)

`scripts/verify_delivery_evidence.py` sobre lo restaurado: 21 PASS, 0 FAIL, 0 BLOCKED, 0 NOT_RUN.

- A: MCC soft voting 0,708028, regresión logística 0,697968, Random Forest 0,695372, HGB 0,685799 (desde predicciones y desde `metrics.json`); 2184 filas y 727 positivos.
- B: 362 filas y 96 positivos.
- C (holdout 2024-2025, solo agregación de la predicción ya existente): MCC 0,664770 y 0,573438 (persistencia), ROC-AUC 0,939049, Brier 0,097512, matrices [[525, 75], [14, 114]] y [[555, 45], [45, 83]].
- Tablas del ensamble retrospectivo regeneradas a un directorio temporal: idénticas a las versionadas salvo CRLF del exportador en Windows. `metrics.json` = `6a6a31d3…2e67732`, el de la memoria.

## Comprobaciones de la entrega

| Comprobación | Resultado |
| --- | --- |
| Hash del zip contra su `.zip.sha256` | PASS |
| `verify` del zip y del paquete extraído (314 archivos) | PASS |
| `restore` en directorio nuevo y revalidación (314 archivos) | PASS |
| Pruebas: 26 pasan, 2 omitidas (enlaces simbólicos; Windows sin permiso) | PASS; las 2 omitidas no cuentan como verificación |
| `ruff check src tests scripts/delivery_package.py scripts/verify_delivery_evidence.py` y `black --check src tests` | PASS |
| `load_ensemble_bundle` de los 3 horizontes (9 componentes) con Python 3.13.14 | PASS |
| Arranque de la demo Pergamino desde lo restaurado (`/docs` 200, sensor listado, histórico 2023-06-15 con 3 `slots`, detención) | PASS |
| `prepare_defense_data.ps1` con los hashes fijados | PASS |
| `check_scientific_closure.py` | PASS estructural |
| Frontend en el navegador | NOT_RUN |
| Inferencia con entrada de prueba | NOT_RUN |
| Reentrenar o repetir A/B/C/H | NOT_RUN (prohibido) |

## Qué se recuperó

- Salidas originales de A, A_sensitivity_7_28cm, B y C (76 archivos) con gobernanza y ledgers (instantánea final de 93 archivos).
- Complemento H completo (102 archivos, manifest de 100).
- Campaña de cierre: manifiesto, imagen Docker de ejecución (217 MB), código, entorno y entradas (17 archivos).
- Finalización de evidencia 2026-09-22 (26 archivos, opcional).

Excluido a propósito: instantáneas intermedias, `rehearsal` y `code-final` de la campaña (fuera de su SHA256SUMS), y lo ya listado en `excluded_on_purpose`.

## Antecedentes

Los defectos de rutas, faltantes obligatorios y `.lock` de la revisión del SHA 89e63917 y la exigencia de Python 3.13.14 exacto se corrigieron antes (SHA e6997168, CI en éxito); sus pruebas siguen vigentes. El estado anterior era PARCIAL por la falta de A/B/C y H.

## Limitaciones y alcance

COMPLETE se refiere a que todos los artefactos obligatorios del alcance definido están presentes y verifican; no equivale a reproducir los experimentos ni cambia los estados científicos (RB-05, `sc-06-scientific-synthesis`, `SC-GOV-025` y GF siguen en FAIL; `sc-08-aux-hitl` en PASS; R/N/S NOT_APPLICABLE). Persisten las limitaciones listadas arriba y en `limitations` del manifiesto. Restaurar con rutas largas falla en Windows por el límite de 260 caracteres; ver `RESTORE.md`.
