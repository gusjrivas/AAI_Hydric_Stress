# Spec delta: experiment-runner (contrato A→B, baselines, marcado científico/sintético y de profundidad)

> Estado de este delta (actualizado 2026-09-13): los dos primeros requirements
> ("Lectura y validación estructural del contrato de transferencia A→B" y
> "Admisibilidad de un candidato congelado para una ejecución concreta", más el
> requirement de "Compatibilidad de procedencia entre etapas" en su parte
> aplicable a la Etapa B) están **implementados e integrados** (`transfer_contract.py`,
> `admissibility.py`, extensión de `artifacts.py`/`config.py`/`cli.py`) y
> verificados exclusivamente con pruebas sintéticas. Los requirements de
> "Baselines del protocolo" y "Distinción verificable entre corrida principal y
> de sensibilidad" (más la parte de compatibilidad de procedencia específica de
> la Etapa C) siguen **sin implementar**. Complementa, sin duplicar, el delta ya
> mergeado en `openspec/changes/add-controlled-daily-v4-external-pergamino/specs/experiment-runner/spec.md`,
> que ya especifica los escenarios "Compuerta real de validación temporal antes
> de abrir el holdout" (Etapa B) y "El holdout no admite ajustes posteriores a
> su apertura" (Etapa C) -- esos dos escenarios (los runners de B/C en sí)
> siguen sin implementar. No reemplaza ni modifica ningún requirement vigente
> de `controlled_daily_v3` ni de la Etapa A ya implementada.

## ADDED Requirements

### Requirement: Lectura y validación estructural del contrato de transferencia A→B

El sistema DEBE poder reconstruir, a partir de los artefactos serializados por una corrida de la Etapa A, el candidato congelado (familia, hiperparámetros, `P20_train` final) sin volver a ejecutar la selección de la Etapa A. Esta operación es exclusivamente estructural: verifica que el artefacto tiene la forma esperada, no si es admisible para una ejecución concreta (ver el requirement siguiente, "Admisibilidad de un candidato congelado para una ejecución concreta"). Debe funcionar de manera idéntica sobre un artefacto sintético o uno científico.

#### Scenario: Round-trip de `frozen_config.json`

- **GIVEN** un `frozen_config.json` producido por una corrida (sintética o científica) de la Etapa A
- **WHEN** se lee con la función de carga del contrato de transferencia
- **THEN** se reconstruye una configuración congelada estructuralmente idéntica a la que produjo ese artefacto (misma familia, mismos hiperparámetros, mismo `P20_train`), sin evaluar todavía si esa configuración es admisible para ninguna ejecución concreta

#### Scenario: El artefacto de congelamiento declara su modo y su rol de profundidad

- **GIVEN** un `frozen_config.json` producido con `--input-mode synthetic` o con `--depth sensitivity`
- **WHEN** se lee con la función de carga del contrato de transferencia
- **THEN** el objeto reconstruido expone `input_mode`, `scientific_run` y `depth_role` explícitamente, sin requerir inspeccionar otro archivo del mismo directorio para saberlo — la lectura estructural expone esos campos; no decide todavía si permiten continuar (eso corresponde al requirement de admisibilidad)

#### Scenario: Un lector rechaza un esquema de artefacto no reconocido

- **GIVEN** un `frozen_config.json` cuyo `schema_version` no está entre los soportados por el lector
- **WHEN** se intenta reconstruir la configuración congelada
- **THEN** la carga falla explícitamente, en lugar de asumir una forma de artefacto no verificada — este es un fallo estructural, previo a cualquier chequeo de admisibilidad

### Requirement: Admisibilidad de un candidato congelado para una ejecución concreta

El sistema DEBE decidir, en el punto de consumo (el momento en que una etapa posterior intenta usar un candidato ya leído estructuralmente), si ese candidato es admisible para el modo de la ejecución que lo consume. Esta decisión es distinta e independiente de la lectura estructural del requirement anterior: un artefacto puede leerse correctamente y aun así resultar inadmisible. La admisibilidad científica distingue tres verificaciones que no deben confundirse: **identidad** (qué artefacto concreto es — un valor de `dataset_fingerprint`, un SHA de commit), **integridad** (que ese valor autorreportado por el productor esté presente, sea internamente consistente y no esté corrupto ni marcado como inválido) y **compatibilidad** (una relación documentada entre la identidad del productor y la del consumidor, que no siempre es una igualdad — ver el requirement "Compatibilidad de procedencia entre etapas").

#### Scenario: Un flujo de integración sintético admite artefactos sintéticos

- **GIVEN** un `frozen_config.json` con `scientific_run=false`, y una ejecución de prueba de integración con un modo de entrada también sintético, usando su propio registro de estado aislado del científico
- **WHEN** se evalúa la admisibilidad de ese candidato para esa ejecución
- **THEN** se admite — el flujo sintético A→B→C completo debe poder probarse de punta a punta con artefactos explícitamente sintéticos en ambos extremos, sin requerir nunca una corrida científica real ni tocar ningún registro de estado científico

