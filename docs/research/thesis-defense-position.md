# Posición para la tesis y la defensa

## Tesis central defendible

El trabajo demuestra que es posible construir e integrar, con trazabilidad
temporal y reproducibilidad, un sistema de apoyo a la decisión para anticipar
un proxy de baja humedad de suelo a tres días. La contribución principal es la
arquitectura de IA, su integración y una evaluación crítica que conserva tanto
los resultados favorables como los negativos y las desviaciones metodológicas.

## Contribuciones

- Pipeline reproducible de ingestión, calidad, modelado, alertas y feedback.
- Comparación temporal de cuatro familias y selección por una regla
  predeclarada de simplicidad cuando no apareció un ganador estable.
- Evaluación en una segunda fuente agroclimática y análisis de episodios,
  calibración, falsos avisos y deriva de prevalencia.
- Complemento H ejecutado en dos pistas: una simulada, con correcciones,
  recalibración y efectos mixtos, y otra humana controlada, limitada a veinte
  aceptaciones sin correcciones ni recalibración; ninguna acredita beneficio
  humano.
- Gobernanza que documenta limitaciones y una no conformidad en vez de ocultarla.

## Resultados que sí pueden presentarse

- A terminó en `SIN_GANADOR_ESTABLE`; el modelo se fijó por desempate
  predeclarado, no por superioridad.
- B mostró no inferioridad frente a persistencia y C produjo una diferencia
  favorable en MCC, ambos como evidencia retrospectiva exploratoria.
- La pista simulada de H verificó corrección/recalibración con efectos de signo
  mixto. La pista humana controlada terminó en `NO_RECALIBRATION`: veinte
  aceptaciones, cero correcciones y detección 0/4 de los errores determinables,
  limitada a ese ejercicio y sin demostrar beneficio humano.
- Los resultados numéricos son reales y fueron recomputados; la secuencia de
  auditoría entre gates no satisfizo el protocolo predeclarado.

## Tres carriles de evidencia que no deben mezclarse

| Carril | Qué existe | Qué puede afirmarse | Límite obligatorio | Fuentes primarias |
| --- | --- | --- | --- | --- |
| **Melchor Romero — `controlled_daily_v3`** | Evidencia formal histórica sobre ocho configuraciones y cinco semillas, con horizonte t+3, dataset `melchor_romero_2024_consolidado` y resultados preservados | Permite describir el comportamiento comparativo histórico dentro de ese diseño: por ejemplo, `recent_fraction_0.5` tuvo las mayores medias de F1/MCC/AP de la tabla formal; sintéticos y anomalías tuvieron aportes mixtos | No es evidencia v4, no se extrapola a Pergamino y debe declararse la imputación causal de huecos de humedad. No prueba detección de anomalías reales, robustez general ni superioridad universal | `docs/research/reference-v3-formal-table.md`; `docs/research/reference-v3-formal-results.json`; `docs/research/hu8-resultados-discusion-conclusiones.md` §8 |
| **Pergamino — `controlled_daily_v4` A/B/C/H** | A terminó en `SIN_GANADOR_ESTABLE`; B observó no inferioridad; C produjo una diferencia favorable en MCC; H tuvo una pista simulada y otra humana controlada | Los valores numéricos se conservan y pueden presentarse con soporte, calibración, falsos avisos y demás limitaciones. En H, la pista simulada produjo correcciones y recalibración con efectos mixtos; la humana registró 20 aceptaciones, cero correcciones, `NO_RECALIBRATION` y detección 0/4 de errores determinables | B y C son evidencia retrospectiva exploratoria, no confirmatoria; el 0/4 humano se limita a ese ejercicio, no acredita beneficio humano ni se generaliza; `GF` y `SC-GOV-025` terminaron en `FAIL` | `docs/research/scientific-closure-synthesis-2026-09-22.md` §6; `openspec/scientific-closure/traceability.md`; GD-38/GD-40 |
| **Ensamble demostrativo de Pergamino** | Refit técnico propio de tres familias para +1/+2/+3: nueve modelos y nueve calibradores, tres manifests y verificación HTTP real | Demuestra que el contrato operativo del ensamble puede empaquetarse, cargarse e inferir en los tres horizontes con los datos permitidos de Pergamino | Tiene identidad, ventanas, calibración y contrato de features propios. Los CSV completos se cargan transitoriamente; 2024–2025 se excluye antes de agregación, cálculo del umbral, features y targets, y no se usa para entrenamiento, calibración ni demo. Esta garantía del runner es distinta de no reabrir la evaluación del holdout custodiado. No reutiliza artefactos ajustados de v4, no reejecuta A/B/C y no aporta evidencia confirmatoria | `docs/design/ensemble-real-execution-report-2026-09-26.md` §§6–9; `src/experiment_runner/pergamino_ensemble_demo_runner.py:40-50,280-325,354-475` |

