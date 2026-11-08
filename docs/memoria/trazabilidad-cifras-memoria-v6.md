# Trazabilidad de las cifras de la memoria V6

Índice de respaldo entre las tablas y cifras de `TI_Rivas_Gustavo_V6.pdf` y los artefactos versionados en este repositorio. No introduce resultados nuevos, no modifica evidencia congelada y no amplía las conclusiones de la memoria. HU8 · capacidad `experiment-runner` · fase CRISP-DM Evaluation.

Verificación: contraste de la memoria contra `main` (2026-11-07). Las cifras se compararon con las fuentes indicadas; las salidas crudas de las etapas A, B y C no se releyeron (ver sección 3).

## 1. Cifras de la memoria y su fuente versionada

| Memoria | Contenido | Fuente en el repositorio |
| --- | --- | --- |
| Tabla 4.1, sección 4.3 | 8 configuraciones de Melchor Romero (F1, MCC, AP), 5 semillas | `docs/research/reference-v3-formal-table.md`; `docs/research/reference-v3-formal-results.json` (umbral 0,316782, 199 ejemplos de entrenamiento, persistencia F1 0,6 y MCC 0,0083, corte 2024-10-19) |
| Cobertura de 75,96 % | Humedad original de Melchor Romero 2024 | `data/melchor_romero_2024_consolidado_coverage.csv`; `data/esa_cci_soil_moisture_melchor_romero_2024_coverage.csv` |
| Tabla 4.2, sección 4.4.1 | MCC por familia en el desarrollo de Pergamino (0,7080 / 0,6980 / 0,6954 / 0,6858) | `docs/research/scientific-closure-synthesis-2026-09-22.md`, sección 3 (0,708028 / 0,697968 / 0,695372 / 0,685799) |
| 2184 predicciones, 3 particiones | Out-of-fold de la etapa A | `docs/research/scientific-closure-synthesis-2026-09-22.md` (prevalencia 727/2184) |
| Tabla 4.3, sección 4.4.2 | Regresión logística y persistencia, 2023 y 2024–2025; intervalos pareados | `docs/research/scientific-closure-synthesis-2026-09-22.md`, secciones 4 y 5; `openspec/scientific-closure/current-execution-checkpoint.md`; `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml` |
| Sección 4.4.3 | Bin 0,9–1,0 (n=83, 0,9643 frente a 0,6627), AUC 0,9390, Brier 0,0975 | `docs/research/scientific-closure-synthesis-2026-09-22.md`, sección 5 (ROC-AUC 0,939049; Brier 0,097512) |
| Sección 4.5.1, tablas 4.4 a 4.7 | Ensamble retrospectivo 2023: umbral 0,313058, 364/363/362 casos, 112 positivos, MCC, falsas alertas, omisiones, transiciones y episodios | `docs/research/tables/ensemble-retrospective-2023/*.csv`; `docs/research/ensemble-retrospective-evaluation-results.md`; `frontend/public/retrospective-2023.json` (SHA-256 `1bd003656e2624a0755c16d5c47ad23241b9f920a3ea9b1fff6f16943a33335b`, calculado sobre el contenido versionado en Git con saltos de línea LF; una copia con CRLF produce otro hash) |
| Sección 4.5.6, figura 4.4 | Calibración a tres días (n=31, 0,915 frente a 0,645) | `docs/research/tables/ensemble-retrospective-2023/reliability_bins.csv` |
| Sección 4.2 | Nueve modelos y nueve calibradores; quince pronósticos del 13 al 17/06/2023 | `docs/design/ensemble-real-execution-report-2026-09-26.md`; `docs/design/ensemble-historical-walkthrough-report-2026-09-26.md` |
| Tabla 4.8, sección 4.6.1 | MCC por semilla con correcciones simuladas | `docs/research/scientific-closure-synthesis-2026-09-22.md`, sección 6.1 |
| Sección 4.6.2 | Veinte registros, cuatro etiquetas invertidas, 0 de 4 detectadas, concordancia 16/20 | `docs/research/scientific-closure-synthesis-2026-09-22.md`, sección 6.2; `docs/research/forecast-evidence-assessment.md` |

Identidad del ensamble retrospectivo: ejecución `pergamino-ensemble-retrospective-2023-20260927T062026Z`, `metrics.json` SHA-256 `6a6a31d35196313061aa4363c98d422f4d1446a9f996d7af51cd93f762e67732`, SHA ejecutable `1e27ad46c1533dffd5b087c824f6e4cf710cbc17` (ver el `README.md` de la carpeta de tablas).

## 2. Capítulo 3 y el código

| Afirmación de la memoria | Código |
| --- | --- |
| Decisión del ensamble por promedio de tres salidas con corte 0,5; votos solo como indicador (ecuación 3.1) | `src/predictive_modeling/ensemble_bundle.py` (promedio, conteo de votos y umbral 0,5) |
| Isolation Forest inactivo en el pronóstico web, disponible en calidad | `backend/app/pipeline.py` (`include_anomaly_detection=False`); `backend/app/routers/quality.py` |
| Retardos, medias móviles de 3 y 7 días, percentil 20 | `src/predictive_modeling/contract.py` |
| Imputación causal por propagación hacia adelante | `src/data_quality/imputation.py` |
| Estados de procedencia del historial | `src/historical_replay/imputation_markers.py` |
| Escritura atómica del registro de feedback | `src/human_feedback/registry.py`; `backend/app/routers/feedback.py` |
| Servicios de despliegue (frontend, backend, MLflow, PostgreSQL, MinIO, preparación del almacenamiento) | `docker-compose.yml` (el servicio opcional `demo-control` no figura en la memoria) |

## 3. Salidas crudas de las etapas A, B y C

Las predicciones y los resultados por corrida de la campaña de cierre (`evidence/{A,B,C}`, incluidos `oof_predictions_<familia>.csv`) no están versionados en Git. Según el manifiesto del protocolo (`controlled-daily-v4-external-pergamino-manifest.yaml`, `actual_paths`):

- ubicación de trabajo: `/home/gus/scientific-closure-runtime/evidence` (WSL);
- copia de respaldo: `/mnt/scientific-backup/AAI_Hydric_Stress/closure-campaign-2026-09-21` (disco USB 1, serie 8986451183503575922);
- huella del conjunto diario derivado: `8062605be37af073a9b6db9be53063cd88fdfc038273f9d45baa036277038931` (2913 filas);
- imagen de ejecución: `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af`; SHA ejecutable `214735e42ee04f018156cd630591e798aadd8bf3`; SHA documental `37eed42716803baa9bdbed912356b981adac093a`.

Las cifras de la memoria para A, B y C se apoyan en los agregados versionados de la sección 1. Para recalcularlas desde cero se requiere la copia de respaldo. Versionar esas salidas queda como decisión pendiente de la autoría, tal como lo declara el manifiesto.

## 4. Nota sobre los CSV crudos

El manifiesto del protocolo (`raw_csv_policy`) mantenía los CSV crudos fuera de Git. Tras el respaldo del 2026-11-07, ese campo se actualizó para reflejar que los cuatro CSV de Pergamino y Balcarce están en `data/external/raw/`, con hashes SHA-256 idénticos a los del protocolo. El cambio es solo de registro: no altera datos, parámetros, resultados ni la memoria.
