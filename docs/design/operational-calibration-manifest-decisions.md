# Decisiones cerradas del manifiesto operacional +1/+2/+3

## Actualizacion 2026-09-21 (2) — multiplicidad conjunta y congelamiento v3

**El congelamiento v2 (2026-09-21, `config/producer-calibration-plan.frozen.v2.json`,
`content_sha256=0c3bbe8a9364ac26c40da3f603fc2e14cf6c97af20e48cd533d9361ea9dca918`)
queda SUSTITUIDO. No usar como manifiesto activo.** (v1 ya estaba sustituido
desde la actualizacion anterior y sigue intacto, sin cambios.)

Dos inconsistencias encontradas en v2, ambas en la construccion del limite
simultaneo family-wise (`multiplicity`/`uncertainty`), sin tocar el ECE, las
tolerancias ni las particiones (esas correcciones de la actualizacion
anterior se mantienen):

1. **Maximo parcial al perder soporte un bin.** v2 decia: "unicamente el
   termino de ESE bin en ESA replica queda invalido y se excluye del
   computo... no invalida por si solo la replica completa." Eso es calcular
   un maximo parcial omitiendo un componente no estimable de la familia
   conjunta, lo cual entendio implicitamente el maximo como mas chico de lo
   que la familia realmente exige. Corregido: `uncertainty.invalid_replicate_rule`
   ahora dice que CUALQUIER componente no estimable (clase, bloques
   temporales, o un bin de `backed_bin_family` sin soporte al remuestrear)
   vuelve la REPLICA ENTERA no evaluable para toda la familia; no se
   calcula un maximo parcial. No se adopto un tratamiento conservador
   alternativo (por ejemplo, sustituir el componente faltante por un valor
   predeclarado): eso seria una decision metodologica nueva que requeriria
   una propuesta explicita, no aplicada silenciosamente aqui. El umbral ya
   existente ("mas de la mitad de las replicas no evaluables -> insufficient_evidence")
   se mantiene sin cambios.
2. **Multiplicidad separada por tipo de estadistico.** v2 calculaba "por
   separado" un maximo/percentil para ECE y otro para error absoluto por
   bin. `design.md` exige un unico limite simultaneo family-wise para
   "ECE y errores absolutos de intervalos respaldados, en la familia
   completa" (una sola construccion conjunta, no dos independientes).
   Corregido: `multiplicity.method` ahora especifica un UNICO maximo por
   replica sobre la union de todos los terminos de ECE
   (`uncertainty.ece_bin_inclusion`) y todos los terminos de error por bin
   (`uncertainty.backed_bin_family`); el percentil 0.95 de esa unica
   distribucion produce un solo limite `U`, que se compara por separado
   contra `epsilon_ece` y `epsilon_bin` (ambas tolerancias usan el mismo
   `U`, no percentiles independientes). Separar las familias, como hacia
   v2, relaja el control conjunto exigido por el diseno.

Se agrego ademas `uncertainty.coverage_guarantee_caveat`, exigido
explicitamente: el percentil bootstrap sobre bloques dependientes no
garantiza cobertura simultanea exacta en muestra finita; se reporta como
limite superior aproximado, no como garantia estadistica formal.

Pruebas en `tests/test_calibration_manifest.py`, diferenciando texto de
calculo:
- `test_manifest_text_separates_ece_inclusion_backed_bins_and_no_partial_maxima`
  (comprobacion de texto: confirma las frases clave del borrador corregido
  y la ausencia de las frases de v1/v2 con el error).
