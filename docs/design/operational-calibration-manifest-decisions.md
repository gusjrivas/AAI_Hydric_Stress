# Decisiones cerradas del manifiesto operacional +1/+2/+3

Trazabilidad: HU4/HU6; capacidades `predictive-modeling` y
`architecture-integration`; CRISP-DM modelado y evaluación de desarrollo. Cierra
parte de las decisiones pendientes de
[`operational-calibration-manifest-proposal.md`](operational-calibration-manifest-proposal.md)
sobre
[`config/producer-calibration-plan.draft.json`](../../config/producer-calibration-plan.draft.json).
No entrena, calibra ni evalúa modelos; no abre holdouts; no modifica
`controlled_daily_v3`, protocolos, hipótesis, alcance ni arquitectura.

## Estado

`status` permanece `draft`. `inspect_calibration_manifest` (validado en
contenedor `python:3.12-slim`, sin instalar nada en el host, dado que este
entorno no tiene intérprete Python en PATH) reporta exactamente dos
incumplimientos, ambos esperados:

```
tolerances.epsilon_ece debe ser numérico
tolerances.epsilon_bin debe ser numérico
```

Ningún otro campo falla. El manifiesto **no** se congeló
(`freeze_calibration_manifest` no fue invocado): `require_ready_for_fit`
seguiría rechazándolo por `status` y por las tolerancias faltantes, tal como
corresponde a un plan con una decisión de producto pendiente.

## Decisiones cerradas (ratificadas en este entrega)

| Campo | Valor cerrado | Motivo de cierre |
|---|---|---|
| `dataset.sensor_id` | `melchor_romero_2024_consolidado` | El dataset no es un sensor IoT en vivo; `sensor_naming.py` documenta explícitamente que este dataset histórico nunca lleva el prefijo `sensor__`. Se reutiliza el `dataset_id` como identidad estable de esta evaluación de desarrollo, sin inventar un sensor inexistente. |
| `model_plan.hyperparameters` | `n_estimators=100, criterion=gini, max_depth=None, min_samples_split=2, min_samples_leaf=1, max_features=sqrt, bootstrap=true` | Copiados del código vigente: `predictive_modeling/models.py::build_candidate_models` construye `RandomForestClassifier(random_state=...)` sin overrides; estos son los valores por defecto de scikit-learn que el código efectivamente usa hoy. **No** se reutilizó la cifra histórica `max_depth=5` de `controlled_daily_v3`, que la spec señala como evidencia, no como configuración vigente. Limitación: `pyproject.toml` fija `scikit-learn>=1.4` sin pin exacto ni lockfile, por lo que estos defaults deben reverificarse contra la versión efectivamente instalada antes de congelar. |
| `deployment_seed` | `0` | Primer valor de la serie predeclarada `training_seeds`, elegido por convención antes de entrenar, conforme a la propuesta. |
| `support.minimum_bin_count/minimum_class_count/minimum_temporal_blocks` | `10/10/4` | Ratificados tal como propuestos: son pisos operativos de detectabilidad, no garantías estadísticas; se documentó esa distinción en `support.justification`. |
| `coverage.minimum` | `0.80` | Ratificado tal como propuesto. |
| Bloques temporales | Contiguos de 7 días sobre `target_date` | Ratificado; mayor que el hueco máximo observado de humedad (6 días). |
| Ventanas de estabilidad | `2024-10-19..2024-11-24` y `2024-11-25..2024-12-31` | Ratificadas; ambas dentro de `evaluation`, sin solape, sobre `target_date`, `criteria_reference=global`. |
| Incertidumbre | Bootstrap de bloques móviles de 7 días, `replicates=5000`, `resampling_seed=20260919`, sin imputar target, réplicas/alcances sin soporte declarados inválidos | Ratificado tal como propuesto. |
| Multiplicidad | Cuantil 0.95 del máximo estadístico sobre una única familia conjunta (horizonte × semilla × ventana × bin respaldado), sin separar por horizonte | Ratificado: separar por horizonte relajaría el control conjunto y cambiaría el significado del gate; se documentó en `multiplicity.method`. |
| `log_loss.clipping_epsilon` | `1e-15` | Ratificado tal como propuesto; protección numérica uniforme, no tolerancia de aprobación. |

Ningún valor se ajustó mirando resultados: no se abrió el tramo de evaluación
ni se calcularon prevalencias, soporte real o desempeño.

## Decisión mínima pendiente

`tolerances.epsilon_ece` y `tolerances.epsilon_bin` quedan **sin valor**. Son
una decisión de producto (cuánto error de calibración, en puntos de
probabilidad sobre límites superiores simultáneos, sigue siendo honesto
mostrarle al productor), no una constante derivable del dataset o del código.

Pregunta concreta para quien apruebe el producto: **¿qué error superior
aceptamos publicar como "calibrado" en la UI del productor: 0.10/0.15,
un valor más estricto, o directamente ningún porcentaje hasta contar con
evidencia externa?**

Alternativas y consecuencias:

1. **Adoptar `epsilon_ece=0.10` / `epsilon_bin=0.15`** (los valores de
   referencia ya discutidos en la propuesta). Consecuencia: es la tolerancia
   más permisiva evaluada hasta ahora; sin evidencia estadística que la
   respalde, aprobarla equivale a una decisión de producto explícita de
   tolerar hasta 10-15 puntos porcentuales de error simultáneo, no a un
   hallazgo técnico.
2. **Adoptar un valor más estricto** (p. ej. la mitad). Consecuencia: sube la
   probabilidad de que el gate resulte `failed` o `insufficient_evidence` con
   apenas 74 días de evaluación y ventanas de 37 días; puede dejar la UI sin
   `display_probability` en la mayoría de los escenarios, lo cual es un
   resultado válido, no un defecto del manifiesto.
3. **No fijar tolerancia todavía** (mantener `status=draft` indefinidamente).
   Consecuencia: el manifiesto sigue bloqueado para `ready_for_fit`; ningún
   ajuste, calibración o evaluación puede ejecutarse hasta que producto
   decida, lo cual es consistente con "no aprobar porcentajes por
   conveniencia" pero retrasa HU4/HU6.

Hasta que se resuelva, `status` permanece `draft` y `display_probability`
seguiría siendo `null` en cualquier evaluación futura.