La separación entre carriles es parte del argumento científico: que dos carriles
usen Pergamino o compartan constructores de modelos no los convierte en la misma
campaña, el mismo contrato ni la misma clase de evidencia.

## Qué significa hoy una alerta del ensamble

La decisión vigente **no es una votación mayoritaria**. Para cada horizonte, el
sistema calcula el promedio aritmético de las tres probabilidades calibradas y
emite `combined_alert = combined_probability >= 0.5`. `positive_votes` cuenta
los componentes que individualmente cruzan el umbral y `agreement_category`
traduce ese conteo a una etiqueta de acuerdo; ambos son metadata descriptiva y
no gobiernan la alerta. El contrato está implementado en
`src/predictive_modeling/ensemble_bundle.py:343-351` y validado nuevamente en
`backend/app/schemas_v2.py:202-243`.

Los tests de discrepancia vuelven observable esta distinción:
`tests/test_ensemble_bundle.py:440-483` prueba tanto dos votos positivos con
alerta combinada negativa como un solo voto positivo con alerta combinada
positiva; `backend/tests/test_producer_v2_ensemble.py:174-216` confirma que la
API y el feedback siguen `combined_alert`, no la categoría de mayoría. Por lo
tanto, adoptar mayoría como política sería un cambio futuro de contrato,
pendiente y **no implementado**; no debe describirse como comportamiento actual.

La probabilidad del ensamble tampoco está habilitada para presentación al
usuario: la emisión persiste `display_probability=None`,
`probability_status=not_qualified` y razón `incompatible_assessment`
(`src/architecture_integration/producer_emission.py:144-178`). El campo
`combined_probability` existe para el contrato técnico y la decisión binaria;
no debe mostrarse ni narrarse como riesgo calibrado para el productor.

## Dos circuitos de feedback distintos

| Circuito | Qué hace | Qué no hace | Fuente primaria |
| --- | --- | --- | --- |
| **Review API v2 del pronóstico** | `POST /api/v2/sensors/{sensor_id}/forecasts/{forecast_id}/reviews` registra `confirm`/`reject`, revisión y comentario. En modo ensamble, el `alert` superior está obligado a coincidir con `ensemble.combined_alert`; la opinión se refiere a esa decisión binaria | No cambia los nueve bundles ni recalibra automáticamente. Sin revisión corresponde `no_review`; antes de la madurez, `waiting_target_maturity`; y una revisión no madura exige `requires_mature_revalidation`. Ya madura, una confirmación es `confirmation_only`; sólo una corrección `reject` madura del ensamble resulta `incompatible_source_model` por carecer de una única `calibration_version`. `applied` no se alcanza en este repositorio | `backend/app/routers/producer_v2.py:365-385`; `src/human_feedback/operational_repository.py:144-148,798-843` |
| **Review del recorrido histórico** | Registra una prueba técnica bajo reloj simulado y en un store separado del review operativo | No es opinión real de productor/experto, no modifica bundles y no dispara recalibración. Los tests verifican hashes idénticos antes/después y aislamiento entre ambos stores | `backend/app/routers/producer_v2.py:416-425,557-610`; `src/human_feedback/historical_review_store.py`; `backend/tests/test_pergamino_ensemble_historical_reproduction.py:208-243,392-437` |
| **Recalibración legacy/HU5** | `POST /recalibrate/{sensor_id}` carga el log HU5, selecciona correcciones rechazadas maduras, refitea un predictor y registra un sucesor con linaje | Es un circuito manual de **un solo modelo**; no consume el review histórico del ensamble ni recalibra sus tres componentes/nueve bundles como conjunto | `backend/app/routers/recalibration.py:34-113`; `src/human_feedback/recalibration.py:51-125`; `openspec/specs/human-feedback/spec.md` |