- `test_synthetic_missing_component_makes_the_whole_replicate_not_evaluable`
  (calculo sintetico: implementa la regla "todo o nada" y muestra que un
  implementador incorrecto devolveria un maximo parcial en vez de "no
  evaluable").
- `test_synthetic_joint_maximum_combines_ece_and_bin_error_terms_together`
  (calculo sintetico: muestra que el maximo conjunto sobre ECE + error por
  bin es mayor o igual a cualquiera de los dos maximos separados, y en el
  ejemplo estrictamente mayor que el maximo de ECE solo).
- `test_frozen_v1_manifest_is_preserved_untouched_but_superseded` y
  `test_frozen_v2_manifest_is_preserved_untouched_but_superseded` (guardan
  los hashes de v1 y v2 y confirman que retienen el texto con el error
  correspondiente, como evidencia historica).
- `test_frozen_v3_manifest_matches_the_corrected_draft_and_uses_joint_multiplicity`
  (verifica v3 contra el borrador corregido, y que tolerancias/particiones
  no cambiaron).

`inspect_calibration_manifest` sobre el borrador corregido (contenedor
`python:3.12-slim`, sin interprete Python en el host) devuelve `issues=()`.
Se congelo:
[`config/producer-calibration-plan.frozen.v3.json`](../../config/producer-calibration-plan.frozen.v3.json)
(+ `producer-calibration-plan.frozen.v3.json.identity.json`,
`content_sha256=de65e3c021fb04c568fec1dfc02633688ef42144cccba67ec476667323429f2e`,
`byte_length=12746`, `frozen_at=2026-09-21T14:00:00Z`).
`verify_frozen_calibration_manifest` confirma su identidad y
`require_ready_for_fit` pasa. v1 y v2 se verificaron byte a byte sin
cambios antes y despues de este congelamiento.

**Referencia activa:** desde esta actualizacion, el manifiesto congelado
vigente es `producer-calibration-plan.frozen.v3.json`. `frozen.json` (v1) y
`frozen.v2.json` quedan sustituidos y se conservan solo como evidencia
historica.

No se entreno, calibro ni evaluo ningun modelo; no se abrio el tramo de
evaluacion ni holdouts; no se modificaron `controlled_daily_v3`,
protocolos v3/v4, specs canonicas, hipotesis, alcance ni arquitectura.
Trazabilidad: HU4/HU6, capacidad `predictive-modeling`, CRISP-DM
modelado/evaluacion de desarrollo.

## Actualizacion 2026-09-21 — correccion del ECE y congelamiento v2

**El congelamiento v1 (2026-09-20, `config/producer-calibration-plan.frozen.json`,
`content_sha256=0301207e5d750002694a73b3e9313ee2ea6bff58f1081fcd4797c2ef9279cbd1`)
queda SUSTITUIDO. No usar como manifiesto activo.**

Hallazgo: `uncertainty.method` de v1 calculaba el ECE "solo bins con soporte
en esa replica" (filtrando por `minimum_bin_count`). Esto contradice
[`design.md`](../../openspec/changes/add-daily-multihorizon-predictors/design.md):
"ECE se define como suma de n_b/N por abs(frecuencia_b - probabilidad_media_b)
sobre los intervalos no vacíos del conjunto evaluado (...) No omitir
intervalos de poco soporte del cálculo para mejorar la cifra." `support.minimum_bin_count`
gobierna `coverage` y las afirmaciones individuales por bin, no la suma del
ECE. v1 no se abrio ni se evaluo con datos reales; el error es puramente de
especificacion (texto del manifiesto), detectado antes de cualquier ajuste.

Correccion aplicada sobre `config/producer-calibration-plan.draft.json`
(nueva revision del borrador, no se toco `frozen.json` de v1 ni su
identidad, que siguen intactos como evidencia historica):

- `uncertainty.method` ya no dice "solo bins con soporte"; el ECE suma
  ahora sobre todos los bins con al menos 1 observacion del alcance.
- Se separan tres conceptos con campos propios, para que no vuelvan a
  confundirse:
  - `uncertainty.ece_bin_inclusion`: bins incluidos en el ECE (todos los
    no vacios; el conjunto se fija una unica vez por alcance a partir del
    conjunto observado completo sin remuestrear, y es identico en las
    5000 replicas — nunca cambia segun lo que ocurra en una replica
    particular).
  - `uncertainty.backed_bin_family`: bins respaldados (>= `minimum_bin_count`)
    usados para `coverage`, para publicar un porcentaje individual por bin y
    para el error absoluto sujeto a `epsilon_bin`; tambien fijo por alcance.
  - `uncertainty.invalid_replicate_rule`: reescrita para que una replica
    solo se invalide por condiciones estructurales (clase o bloques
    temporales insuficientes), nunca porque un bin puntual pierda soporte;
    perder soporte en un bin de `backed_bin_family` excluye unicamente el
    termino de ese bin en esa replica, sin invalidar la replica ni su ECE
    ni sacar al bin de la familia predeclarada. Esto resuelve la
    ambiguedad entre "excluir replicas invalidas" (regla de soporte,
    ciega al resultado) y "no descartar replicas o intervalos
    desfavorables" (prohibicion de cherry-picking): son compatibles
    porque actuan en momentos y sobre criterios distintos, y la familia
    de comparacion no cambia silenciosamente entre replicas.
- `multiplicity.method` referencia ahora explicitamente ambas familias
  fijas (`ece_bin_inclusion` para ECE, `backed_bin_family` para el error
  por bin) en vez de una unica nocion ambigua de "bins con soporte".

No se modificaron tolerancias (`epsilon_ece=0.10`, `epsilon_bin=0.15`),
particiones, soporte (10/10/4), cobertura (0.80), ventanas de estabilidad,
semillas, dataset ni hiperparametros: solo el texto que define el ECE y la
regla de invalidez de replicas.

Pruebas agregadas en `tests/test_calibration_manifest.py`:
`test_frozen_v1_manifest_is_preserved_untouched_but_superseded` (guarda el
hash de v1 y confirma que conserva el texto con el error, como evidencia
historica), `test_draft_separates_ece_inclusion_backed_bins_and_replicate_invalidity`
(verifica que el borrador ya no dice "solo bins con soporte" y sí declara
las tres piezas separadas) y
`test_synthetic_ece_over_all_nonempty_bins_differs_from_support_filtered_ece`
(fixture sintetico que muestra numericamente cuanto subestima el ECE la
regla incorrecta: con un bin no vacio pero sin soporte muy mal calibrado,
el ECE correcto es mayor que 0 y el filtrado por soporte da 0). No se
implemento ni se ejecuto codigo real de calculo de ECE (esa
implementacion, tarea 10 de `tasks.md`, sigue pendiente); estas son
pruebas sobre la especificacion del manifiesto y sobre la definicion
matematica, con datos sinteticos.

`inspect_calibration_manifest` sobre el borrador corregido (contenedor
`python:3.12-slim`) devuelve `issues=()`. Se congelo una nueva revision:
[`config/producer-calibration-plan.frozen.v2.json`](../../config/producer-calibration-plan.frozen.v2.json)
(+ `producer-calibration-plan.frozen.v2.json.identity.json`,
`content_sha256=0c3bbe8a9364ac26c40da3f603fc2e14cf6c97af20e48cd533d9361ea9dca918`,
`byte_length=11248`, `frozen_at=2026-09-21T01:00:00Z`).
`verify_frozen_calibration_manifest` confirma su identidad y
`require_ready_for_fit` pasa. `producer-calibration-plan.draft.json` sigue
siendo el antecedente vivo (status=draft), ahora con la correccion
incorporada.

**Referencia activa:** desde esta actualizacion, el manifiesto congelado
vigente es `producer-calibration-plan.frozen.v2.json`, no
`producer-calibration-plan.frozen.json` (v1, sustituido y preservado solo
como evidencia).

No se entreno, calibro ni evaluo ningun modelo; no se abrio el tramo de
evaluacion ni holdouts; no se modificaron `controlled_daily_v3`,
protocolos v3/v4, specs canonicas, hipotesis, alcance ni arquitectura.
Trazabilidad: HU4/HU6, capacidad `predictive-modeling`, CRISP-DM
modelado/evaluacion de desarrollo.

## Actualizacion 2026-09-20 (2) — congelamiento tecnico

Se resolvieron los cuatro pendientes tecnicos dejados abiertos por la
actualizacion anterior y se congelo el manifiesto. No se reabrieron
tolerancias (epsilon_ece=0.10, epsilon_bin=0.15 quedan como fueron
aprobadas) ni ninguna otra decision ya cerrada; no se miro el tramo de
evaluacion ni se calculo resultado alguno.

1. **Identidad reproducible.** Se re-verifico `dataset.sha256` con
   `sha256sum` sobre `data/melchor_romero_2024_consolidado.parquet` (sin
   abrir el archivo como datos): coincide byte a byte con el valor ya
   declarado. Se agrego `dataset.variables` (columnas y unidades reales
   segun `data_ingestion/schema.py`: `soil_moisture` m3/m3,
   `temperature` degC, `relative_humidity` %, `precipitation` mm/day,
   `solar_radiation` MJ/m2/day, `wind_speed` m/s) y
   `dataset.excluded_columns_fully_null` (`et0` y las cuatro columnas
   opcionales, 100% nulas segun la auditoria, sin uso en el bundle). Se
   agrego un bloque `environment` con las versiones de Python/numpy/
   pandas/scikit-learn/pyarrow efectivamente resueltas al validar
   `model_plan.hyperparameters` contra los defaults reales de
   `RandomForestClassifier`, con una limitacion explicita: `pyproject.toml`
   fija minimos sin lockfile, por lo que esta es la resolucion usada para
   verificar este manifiesto, no una garantia de reinstalacion identica en
   un ajuste futuro.
2. **Algoritmo de incertidumbre.** `uncertainty.centering` precisa que el
   limite superior es un percentil 0.95 no centrado (no pivotal, sin
   correccion de sesgo) sobre la distribucion empirica de replicas;
   `multiplicity.method` aplica el maximo de ese estadistico sobre la
   familia completa antes de tomar ese percentil. `uncertainty.invalid_replicate_rule`
   resuelve la aparente contradiccion: una replica se excluye solo por
   perder el soporte predeclarado (regla ciega al resultado, evaluada
   antes de calcular su estadistico), nunca por producir un valor
   desfavorable; si mas de la mitad de las 5000 replicas de un alcance
   quedan invalidas por soporte, ese alcance es `insufficient_evidence` en
   vez de reportar un cuantil sobre una mayoria de replicas invalidas.
3. **Bloques de 7 dias.** `uncertainty.block_length_rationale` deja
   explicito que la semana es una convencion operacional de agrupamiento
   calendario, elegida antes de ver resultados, y que el hueco maximo
   observado (6 dias) no es evidencia de la duracion real de la
   dependencia temporal; solo se usa para que un bloque no quede vacio por
   un hueco ya conocido.
4. **Coherencia con el validador.** `inspect_calibration_manifest` sobre
   el manifiesto actualizado (contenedor `python:3.12-slim`, sin
   intérprete Python en el host) devuelve `issues=()`; no se modifico
   `calibration_manifest.py` ni se debilito ningun chequeo. Los campos
   nuevos (`environment`, `dataset.variables`,
   `dataset.excluded_columns_fully_null`, `uncertainty.centering`,
   `uncertainty.invalid_replicate_rule`, `uncertainty.block_length_rationale`)
   son informativos: el validador no los exige ni los usa para aprobar.

**Resultado:** con `report.issues == ()` y `status` completable, se
construyo una copia del manifiesto con `status="ready_for_fit"` y
`frozen_at="2026-09-20T22:30:00Z"`, y se congelo con
`freeze_calibration_manifest` en
[`config/producer-calibration-plan.frozen.json`](../../config/producer-calibration-plan.frozen.json)
(+ su identidad en `producer-calibration-plan.frozen.json.identity.json`,
`content_sha256=0301207e5d750002694a73b3e9313ee2ea6bff58f1081fcd4797c2ef9279cbd1`,
`byte_length=8905`). `verify_frozen_calibration_manifest` confirma que el
contenido coincide con su identidad y pasa `require_ready_for_fit`.
[`config/producer-calibration-plan.draft.json`](../../config/producer-calibration-plan.draft.json)
se conserva sin cambios de contenido salvo `status`/`frozen_at` (permanece
`draft`), como antecedente del proceso de decision, tal como exige el
protocolo de no congelar planes incompletos y de no sobrescribir
artefactos ya congelados.

No se entreno, calibro ni evaluo ningun modelo; no se abrio el tramo de
evaluacion ni holdouts; no se modificaron `controlled_daily_v3`,
protocolos v3/v4, specs canonicas, hipotesis, alcance ni arquitectura.
Trazabilidad: HU4/HU6, capacidad `predictive-modeling`, CRISP-DM
modelado/evaluacion de desarrollo; cierra la tarea 1.3 de
`openspec/changes/add-daily-multihorizon-predictors/tasks.md`.

## Actualizacion 2026-09-20 — tolerancias aprobadas
El autor aprobo explicitamente epsilon_ece=0.10 y epsilon_bin=0.15 como
criterios de producto para evaluacion exploratoria. Se registran en el JSON.
Esta actualizacion reemplaza el pendiente de tolerancias descrito en la nota
historica siguiente. No cambia soporte, ventanas, modelos o datos.

El archivo permanece draft: aceptar tolerancias no congela el plan ni acredita
calibracion. Antes de congelar, verificar hash del dataset sin evaluar resultados,
variables/unidades y versiones efectivas del entorno como exige el diseno.
Precisar tambien el algoritmo de limites simultaneos (estadistico centrado y
construccion del limite) y la regla para replicas invalidas: el texto actual
dice que se excluyen, pero tambien afirma que no se descartan replicas.
La longitud de huecos no justifica por si sola la dependencia temporal.
Son comprobaciones tecnicas pendientes; no requieren volver a pedir aprobacion
de estas dos tolerancias ni permiten ajustarlas mirando resultados.

Trazabilidad: HU4/predictive-modeling, CRISP-DM modelado/evaluacion de desarrollo.
Sin cambio de protocolos v3/v4, configuraciones formales, hipotesis, arquitectura,
datasets o resultados HU7/HU8. No se entreno, calibro ni evaluo ningun modelo.

## Registro previo a la aprobacion (historico)

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
