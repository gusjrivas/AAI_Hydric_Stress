# Informe de verificación del paquete de entrega

HU7/HU8 · capacidad `experiment-runner` (solo cierre técnico de la entrega) · fase CRISP-DM Deployment. Sin impacto en hipótesis, alcance, arquitectura ni configuración experimental. No es una validación científica nueva.

- Commit base: `02b4036eff939d442d63c10af99c0bc433917316` (merge del PR #238). CI de ese commit al consultarlo: `backend-quality` y `frontend-quality` en éxito; `python-quality` y `experiment-v4-container` aún en curso.
- Paquete: `aai-hydric-stress-delivery-package-02b4036.zip`, 2 331 948 bytes, SHA-256 `d5ccd7776fc6de96d8e3e89612e54387fb2c8433938f8da5cfc045f898a2abaf`, 76 archivos, **estado PARCIAL**.
- Entorno de verificación: copia limpia (clon aislado) del commit con la herramienta, venv nuevo con Python 3.13, numpy 2.5.1, pandas 2.3.3, pyarrow 19.0.1, scikit-learn 1.9.0 (el de `run_manifest.json`).

## Comprobaciones

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| SHA-256 del `.zip` contra su `.zip.sha256` | PASS | `sha256sum -c` |
| `verify` del `.zip` (76 archivos, manifiesto y `SHA256SUMS` coherentes) | PASS | `delivery_package.py verify` |
| `verify` del paquete extraído | PASS | idem, sobre directorio extraído |
| `restore` en directorio nuevo y revalidación posterior | PASS | 76 archivos |
| Pruebas de la herramienta (`tests/test_delivery_package.py`) | PASS | 4 pruebas: exclusión de `.lock`, bytes con CRLF intactos, destino no vacío, detección de alteración |
| Hashes de lecturas y emisión de Pergamino contra los fijados en `scripts/prepare_defense_data.ps1` | PASS | F6F9E19A… / FCD7AC52…; el propio script los exige |
| `prepare_defense_data.ps1` sobre lo restaurado | PASS | copia aislada creada |
| Carga de 9 modelos y 9 calibradores `.joblib` y de los JSON de bundles | PASS | 18 `.joblib`, 22 JSON |
| Arranque de `start_defense_demo.ps1 -Mode pergamino` con lo restaurado, puerto 8599, sin frontend | PASS | `/docs` 200; `/api/v2/sensors` lista `pergamino-ensemble-demo`; `GET …/historical/2023-06-15/forecasts` devuelve el lote con `slots`; `-Stop` lo detuvo |
| Regeneración de las 5 tablas del ensamble retrospectivo desde el paquete | PASS con salvedad | Idénticas a las versionadas salvo que en Windows el exportador escribe CRLF; sin CR coinciden con el blob de Git. Solo lee agregados |
| `metrics.json` del ensamble retrospectivo contra el hash de la memoria | PASS | `6a6a31d3…2e67732` |
| CSV crudos de Pergamino de la ejecución contra `data/external/raw/` | PASS | hashes idénticos |
| Frontend (`npm`) y recorrido en el navegador | NOT_RUN | Fuera del alcance de esta comprobación |
| Inferencia con una entrada de prueba aislada | NOT_RUN | La demo usa emisiones persistidas; no se ejecutó inferencia ni nuevas métricas |
| Recalcular cifras de A, B y C desde salidas crudas | BLOCKED | Faltan `evidence/{A,A_sensitivity_7_28cm,B,C}` (ver abajo) |
| Verificar evidencia del complemento H | BLOCKED | Falta `hitl-complement-2026-09-21` |
| Reproducción completa de procedencia (reentrenar) | NOT_RUN | Prohibido por el alcance |

Las comprobaciones de restauración, carga y arranque se ejecutaron sobre una compilación previa del paquete que difiere de la final solo en `RESTORE.md` (se agregó la nota de rutas cortas); los 75 archivos restantes y sus hashes son idénticos, y la compilación final se volvió a verificar y restaurar.

Observación: restaurar en un directorio con ruta larga (más de unos 150 caracteres) falla en Windows por el límite de 260; documentado en `RESTORE.md`.

## Faltantes

1. **Salidas crudas de A, B y C** (75 archivos: `metrics.json`, `oof_predictions_*.csv`, `predictions_2023.csv`, `predictions_2024_2025.csv`, `integrity_manifest.json`, etc.). En el árbol de trabajo WSL pertenecen a `root` con modo 0600; el usuario de trabajo no puede leerlas y no se elevaron privilegios. Impide recalcular las cifras de las etapas A/B/C.
2. **Evidencia del complemento H.** No existe en el árbol WSL; según los congelados de `sc-08-aux-hitl` está en `/mnt/scientific-backup/…/hitl-complement-2026-09-21`, y el montaje del respaldo USB está vacío. Impide verificar H y su `SHA256SUMS`.
3. **Respaldo USB `closure-campaign-2026-09-21`** no montado; impide contrastar copia de trabajo y respaldo.

## Conclusión

Entrega **parcial**: apta para restaurar y demostrar el modo Pergamino y para regenerar y contrastar las tablas del ensamble retrospectivo; **no** apta para afirmar reproducibilidad completa de la procedencia de A/B/C/H.
