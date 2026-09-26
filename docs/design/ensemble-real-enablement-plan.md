# Hito 2 — Estado real de la habilitación del ensamble v4 (documento de estado; nada ejecutado en esta intervención)

**Estado:** documento de estado y planificación. Ningún paso de entrenamiento, calibración, refit o empaquetado real se ejecutó en esta intervención. No autoriza, por sí mismo, ninguna acción nueva sobre datos reales, ni la apertura o reutilización del holdout, ni ningún experimento A/B/C.

**Origen:** sección 7 de `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md` (Hito 1, contrato técnico del ensamble operativo, mergeado en PR #217, verificado exclusivamente con fixtures sintéticas).

**HU/capacidad:** `experiment-runner` (HU7, `controlled_daily_v4_external_pergamino`) + `predictive-modeling` (contrato operativo del ensamble, Hito 1). **Fase CRISP-DM:** evaluación de admisibilidad — no despliegue, no modelado nuevo.

## 0. Corrección respecto de la versión anterior de este documento

La versión anterior afirmaba: *"No se encontró en lo inspeccionado ninguna ejecución real de Stage A sobre Pergamino."* Esa afirmación es **incorrecta** a la luz de evidencia que esta intervención sí revisó: la campaña `controlled_daily_v4_external_pergamino` (Etapas A→B→C) **se ejecutó realmente el 2026-09-21**, una sola vez, con identidad ejecutable verificada (commit `214735e42ee04f018156cd630591e798aadd8bf3`, imagen `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af`), exit 0 y custodia verificada en las tres etapas. Fuentes: `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml` (`status: EXECUTED_2026_09_21`), `openspec/scientific-closure/decisions.md` (GD-38, GD-40), `openspec/scientific-closure/changes.json` (`sc-03-stage-a`/`sc-04-stage-b`/`sc-05-stage-c`, los tres `"status": "PASS"`), y `docs/research/scientific-closure-synthesis-2026-09-22.md`.

**No confundir "no encontrado" con "nunca ejecutado":** esta corrección es precisamente el caso que esa distinción advertía. Lo que sigue siendo válido de la sección 0 original —consultar antes de proponer repetir cualquier experimento— ya no aplica a la pregunta "¿existe una ejecución real de A?" (respuesta: sí, verificada), pero sigue aplicando a cualquier pregunta sobre datos que la campaña *no* usó.

## 1. Qué se acreditó realmente (release de la campaña 2026-09-21)

- **Cierre científico:** `SC-GOV-025`/`GF` cierran en **`FAIL`**, no en `PASS` ni `PASS_WITH_LIMITATIONS` (`openspec/scientific-closure/README.md`, `decisions.md` GD-40). Causa: defecto de **gobernanza de secuencia de gates** — las auditorías independientes de A y B se escribieron a disco *después* de que B y C, respectivamente, ya habían corrido (`changes.json`: la aprobación de `sc-04-stage-b` cita "sc-03 PASS" a las `03:20:00Z`, pero la transición `REVIEW→PASS` de `sc-03-stage-a` no ocurre hasta las `04:30:00Z` — 70 minutos después; mismo patrón entre B y C). **No** es una falla de los resultados numéricos de A/B/C en sí (`decisions.md` GD-40: "no invalida las métricas recomputadas... que permanecen como resultados numéricos verificados").
- **Aceptación administrativa (GD-40):** desviación histórica permanente e irreparable. B y C deben presentarse solo como **evidencia retrospectiva exploratoria**, nunca como validación confirmatoria gobernada. **No se autoriza reejecutar B, C ni reabrir el holdout 2024-2025 bajo ningún supuesto derivado de esta decisión.**
- **Holdout 2024-2025:** abierto una única vez, de forma irreversible, `2026-09-21T04:06:11Z`, autorización explícita del responsable, ledger `holdout.sqlite` estado `CONFIRMADA`. Cerrado; no se reabre.

## 2. Qué familias y horizontes tienen soporte real — y por qué el ensamble de 3 votos no puede armarse con lo ejecutado

- **Horizonte:** la campaña real cubrió **exclusivamente t+3** (`experimental_design.target.horizon_days: 3` en el manifiesto; corroborado por `scientific-closure-synthesis-2026-09-22.md`). **No existe ninguna ejecución real, ni siquiera parcial, para horizonte +1 o +2.** Extender el protocolo a esos horizontes sería una decisión metodológica nueva, fuera del alcance de este documento y de esta intervención — no se propone aquí.
- **Selección de familia (Etapa A, 2015–2022, OOF anidado):** se evaluaron las 4 candidatas del diseño (`logistic_regression`, `random_forest`, `hist_gradient_boosting_classifier`, `soft_voting` con pesos fijos 1/3) — el mismo universo de familias que la política `ensemble_agreement_v1` de Hito 1 usa para las tres primeras. Resultado: **`SIN_GANADOR_ESTABLE`** (ninguna superó a las demás por el margen predeclarado Δ=0.05 MCC; MCC OOF: soft_voting 0.7080, logistic_regression 0.6980, random_forest 0.6954, hist_gradient_boosting_classifier 0.6858). El desempate predeclarado por simplicidad eligió **`logistic_regression`** como única candidata llevada a B y C.
- **Consecuencia directa, verificada en código (`src/experiment_runner/controlled_daily_v4/stage_a_runner.py`, `freezing.py`):** el protocolo v4 congela (`freeze_family` + `fit_final_estimator`) **únicamente a la familia ganadora**. `random_forest` y `hist_gradient_boosting_classifier` **nunca fueron congeladas ni reajustadas sobre el `eligible_frame` completo** — solo existen sus métricas de comparación de la Etapa A. La rama de código que sí congelaría las tres bases (`stage_a_runner.py`, cuando `selection.selected_family == FAMILY_SOFT_VOTING`) **no se ejecutó** en la corrida real, porque la ganadora fue `logistic_regression`, no `soft_voting`.
- **Calibración:** el protocolo real **no aplicó ningún paso de calibración** a la familia ganadora ni a ninguna otra (`scientific-closure-synthesis-2026-09-22.md`, §7: "Calibración no corregida... el protocolo congelado no lo predeclaraba"). Es una limitación documentada y verificada: las probabilidades sobre el holdout 2024–2025 son sistemáticamente sobreconfiadas (ej. 96% predicho vs. 66% observado en el bin superior).
- **Persistencia de estimadores:** confirmado directamente en código (`freezing.py`, sin llamadas a `joblib.dump`/`pickle.dump` en todo el paquete `controlled_daily_v4/`) — `fit_final_estimator` devuelve el estimador ajustado **solo en memoria**, nunca lo serializa. No existe ningún `model.joblib`/`calibrator.joblib` de la campaña real, ni de `logistic_regression` ni de ninguna otra familia.

## 3. Dónde viven los artefactos reales — corrección: el dataset crudo y el entorno exacto SÍ son accesibles desde esta máquina

**Corrección respecto de la versión anterior de esta sección**, que concluía que esta sesión no tenía acceso físico a los datos ni al entorno real. Verificado en esta intervención (nada de esto entrena; son solo lecturas/comprobaciones de identidad):

- **Dataset crudo, localizado y con hash verificado:** `C:\Repo\AAI_Hydric_Stress_external_data\raw\pergamino_era5land_soil_hourly_2015_2025.csv` (SHA-256 `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f`) y `pergamino_nasa_power_daily_2015_2025.csv` (SHA-256 `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b`). Estos hashes coinciden byte a byte con las copias ya presentes en el runtime WSL (`/home/gus/scientific-closure-inputs/migration-20260920/.../raw/`). Verificado además contra la referencia versionada del propio manifiesto ejecutando el comando de validación que el runner ya provee, sin entrenar nada:
  ```
  python -m experiment_runner.controlled_daily_v4.cli --stage A --validate-inputs-only \
    --era5-csv .../pergamino_era5land_soil_hourly_2015_2025.csv \
    --nasa-power-csv .../pergamino_nasa_power_daily_2015_2025.csv \
    --output-dir <dir-vacío-descartable>
  ```
  Resultado: `Provenance OK. --validate-inputs-only: no se entrena nada.` — ejecutado dos veces, con resultado idéntico: (a) en el host Windows/`tcnenv`, (b) dentro de la imagen Docker exacta de la campaña (ver punto siguiente). Ningún archivo quedó escrito; el directorio de salida usado se descartó vacío.
- **Entorno exacto de la campaña, presente localmente:** la imagen `experiment-v4-scientific-closure:latest` (`docker images` → ID `55bc923efac0`) coincide con `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af`, la imagen aprobada que produjo A, B y C el 2026-09-21. No hace falta reconstruir nada: ya está disponible en el Docker Desktop de esta máquina.
- **Evidencia de la campaña cerrada (`/home/gus/scientific-closure-runtime/evidence/{A,B,C}`, vía WSL Ubuntu):** los **nombres** de los artefactos son legibles (`ls`) y confirman lo ya sabido — existe `frozen_config.json` (singular, solo `logistic_regression`) y, adicionalmente, `oof_predictions_{logistic_regression,random_forest,hist_gradient_boosting_classifier,soft_voting}.csv` para las 4 candidatas de la Etapa A. **El contenido de estos archivos está bajo control de acceso** (propietario `root`, modo `600`) y esta intervención **no escaló privilegios** para leerlo — es una barrera de custodia deliberada, no un obstáculo a saltear. No se leyó `frozen_config.json`, `metrics.json` ni ningún `oof_predictions_*.csv` real.
- **Consecuencia:** el bloqueo de "acceso a datos/entorno" que la versión anterior de esta sección declaraba **ya no aplica**. Lo que sigue bloqueado es una cuestión de **autorización y alcance metodológico**, no de acceso — ver secciones 5 y 6.

## 4. Búsqueda de autorización operativa — resultado: no encontrada, y un hallazgo explícitamente negativo

Se revisaron `openspec/scientific-closure/decisions.md` (GD-1 a GD-40), `README.md`, `risks.md`, `changes.json`, ADR-0009/0010/0011 y el protocolo de Pergamino, buscando cualquier autorización, ADR o decisión que habilite reutilizar los artefactos/código/configuración de A/B/C con un fin **operativo** (alimentar un ensamble de apoyo a la decisión en vivo), distinto del fin **científico** (confirmación HU7/HU8, ya cerrada en `FAIL` de gobernanza). **No se encontró ninguna.** Ningún documento afirma que el protocolo se haya "ampliado" para uso operativo.

El hallazgo más directamente relevante es explícitamente **negativo**: `openspec/scientific-closure/closure-verification-2026-09-20/claim-evidence-review.json` registra la pregunta "Is operational anticipation asserted?" con respuesta **"NO"**, y cita la limitación de que la anticipación operativa prospectiva "cannot be asserted without further own evidence". `scientific-closure-synthesis-2026-09-22.md` (§8/§11) refuerza lo mismo: la campaña es "retrospectivo, no operativo", sin medición de latencia, disponibilidad de dato en tiempo real, ni utilidad de riego.

**No se infiere ni se da por aprobada ninguna autorización a partir de este silencio.** La ausencia de una prohibición explícita no equivale a una habilitación.

## 5. Matriz por horizonte

| Horizonte | Estado | Causa |
| --- | --- | --- |
| +1 | **BLOQUEADO** | Sin cobertura real de protocolo. `HORIZON_DAYS=3` está fijo como constante de módulo en `features.py` (`frame["future_soil_moisture"] = s.shift(-HORIZON_DAYS)`), no como parámetro — soportar +1 exige modificar código congelado. No se propone ni se implementa aquí (sección 6.3). |
| +2 | **BLOQUEADO** | Idéntica causa que +1. |
| +3 | **BLOQUEADO** | Ya no por falta de datos/entorno (sección 3, corregida) ni por falta de decisión explícita registrada — sigue condicionado a que el responsable resuelva las dos cuestiones metodológicas de la sección 6.1/6.2, que esta intervención no decide por sí misma. |

Ningún horizonte alcanza el cuarto estado ("ensemble habilitado con artefactos reales admisibles", sección 8). Hito 2 permanece sin ejecutar.

## 6. Propuesta concreta para +3 — alcance técnico, particiones, ejecución y criterio de habilitación

### 6.0 Qué cambió respecto de la versión anterior

Con la corrección de la sección 3, el único bloqueo real para +3 pasó de ser "no hay acceso a datos/entorno" a ser, exclusivamente, dos decisiones metodológicas que el responsable debe resolver (6.1, 6.2) y, una vez resueltas, una ejecución bien definida (6.4). +1/+2 siguen bloqueados por una causa distinta y más dura: el código congelado no admite otro horizonte sin modificarse (6.3).

### 6.1 Decisión pendiente 1 — completar las familias faltantes

`random_forest` e `hist_gradient_boosting_classifier` no tienen modelo final ajustado en la campaña real — solo participaron en la comparación OOF de la Etapa A (`evidence/A/oof_predictions_{random_forest,hist_gradient_boosting_classifier}.csv`, confirmados existentes por nombre; contenido no leído, ver sección 3). Completar el ensamble exigiría, para cada una, tomar su mejor configuración ya evaluada en la grilla de A (leída de `evidence/A/metrics.json`, root-only, no leído aquí) y ejecutar `freeze_family` + `fit_final_estimator` sobre el mismo `eligible_frame` ya usado por A — sin tocar B, C ni el holdout. **Pregunta para el responsable:** ¿esto es reutilización admisible de una evaluación ya hecha, o constituye una ejecución científica nueva? `decisions.md` (GD-38) reserva expresamente esa clase de decisión ("el orquestador no tiene autoridad para decidir eso por su cuenta"); esta intervención tampoco la decide.

### 6.2 Decisión pendiente 2 — introducir calibración

Ninguna de las 4 candidatas de la campaña real fue calibrada nunca; el protocolo congelado no lo predeclaraba (sección 2). El contrato de Hito 1 (`load_operational_bundle`) exige un `calibrator.joblib` por componente — sin este paso, **ninguna familia real, ni siquiera la ganadora `logistic_regression`, puede empaquetarse**, independientemente de 6.1. Añadir `CalibratedClassifierCV(FrozenEstimator(modelo), method="sigmoid")` donde el protocolo real nunca lo tuvo **es un cambio metodológico**, explícitamente fuera de la autoridad que este encargo delimita ("no autoriza... cambios metodológicos"). **Pregunta para el responsable:** ¿se autoriza agregar este paso como parte del empaquetado operativo (Hito 2), documentado como una diferencia explícita respecto del protocolo científico congelado, sin alterar éste?

### 6.3 +1/+2 — cambio mínimo necesario, no implementado

`features.py` usa la constante de módulo `HORIZON_DAYS` directamente en el cálculo del target (`s.shift(-HORIZON_DAYS)`), no un parámetro de configuración pese a que `config.py` sí declara un campo `horizon_days` (actualmente decorativo para este cálculo). El cambio mínimo sería parametrizar ese `shift` para leer `config.horizon_days` en lugar de la constante — pero esto exige re-verificar, para cada nuevo horizonte, los márgenes de corte temporal (`gap` de `TimeSeriesSplit`), el P20 por fold y la ventana de comparación con persistencia, ninguno de los cuales fue nunca evaluado a +1/+2. Es un cambio de código sobre `controlled_daily_v4/` congelado — no se implementa en esta intervención ni se propone su aprobación aquí; solo se documenta como lo que haría falta.

### 6.4 Particiones propuestas para +3 (si 6.1 y 6.2 se autorizan)

Restricción de fondo: **los 11 años de dato (2015–2025) ya están íntegramente asignados** a alguna etapa de la campaña cerrada — A (2015–2022, desarrollo/selección), B (2023, validación temporal), C (2024–2025, holdout cerrado). No existe ningún período "nunca tocado" fuera del holdout (que permanece intocable). Por lo tanto, cualquier demo real para +3 necesariamente reutiliza días que ya participaron en selección (A) o en la compuerta de validación (B) — y debe decirlo explícitamente, nunca presentarse como evaluación independiente.

| Partición propuesta | Rango (fecha objetivo, t+3) | Rol | Independencia real |
| --- | --- | --- | --- |
| Entrenamiento demo | 2015-01-10 a 2021-12-31 | Ajustar las 3 familias (refit determinístico) | **No independiente**: subconjunto del rango de desarrollo/selección de la Etapa A; cada día participó como train u OOF-validación en algún fold del nested CV que decidió `SIN_GANADOR_ESTABLE`. |
| Calibración demo | 2022-01-01 a 2022-12-31 | Ajustar `CalibratedClassifierCV` por familia | **No independiente**: último año del rango de desarrollo de la Etapa A, mismo motivo. |
| Recorrido demo (no "evaluación") | 2023-01-01 a 2023-12-31 | Recorrido operativo de punta a punta (HTTP real, votos, agregación) con números reales | **No independiente**: coincide exactamente con el período de validación temporal de la Etapa B (la compuerta que autorizó abrir el holdout). Debe presentarse solo como demostración de arquitectura, nunca como validación prospectiva. |
| — | 2024-01-01 a 2025-12-31 | — | **Fuera de alcance permanente**: holdout cerrado, irreversible. No se usa bajo ningún concepto. |

Orden causal preservado (entrenamiento < calibración < recorrido, sin fuga temporal); el propio contrato de Hito 1 (`temporal_cuts`, `HorizonContract`) ya exige y verifica esto en tiempo de carga.

### 6.5 Ejecución preparada (comandos exactos, nada ejecutado)

Entorno verificado disponible localmente (sección 3): imagen `experiment-v4-scientific-closure:latest` (`sha256:55bc923e...`), con las dos rutas crudas ya localizadas. Destino de artefactos **deliberadamente separado** de la campaña cerrada — nunca `/home/gus/scientific-closure-runtime/evidence/{A,B,C}` ni `openspec/scientific-closure/`:

```
# Todo dentro de la imagen exacta de la campaña; solo lectura de las rutas
# crudas ya verificadas; salida a un árbol nuevo, nunca al de la campaña cerrada.
docker run --rm \
  -v "C:/Repo/AAI_Hydric_Stress_external_data/raw:/data/raw:ro" \
  -v "<runtime-nuevo>/ensemble-hito2-preparation-<fecha>:/workspace/output" \
  experiment-v4-scientific-closure:latest \
  python -m experiment_runner.controlled_daily_v4.cli \
    --stage A --input-mode scientific \
    --era5-csv /data/raw/pergamino_era5land_soil_hourly_2015_2025.csv \
    --nasa-power-csv /data/raw/pergamino_nasa_power_daily_2015_2025.csv \
    --output-dir /workspace/output/logistic_regression
    # (repetir con la config de cada familia una vez resuelto 6.1;
    #  agregar el paso de calibración, hoy inexistente en el runner,
    #  una vez resuelto 6.2 -- ninguno de los dos flags existe todavía)
```

Después del refit (si autorizado): empaquetar con `attach_feature_names` (`src/predictive_modeling/bundle_packaging.py`, sin cambios) + el patrón de `write_single_bundle` de Hito 1, destino `bundle_root/<sitio-demo>/horizon_3/ensemble/<familia>/` — un `bundle_root` de demostración, nunca el de producción ni el de un sensor real reservado. Verificar carga/inferencia con `load_ensemble_bundle`/`predict_ensemble_bundle` (sin modificar), y un smoke test HTTP real contra `POST /api/v2/sensors/{sensor_id}/forecasts` con un `sensor_id` de demostración explícito (nunca uno productivo). Pruebas de aceptación: mismo patrón que `tests/test_ensemble_bundle_real_families.py` y `backend/tests/test_producer_v2_ensemble.py`, pero sin ningún dato sintético, corridas dentro de la misma imagen verificada (para que `capture_environment()` coincida en cada paso).

### 6.6 Criterio para declarar el ensamble real habilitado (+3)

Los cinco, todos verificados, no solo alguno:

1. Las 3 familias tienen modelo + calibrador reales, empaquetados, con hashes registrados y procedencia documentada (commit, imagen, config, datos, comandos).
2. `load_ensemble_bundle`/`predict_ensemble_bundle` cargan e infieren correctamente sobre el bundle real, dentro del mismo entorno verificado.
3. Un smoke test HTTP real contra la API v2, con un sensor de demostración explícito, devuelve un detalle `ensemble` coherente.
4. Las decisiones 6.1 y 6.2 están resueltas y **registradas explícitamente** por el responsable (análogo a GD-38/GD-40, pero como una decisión nueva de Hito 2 — nunca reescribiendo esas).
5. El documento resultante distingue, para cada componente, qué es reutilización de la campaña real (identidad heredada) y qué es nuevo (refit de familias no ganadoras, calibración) — nunca presentado como si todo viniera de la misma auditoría `PASS`/`FAIL` ya cerrada.

**Ninguno de los cinco se cumple hoy.** No se declara habilitado el ensamble real.

## 7. Umbrales y demostración histórica (sin cambios respecto de la versión anterior)

- `decision_threshold = 0.5`, comparador `>=`, sin optimizar — confirmado también como el umbral fijo de la campaña real (nunca ajustado contra evaluación/holdout).
- Particiones ya definidas por el protocolo real: A = 2015–2022, B = 2023, C = 2024–2025 (holdout, cerrado). No se alteran; la propuesta de la sección 6.4 reutiliza sub-rangos de A/B explícitamente, nunca C.
- Cualquier demostración histórica futura debe ser causalmente válida y no debe tocar `replay_packages/` ni el paquete `base-seed4` custodiado.

## 8. Los cuatro estados (referencia)

Definidos en `docs/superpowers/specs/2026-09-25-ensemble-operational-integration-design.md`, sección 1:

1. Single-model disponible (sin cambios).
2. Ensemble configurado pero `unavailable` (artefactos incompletos/inválidos/ausentes).
3. Integración probada con datos sintéticos (Hito 1 — alcanzado, PR #217 mergeado).
4. Ensemble habilitado con artefactos reales admisibles — **no alcanzado**. Bloqueado en los tres horizontes (sección 5); para +3, condicionado a una decisión explícita del responsable sobre las dos cuestiones de la sección 6, no solo a disponibilidad de datos/entorno.

## 9. Trazabilidad

- **HU:** HU7 (`experiment-runner`, `controlled_daily_v4_external_pergamino`, campaña real 2026-09-21, cierre `FAIL` de gobernanza) + `predictive-modeling` (contrato operativo del ensamble, Hito 1, PR #217).
- **Impacto en configuración experimental:** ninguno — este documento no ejecuta ningún experimento ni reabre el holdout.
- **Impacto en hipótesis/alcance/arquitectura:** ninguno. No se propone reejecutar B/C, no se propone ampliar el protocolo a nuevos horizontes, no se decide por cuenta propia si completar las familias faltantes o agregar calibración es admisible.
- **Fuentes citadas:** `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`, `docs/research/scientific-closure-synthesis-2026-09-22.md`, `docs/adr/0010-seleccion-modelos-controlled-daily-v4.md`, `docs/adr/0011-protocolo-controlled-daily-v4-external-pergamino.md`, `openspec/scientific-closure/decisions.md` (GD-38, GD-40), `openspec/scientific-closure/README.md`, `openspec/scientific-closure/changes.json`, `openspec/scientific-closure/closure-verification-2026-09-20/claim-evidence-review.json`, `src/experiment_runner/controlled_daily_v4/{stage_a_runner.py,freezing.py,features.py,config.py,cli.py,provenance.py}`, `docker/experiment-v4/Dockerfile`, y las verificaciones de esta intervención: `sha256sum` de los dos CSV crudos, `--validate-inputs-only` (host y dentro de `experiment-v4-scientific-closure:latest`), y `ls` de nombres de archivo (sin lectura de contenido) en `/home/gus/scientific-closure-runtime/evidence/{A,B,C}` vía WSL Ubuntu.