#### Scenario: Una ejecución científica rechaza antecedentes sintéticos o con integridad no verificable

- **GIVEN** un `frozen_config.json` con `scientific_run=false`, o cuyo `code_version.json` no reporta un commit del productor (ausente o marcado como inválido), o cuya compatibilidad de procedencia con la ejecución consumidora no se verifica (ver el requirement siguiente), y una ejecución en modo científico
- **WHEN** se evalúa la admisibilidad de ese candidato
- **THEN** se rechaza explícitamente, sin proceder a reentrenar ni evaluar ningún modelo

#### Scenario: `scientific_run=true` por sí solo no basta para una ejecución científica

- **GIVEN** un `frozen_config.json` con `scientific_run=true`, consumido por una ejecución en modo científico
- **WHEN** se evalúa su admisibilidad
- **THEN** además de esa bandera se verifican, reutilizando los mecanismos ya existentes y sin duplicarlos: la integridad del autorreporte de identidad de código del productor (`code_identity`/`code_version.json` — commit presente, no marcado como inválido, árbol limpio); la consistencia interna entre los propios artefactos del productor (`frozen_config.json` vs. `code_version.json` del mismo directorio, misma corrida); y la compatibilidad de procedencia con la ejecución consumidora, según la política del requirement "Compatibilidad de procedencia entre etapas" — un candidato que falle cualquiera de esos contrastes se rechaza igual que si `scientific_run` fuera `false`. **Corrección (revisión externa 2026-09-13):** la compatibilidad de procedencia SÍ compara explícitamente el commit de la ejecución consumidora contra el commit histórico del productor, recibido como contexto explícito de la ejecución consumidora — ambos commits pueden coincidir (caso normal) o diferir (por ejemplo, tras una corrección posterior a A); si difieren y no existe una política de compatibilidad documentada que acredite esa diferencia, la admisibilidad se rechaza explícitamente por "compatibilidad no acreditada". Esta comparación productor-consumidor es distinta e independiente de la consistencia interna del productor consigo mismo, y ninguna de las dos sustituye a la otra.

#### Scenario: La restricción de profundidad se aplica en el punto de consumo, no en la lectura, y su rechazo es siempre un error duro

- **GIVEN** un `frozen_config.json` estructuralmente válido cuyo `depth_role` es `sensitivity_only_no_selection_effect`
- **WHEN** la Etapa B intenta consumirlo para congelar un modelo
- **THEN** la admisibilidad se rechaza en ese punto de consumo, siempre como error duro (nunca como advertencia que permita continuar) — la lectura estructural del requirement anterior no rechaza este artefacto por sí sola, y esta restricción no impide leerlo estructuralmente ni crea una ruta de experimento paralela para la profundidad de sensibilidad; únicamente bloquea su uso como insumo de la Etapa B

### Requirement: Compatibilidad de procedencia entre etapas

El sistema DEBE distinguir cuatro nociones al verificar la procedencia de un candidato consumido por una etapa posterior: (1) la identidad y evidencia persistida por el productor A (su propio commit, `dirty`, `dataset_fingerprint` y entorno, capturados en el momento de A); (2) la identidad y el entorno de la ejecución consumidora, capturados por ella misma; (3) la huella del conjunto derivado que A usó para entrenar y congelar; y (4) la huella del conjunto sobre el que la etapa posterior efectivamente reentrena. La política de compatibilidad entre (3) y (4) NO es una igualdad genérica: depende de si la etapa posterior reentrena sobre el mismo período que A o sobre un período extendido.

#### Scenario: La Etapa B exige igualdad de huella porque reentrena sobre el mismo período que A

- **GIVEN** un candidato congelado por A sobre `target_timestamp ≤ 2022-12-31`, y una ejecución de la Etapa B que reentrena con el mismo corte
- **WHEN** se compara la huella (4) del conjunto de reentrenamiento de B contra la huella (3) registrada por A
- **THEN** se exige igualdad exacta — cualquier diferencia se rechaza, porque el protocolo especifica el mismo período de entrenamiento para ambas

#### Scenario: La Etapa C no exige igualdad de huella porque incorpora 2023 y recalcula `P20_train`

- **GIVEN** un candidato congelado por A sobre `target_timestamp ≤ 2022-12-31`, y una ejecución de la Etapa C que reentrena con `target_timestamp ≤ 2023-12-31` (protocolo, sección 11)
- **WHEN** se evalúa la compatibilidad del conjunto de reentrenamiento de C contra la procedencia de A
- **THEN** NO se exige que la huella (4) de C sea igual a la huella (3) de A — en cambio, se verifica que el conjunto de C proviene de la misma identidad de fuente/provenance que A (mismos CSV identificados, mismo sitio, mismas variables, mecanismo de H-01 reutilizado) y que su período es la extensión causal exacta prevista por el protocolo (superset que agrega 2023 según `STAGE_C_BOUNDS`) — una relación de compatibilidad distinta de la igualdad, no una excepción arbitraria a ella

