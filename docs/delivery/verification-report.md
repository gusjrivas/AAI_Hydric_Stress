# Informe de verificación del paquete de entrega

HU7/HU8 · capacidad `experiment-runner` (solo cierre técnico de la entrega) · fase CRISP-DM Deployment. Sin impacto en hipótesis, alcance, arquitectura ni configuración experimental. No es una validación científica nueva.

- Base de los artefactos: `02b4036eff939d442d63c10af99c0bc433917316` (merge del PR #238). CI de ese commit, ya completo: `backend-quality`, `frontend-quality`, `python-quality` y `experiment-v4-container` en éxito (run 42439030794). Al abrir el PR, `python-quality` y `experiment-v4-container` estaban aún en curso; ese estado queda como antecedente.
- Versión con la herramienta: PR #239, rama `fix/paquete-entrega-artefactos`. La base `02b4036` precede a `delivery_package.py`; el PR solo agrega documentación, la herramienta y su prueba, sin tocar código de la demo ni de los cargadores.
- Paquete vigente: `aai-hydric-stress-delivery-package-02b4036.zip`, 2 332 809 bytes, SHA-256 `d3c88874e552217f4f8ad280d553ae837fd7fb04ce4eced0fa536392ec8c32e5`, 76 archivos, **estado PARCIAL**.
- Entorno de verificación: clon limpio y aislado del commit `7db6fd5` (su `RESTORE.md` es el que contiene el paquete); venv con **Python 3.13.14** exacto, numpy 2.5.1, pandas 2.3.3, pyarrow 19.0.1, scikit-learn 1.9.0.

## Antecedente: revisión del SHA 89e63917 y correcciones

La revisión independiente reprodujo dos defectos, más una exclusión errónea de `.lock`. Se corrigieron en este PR con pruebas de regresión:

| Defecto | Corrección | Prueba |
| --- | --- | --- |
| `restore` aceptaba `restore_path="../outside.txt"`, informaba PASS y escribía fuera del destino | Todas las rutas del manifiesto se validan antes de escribir: se rechazan absolutas, de unidad, UNC, con `..`/`.`/vacías, con `\`, con `:`, duplicadas (sin distinguir mayúsculas), ambiguas (archivo y directorio) y destinos que resuelvan fuera de la raíz; el destino no puede ser un enlace simbólico; `verify` aplica lo mismo a zip y directorios extraídos y rechaza enlaces simbólicos y entradas fuera de `payload/` | 10 rutas inseguras sin escrituras fuera del destino, duplicados y ambiguos, `package_path` inseguro, entradas ajenas, directorio extraído y enlaces. Las 2 pruebas de enlaces se omiten en esta máquina Windows por falta de permiso: no cuentan como verificación aquí |
| `expand` no informaba faltantes (`present.txt` presente, `missing.txt` ausente) | Cada archivo obligatorio ausente se informa; un grupo obligatorio con comodines debe declarar `required_files`, y encontrar un solo archivo no lo completa | `missing.txt`, grupo con comodines, grupo sin requisitos, grupo opcional |
| `**/*.lock` no coincidía con `root.lock` | `_match` también prueba el patrón sin el prefijo `**/` | `root.lock`, `a/b/c.lock`, `root.locked` |

Requisitos mínimos reales declarados en `artifact-selection.json`, tomados de los cargadores: por cada horizonte 1-3, `ensemble_manifest.json` y por familia `bundle.json`, `contract.json`, `model.joblib` y `calibrator.joblib` (40 archivos con `run_manifest.json`); en la ejecución retrospectiva, `metrics.json` y `execution_manifest.json` (los lee el exportador de tablas) más el resto del conjunto canónico; los 11 registros de gobernanza más los tres archivos nombrados.

## Comprobaciones

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| SHA-256 del `.zip` contra su `.zip.sha256` | PASS | `sha256sum -c` |
| `verify` del `.zip` y del paquete extraído (76 archivos) | PASS | `delivery_package.py verify` |
| `restore` en directorio nuevo y revalidación posterior | PASS | 76 archivos |
| Pruebas de la herramienta | PASS | 23 pasan, 2 omitidas (enlaces simbólicos, sin permiso en Windows) |
| `ruff check src tests scripts/delivery_package.py` y `black --check src tests` | PASS | sin hallazgos |
| Script de recuperación probado en WSL con un árbol de ejemplo | PASS | copia 8/8, rechazo de destino existente y de destino dentro del origen, detección de alteración, originales con modo y propietario intactos |
| Hashes de lecturas y emisión de Pergamino contra los fijados en `prepare_defense_data.ps1` | PASS | F6F9E19A… / FCD7AC52… |
| `prepare_defense_data.ps1` sobre lo restaurado | PASS | copia aislada creada |
| Carga con `load_ensemble_bundle` de los 3 horizontes (9 componentes, cruzando hashes del manifiesto) | PASS con Python 3.13.14 | `[3, 3, 3]`; ver nota |
| Arranque de `start_defense_demo.ps1 -Mode pergamino` desde lo restaurado, puerto 8599, sin frontend | PASS | `/docs` 200; `/api/v2/sensors` lista el sensor; el histórico 2023-06-15 devuelve 3 `slots`; `-Stop` lo detuvo |
| Regeneración de las 5 tablas del ensamble retrospectivo desde el paquete | PASS con salvedad | Idénticas a las versionadas salvo CRLF del exportador en Windows (sin CR coinciden con el blob de Git). Comprobado sobre la compilación anterior del paquete; el payload es idéntico |
| `metrics.json` del ensamble retrospectivo contra el hash de la memoria | PASS | `6a6a31d3…2e67732` |
| CSV crudos de Pergamino de la ejecución contra `data/external/raw/` | PASS | hashes idénticos |
| Frontend (`npm`) y recorrido en el navegador | NOT_RUN | Fuera del alcance |
| Inferencia con una entrada de prueba aislada | NOT_RUN | No se ejecutó inferencia ni se generaron métricas |
| Recalcular cifras de A, B y C desde salidas crudas | BLOCKED | Faltan `evidence/{A,A_sensitivity_7_28cm,B,C}` |
| Verificar la evidencia del complemento H | BLOCKED | Falta `hitl-complement-2026-09-21` |
| Reproducción completa de procedencia (reentrenar) | NOT_RUN | Prohibido por el alcance |

**Corrección sobre el entorno.** La versión anterior de la guía indicaba «Python 3.13.x». Al cargar los bundles con el cargador real se comprobó que `load_operational_bundle` exige igualdad exacta del entorno capturado, incluido el parche de Python: con 3.13.15 rechaza los bundles con `incompatible_environment`; con 3.13.14 los carga. La demostración con emisiones persistidas arranca con cualquier Python porque no carga modelos. La guía y el manifiesto ahora exigen 3.13.14.

**Antecedente.** La primera verificación (SHA 89e63917, paquete `d5ccd777…` de 2 331 948 bytes) comprobó restauración, carga de 18 `.joblib` con `joblib` directo y arranque; no usó el cargador real ni detectó el requisito de Python exacto. El paquete previo se conserva fuera del repositorio en `previous-89e63917/`.

Restaurar en un directorio con ruta larga (más de unos 150 caracteres) falla en Windows por el límite de 260 caracteres; documentado en `RESTORE.md`.

## Faltantes

1. **Salidas crudas de A, B y C** (75 archivos). En WSL pertenecen a `root` con modo 0600; `gus` no puede leerlas y no se elevaron privilegios. Operación preparada y probada, pendiente de autorización: `docs/delivery/RECOVERY.md`.
2. **Evidencia del complemento H.** Respaldo esperado: `/mnt/scientific-backup/AAI_Hydric_Stress/hitl-complement-2026-09-21/` en el disco USB 1 (serie `8986451183503575922`), con `manifest/SHA256SUMS` de 100 archivos. El directorio de montaje existe vacío y no es un punto de montaje; no hay discos USB visibles en Windows. Falta el dispositivo conectado y montado: no se concluye que el respaldo no exista.
3. **Respaldo USB `closure-campaign-2026-09-21`** en el mismo dispositivo.

## Conclusión

Entrega **parcial**: apta para restaurar y demostrar el modo Pergamino, cargar los bundles con el entorno exacto y regenerar y contrastar las tablas del ensamble retrospectivo; **no** apta para afirmar reproducibilidad completa de la procedencia de A/B/C/H.
