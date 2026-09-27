# Tablas agregadas de la evaluacion retrospectiva 2023

Tablas derivadas exclusivamente de los agregados de la ejecucion canonica
`pergamino-ensemble-retrospective-2023-20260927T062026Z`. No se leyeron predicciones, no se ejecuto inferencia y
no se usa la corrida duplicada como replica.

- Fuente canonica: `C:\Repo\AAI_Hydric_Stress_ensemble_retrospective_runtime\pergamino-ensemble-retrospective-2023-20260927T062026Z`
- `metrics.json` SHA-256: `6a6a31d35196313061aa4363c98d422f4d1446a9f996d7af51cd93f762e67732`
- `execution_manifest.json` SHA-256: `780386ff58b490a452d77f968e61efcd15b998a97d28de2f908ab1a346d9d33b`
- SHA ejecutable: `1e27ad46c1533dffd5b087c824f6e4cf710cbc17`
- Protocolo SHA-256: `6525f639276d5f809a701336090c58cc9dce888bd49f092b97af792c90201fdf`
- Estado: `completado`
- Inicio/fin UTC: `2026-09-27T06:28:11.542111+00:00` / `2026-09-27T06:30:35.689840+00:00`

Los CSV preservan la precision numerica del JSON sin redondeo. Un valor no
disponible queda vacio y se acompana por columnas `status`/`reason`; nunca se
convierte `null` en cero. Persistencia y mayoria no reciben AP, Brier ni bins
porque no son modelos probabilisticos en este analisis.

Archivos: `evaluation_support.csv`, `classification_metrics.csv`,
`paired_mcc_comparisons.csv`, `episode_onset.csv` y `reliability_bins.csv`.

Regeneracion (solo agregados canonicos):

```powershell
python scripts/export_ensemble_retrospective_tables.py --source-dir "C:\Repo\AAI_Hydric_Stress_ensemble_retrospective_runtime\pergamino-ensemble-retrospective-2023-20260927T062026Z" --output-dir "docs/research/tables/ensemble-retrospective-2023"
```