El complemento científico H es otra cosa y tuvo dos pistas. La simulada evaluó
correcciones y recalibración bajo el diseño predeclarado, con efectos mixtos. La
humana controlada registró veinte aceptaciones, ninguna corrección,
`NO_RECALIBRATION` y detección 0/4 de los errores determinables. Ese resultado
queda limitado al ejercicio y no se atribuye como beneficio humano ni se
generaliza; ninguna pista convierte estos circuitos en evidencia de mejora
causada por feedback humano real.

## Limitación en una frase

Cada carril o evaluación corresponde a un solo sitio: v3 a Melchor Romero y
v4/ensamble demostrativo a Pergamino. El conjunto no constituye validación
multisitio ni agronómica longitudinal; además, B y C no son confirmatorias por
la desviación cronológica de gates y no hubo evaluación con usuarios finales.

## Afirmaciones prohibidas

- Superioridad general de IA o del modelo elegido.
- Confirmación de la hipótesis mediante B o C.
- Validación agronómica, ahorro de agua o estrés fisiológico medido.
- Mejora causada por feedback humano.
- Generalización geográfica u operación productiva demostradas.
- Robustez ante sensores ausentes, detección reservada de corrupciones o error
  continuo de humedad, que no se evaluaron en esta campaña.

## Estructura sugerida de defensa

1. Problema y alcance: apoyo a la decisión, no automatización del riego.
2. Arquitectura y contribución de IA.
3. Diseño temporal, baselines y criterios predeclarados.
4. Resultados A, B, C y H, separando hechos de inferencias.
5. Limitaciones y no conformidad de gates.
6. Contribuciones que permanecen válidas y trabajo futuro.

## Preguntas difíciles y respuestas honestas

**¿La hipótesis quedó confirmada?** No de manera confirmatoria. A no encontró un
ganador estable; B y C aportan evidencia exploratoria útil, pero la secuencia de
auditoría de gates no cumplió el protocolo predeclarado.

**¿Entonces el experimento fracasó?** No. Produjo resultados reproducibles,
incluido un resultado negativo en selección, y permitió cuantificar desempeño,
calibración, falsos avisos y límites. Lo que no corresponde es elevarlo a
confirmación.

**¿Por qué no repetirlo desde otra rama?** Porque cambiar de rama no recupera
cegamiento: el holdout ya fue observado. Una confirmación exigiría datos nuevos.

**¿Qué aporta el HITL?** La pista simulada acredita el mecanismo técnico de
corrección/recalibración, con efectos mixtos. La pista humana controlada sólo
acredita ese ejercicio: 20 aceptaciones, cero correcciones, `NO_RECALIBRATION` y
0/4 errores determinables detectados. No demuestra beneficio humano ni permite
generalizar la tasa observada.

**¿La alerta del ensamble sale por mayoría?** No. Sale del promedio aritmético
de tres probabilidades comparado con 0,5. Los votos y la categoría de acuerdo
son metadata; una política de mayoría sería trabajo futuro.

**¿Confirmar o rechazar una alerta recalibra el ensamble?** No. El review v2 o
histórico registra la opinión sobre `combined_alert`; no modifica los nueve
bundles. La recalibración manual HU5 es un endpoint legacy separado y opera
sobre un único predictor.

**¿Qué hace que el trabajo sea una tesis de IA?** La formulación predictiva,
comparación de modelos, control temporal, análisis de incertidumbre e integración
del ciclo de feedback; los sensores son fuentes de datos, no la contribución
central.