### Requirement: Baselines del protocolo disponibles para las Etapas A, B y C

El sistema DEBE poder calcular, sobre cualquier período autorizado de cualquier etapa, los tres baselines de la sección 13 del protocolo, cada uno con su propia regla de acceso a datos — ninguno ajusta su regla usando etiquetas del conjunto de evaluación, pero el acceso a las etiquetas del `train` autorizado es legítimo y necesario para el baseline de clase mayoritaria.

#### Scenario: La clase mayoritaria aprende exclusivamente de las etiquetas del train autorizado

- **GIVEN** el conjunto `train` autorizado de un fold/etapa, con sus etiquetas conocidas
- **WHEN** se construye el baseline de clase mayoritaria
- **THEN** predice el `argmax` del conteo de esas etiquetas de `train` — este acceso a las etiquetas de entrenamiento es legítimo y requerido, no una fuga

#### Scenario: La persistencia causal usa el valor actual, nunca la humedad futura de la fila evaluada

- **GIVEN** un `P20_train` y una fila con `soil_moisture(feature_timestamp)` conocida
- **WHEN** se aplica el baseline de persistencia causal a esa fila
- **THEN** la predicción depende exclusivamente de `soil_moisture(feature_timestamp)` frente a `P20_train`, nunca de `soil_moisture(feature_timestamp + horizonte)` de esa misma fila

#### Scenario: El predictor constante de estrés no aprende de ningún conjunto

- **GIVEN** cualquier conjunto de evaluación
- **WHEN** se aplica el baseline constante de estrés
- **THEN** predice `1` para toda fila, sin ajustar ningún parámetro a partir de etiquetas de entrenamiento ni de evaluación

#### Scenario: Ningún baseline ajusta su regla con etiquetas del conjunto de evaluación

- **GIVEN** cualquiera de los tres baselines, ya fijado sobre el `train` autorizado de un fold/etapa (o sin ajuste, en el caso del constante)
- **WHEN** se aplica sobre el conjunto de evaluación de ese fold/etapa
- **THEN** la regla aplicada es exactamente la fijada con `train` (o la regla fija del baseline constante) — ninguna etiqueta del conjunto de evaluación interviene en su cálculo

#### Scenario: La persistencia causal es el baseline formal de la compuerta de la Etapa B

- **GIVEN** las predicciones del candidato congelado sobre 2023 y las del baseline de persistencia causal sobre el mismo período
- **WHEN** se calcula `ΔMCC_B`
- **THEN** el sustraendo es exactamente el MCC de la persistencia causal sobre 2023, ningún otro baseline

### Requirement: Distinción verificable entre corrida principal y de sensibilidad

El sistema DEBE dejar registrado, en los artefactos de cada corrida, si la profundidad analizada es la principal (0–7 cm) o la de sensibilidad (7–28 cm). El rechazo de un candidato de sensibilidad como insumo de la Etapa B está especificado en el requirement anterior ("Admisibilidad de un candidato congelado para una ejecución concreta", escenario "La restricción de profundidad se aplica en el punto de consumo") y no se repite aquí.

#### Scenario: Una corrida de sensibilidad queda marcada como tal

- **GIVEN** una ejecución de la Etapa A con `--depth sensitivity`
- **WHEN** se inspeccionan sus artefactos de salida
- **THEN** `depth_role` queda registrado como `sensitivity_only_no_selection_effect`, distinto del valor `primary_selection` de una corrida principal

## Fuera de alcance de este delta

Los escenarios de la compuerta de la Etapa B (`ΔMCC_B`, `CANDIDATE_VALIDATED`/`CANDIDATE_NOT_VALIDATED`) y de la irreversibilidad de la Etapa C ya están especificados en `add-controlled-daily-v4-external-pergamino/specs/experiment-runner/spec.md` y no se repiten aquí. Las Decisiones 1, 2 y 3 de `docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md` (segmentación del bootstrap de B; identidad del holdout, secuencia de apertura y granularidad del registro de intento de C; política de `--overwrite` de C) no se resuelven ni se anticipan en este delta. La Decisión 4 de ese mismo documento (ubicación exacta de `depth_role`) tampoco se resuelve aquí, pero no bloquea los escenarios de admisibilidad anteriores en su totalidad — la existencia del campo, su punto de verificación y la severidad de su rechazo (siempre error duro) ya están resueltos; solo su ubicación exacta permanece abierta.
