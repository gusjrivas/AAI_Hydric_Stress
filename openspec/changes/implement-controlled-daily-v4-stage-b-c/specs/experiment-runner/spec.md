# Spec delta: experiment-runner (contrato A→B, baselines, marcado científico/sintético y de profundidad, ledger y runner de la Etapa C)

> Estado de este delta (actualizado 2026-09-15): el contrato de transferencia
> A→B (lectura estructural y admisibilidad de una ejecución concreta, más la
> parte de "Compatibilidad de procedencia entre etapas" aplicable a la Etapa B)
> sigue **implementado e integrado** (`transfer_contract.py`, `admissibility.py`,
> extensión de `artifacts.py`/`config.py`/`cli.py`). El requirement de
> "Baselines del protocolo", el escenario "Compuerta real de validación
> temporal antes de abrir el holdout" (Etapa B, ya especificado en
> `add-controlled-daily-v4-external-pergamino/specs/experiment-runner/spec.md`),
> el requirement "Distinción verificable entre corrida principal y de
> sensibilidad", y la parte de "Compatibilidad de procedencia entre etapas"
> aplicable a la Etapa B siguen **implementados e integrados**
> (`baselines.py`, `stage_b_runner.py` — `--stage B` operativo).
>
> **Nuevo en este cierre (2026-09-15, encargo "Etapa C y ledger de protección
> del holdout"):** el ledger transaccional de protección del holdout
> (`holdout_ledger.py`), la admisibilidad de C sobre el veredicto de B
> (`admissibility.check_stage_c_admissibility`), el runner de la Etapa C
> (`stage_c_runner.py`), sus artefactos exclusivos (`artifacts.write_stage_c_artifacts`)
> y `--stage C` en la CLI quedan **implementados e integrados en este cierre**,
> verificados exclusivamente con pruebas sintéticas -- ver los requirements
> "Ledger de protección del holdout de la Etapa C" y "Runner y evaluación
> única de la Etapa C" agregados más abajo, y el escenario "El holdout no
> admite ajustes posteriores a su apertura" (ya especificado en
> `add-controlled-daily-v4-external-pergamino/specs/experiment-runner/spec.md`),
> ahora con implementación real que lo satisface. La parte de "Compatibilidad
> de procedencia entre etapas" específica de la Etapa C también queda
> implementada (`cli.py::_run_stage_c`, verificación de identidad de fuente
> DESPUÉS de la apertura confirmada del holdout). Las Decisiones 2 y 3 del
> documento de decisiones pendientes fueron adoptadas como decisiones
> operativas de este encargo (no atribuidas a una aprobación académica
> externa; ver `docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md`).
>
> No reemplaza ni modifica ningún requirement vigente de `controlled_daily_v3`
> ni de las Etapas A/B ya implementadas. **Ninguna ejecución científica real
> de ninguna etapa, ni apertura real del holdout 2024-2025, se realizó en
> este cierre** -- toda verificación es exclusivamente sintética, y la
> integración a `main` queda pendiente mientras el PR correspondiente esté
> abierto.
>
> **Revisión dirigida sobre este mismo cierre (2026-09-15), cinco hallazgos
> corregidos con evidencia sintética verificable, sin reabrir la Decisión 4
> (`depth_role`):** (1) `check_stage_c_admissibility` ahora valida
> ESTRUCTURALMENTE los artefactos de B antes de interpretar sus valores --
> rechaza booleanos como métrica (`bool` es subclase de `int` en Python),
> valores no finitos, un intervalo bootstrap invertido, réplicas bootstrap
> válidas insuficientes (`diagnostics.replicas_valid`), y una incoherencia
> interna entre `input_mode` y `scientific_run` de la propia corrida de B.
> (2) la recuperación de solo lectura de un resultado finalizado
> (`artifacts.verify_stage_c_recovery`) exige un `integrity_manifest.json`
> con el sha256 de cada artefacto realmente escrito y la correspondencia de
> `holdout_identity_key`/`attempt_id`, escrito como ÚLTIMO artefacto de
> `write_stage_c_artifacts` -- nunca declara éxito sobre un directorio
> ausente, un artefacto faltante, contenido alterado, o evidencia de otro
> intento. (3) la CLI rechaza, ANTES de reservar el ledger, una salida ya
> ocupada, una `--authorized-by` vacía, y una invocación científica con
> semilla/réplicas no normativas (antes solo se detectaban, respectivamente,
> dentro de `write_stage_c_artifacts`, dentro de `confirm_holdout_open`, o
> nunca). (4) la validación de esquema/metadatos del ledger
> (`holdout_ledger._validate_ledger_meta`) ahora es una única función
> reutilizada en lectura, reserva, confirmación y finalización: un
> `schema_version` o `mode` desconocido nunca habilita ninguna de las cuatro
> operaciones; `confirm_holdout_open`/`finalize_holdout` verifican
> explícitamente que el archivo exista (nunca dejan que `sqlite3.connect` cree
> uno vacío implícito); `finalize_holdout` exige el mismo `attempt_id` que
> ganó la reserva y rechaza una segunda finalización en vez de reemplazar en
> silencio la referencia ya persistida. (5) el entrenamiento extendido de C
> se huella con un `scope` propio (`FINGERPRINT_SCOPE_STAGE_C_EXTENDED_TRAINING`,
> nunca el de A/B) y `predictions_2024_2025.csv` incorpora `target_timestamp`
> (esquema de artefactos de C: `controlled_daily_v4_stage_c.v2`).

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

### Requirement: Ledger de protección del holdout de la Etapa C

El sistema DEBE mantener un registro persistente y transaccional que impida, a través del flujo normal de la CLI, que el holdout de 2024-2025 se abra más de una vez para una misma identidad de holdout (protocolo + sitio + profundidad + período — nunca por commit, candidato congelado, `--output-dir` o identificador de intento). El registro DEBE distinguir tres estados (`AUSENTE`, `CONFIRMADA`, `INDETERMINADA`), inicializarse mediante una operación explícita y separada de cualquier ejecución, y nunca crearse ni reinicializarse implícitamente. Es un control operativo del flujo normal de la herramienta, no una garantía criptográfica ni a prueba de manipulación manual deliberada del archivo del registro.

#### Scenario: La identidad del holdout es independiente del intento que lo consulta

- **GIVEN** dos invocaciones de `--stage C` con distinto commit, candidato congelado o `--output-dir`, mismo protocolo/sitio/profundidad/período
- **WHEN** se calcula la identidad de holdout de cada invocación
- **THEN** ambas producen la misma clave: ninguno de esos otros datos puede, ni siquiera cambiándolos, producir una identidad de holdout distinta

#### Scenario: La inicialización del ledger es explícita y nunca reemplaza uno existente

- **GIVEN** un archivo de ledger ya existente en la ruta indicada
- **WHEN** se invoca la operación de inicialización explícita sobre esa misma ruta
- **THEN** la operación se rechaza sin modificar el archivo existente

#### Scenario: Un ledger ausente, corrupto o ilegible se trata como INDETERMINADA, nunca como AUSENTE

- **GIVEN** una ruta de ledger que no existe, o que existe pero no es una base de datos válida, o cuya fila para la identidad de holdout solicitada no está presente o no valida contra su forma esperada
- **WHEN** se consulta el estado de esa identidad de holdout
- **THEN** el estado reportado es `INDETERMINADA` — nunca `AUSENTE` — y bloquea cualquier acceso automático nuevo al holdout

#### Scenario: La reserva es atómica y durable, y precede a cualquier acceso al holdout

- **GIVEN** un registro en estado `AUSENTE`
- **WHEN** se reserva la apertura y, a continuación, se confirma de forma durable (con `fsync` explícito del archivo, y del directorio cuando el mecanismo lo permite)
- **THEN** ningún dato de 2024-2025 se carga ni se evalúa antes de que la confirmación durable haya retornado sin excepción

#### Scenario: Dos reservas concurrentes sobre la misma identidad de holdout — solo una tiene éxito

- **GIVEN** dos procesos del sistema operativo que intentan reservar, al mismo tiempo, la apertura del mismo holdout sobre el mismo archivo de ledger
- **WHEN** ambos ejecutan la operación de reserva
- **THEN** exactamente uno la obtiene y el otro es rechazado de inmediato, sin que ninguno de los dos haya accedido a ningún dato de 2024-2025

#### Scenario: Una interrupción entre la reserva y la confirmación bloquea el acceso sin reintento automático

- **GIVEN** un registro que fue reservado pero cuya confirmación durable nunca se completó (proceso interrumpido)
- **WHEN** se consulta su estado, o se intenta una nueva reserva para la misma identidad de holdout
- **THEN** el estado es `INDETERMINADA`, la nueva reserva se rechaza, y el registro no se borra ni se reinicializa automáticamente

#### Scenario: Un fallo posterior a la confirmación durable no habilita reintentar la evaluación

- **GIVEN** un registro en estado `CONFIRMADA` (la apertura ya se confirmó de forma durable) y un fallo posterior durante la evaluación o la escritura de resultados
- **WHEN** se intenta una nueva invocación de `--stage C` para la misma identidad de holdout
- **THEN** se rechaza de inmediato — el holdout queda protegido de forma permanente, exista o no un resultado serializado, sin ningún mecanismo de reintento automático

#### Scenario: Una ejecución finalizada se recupera por lectura, sin reentrenar ni acceder al holdout crudo

- **GIVEN** un registro en estado `CONFIRMADA` con marca de finalización ya presente, apuntando a un directorio de resultados existente
- **WHEN** se invoca de nuevo `--stage C` para la misma identidad de holdout
- **THEN** se reporta el resultado ya serializado sin reentrenar ningún modelo ni leer de nuevo ningún CSV crudo

#### Scenario: Ledgers sintético y científico están separados y un cruce se rechaza explícitamente

- **GIVEN** un archivo de ledger inicializado con un modo (`synthetic` o `scientific`)
- **WHEN** se lo consulta o se opera sobre él declarando el modo contrario
- **THEN** la operación se rechaza explícitamente, sin degradarse a ningún estado del holdout

#### Scenario: `--overwrite` está prohibido incondicionalmente para la Etapa C

- **GIVEN** una invocación de `--stage C` con `--overwrite`
- **WHEN** la CLI procesa los argumentos
- **THEN** se rechaza antes de cualquier otra verificación, sin excepción — como defensa en profundidad sobre el ledger, no como el único mecanismo de exclusión

### Requirement: Runner y evaluación única de la Etapa C

El sistema DEBE, solo después de que la apertura del holdout haya sido confirmada de forma durable por el ledger, reentrenar exclusivamente el candidato ya congelado por A y aprobado por B (misma familia, mismos hiperparámetros, mismos pesos de combinación) con `target_timestamp <= 2023-12-31`, recalcular `P20_train` exclusivamente sobre ese entrenamiento extendido, y evaluar una única vez `target_timestamp` entre 2024-01-04 y 2025-12-31 — sin selección, tuning, calibración, ajuste de umbrales ni prueba de candidatos alternativos, y sin comparar el `P20_train` recalculado contra el de A/B.

#### Scenario: El entrenamiento de C nunca depende de humedad de 2024-2025

- **GIVEN** una serie diaria con valores de humedad de 2024-2025 arbitrariamente modificados
- **WHEN** se construye el conjunto de entrenamiento autorizado de C
- **THEN** el conjunto resultante es idéntico al que se obtendría sin esa modificación

#### Scenario: C no exige que el `P20_train` recalculado coincida con el de A

- **GIVEN** un candidato congelado por A con un `P20_train` de A/B conocido
- **WHEN** C recalcula `P20_train` sobre su propio entrenamiento extendido (que incorpora 2023)
- **THEN** no se produce ningún fallo aunque ambos valores difieran — a diferencia de B, que sí exige esa igualdad porque reentrena sobre el mismo período que A

#### Scenario: Un resultado desfavorable de C nunca autoriza repetir la evaluación

- **GIVEN** un resultado de la Etapa C ya serializado y finalizado, cualquiera sea su métrica principal
- **WHEN** se considera si corresponde una nueva evaluación
- **THEN** no existe ningún mecanismo de este sistema que permita repetirla para la misma identidad de holdout

#### Scenario: Monoclase y métricas indefinidas se persisten sin fabricar predicciones

- **GIVEN** un entrenamiento o una evaluación de C genuinamente monoclase
- **WHEN** se serializan los artefactos de esa corrida
- **THEN** las predicciones del candidato quedan explícitamente ausentes (nunca fabricadas, nunca ceros en lugar de un valor indefinido), y el motivo queda registrado

## Fuera de alcance de este delta

Los escenarios de la compuerta de la Etapa B (`ΔMCC_B`, `CANDIDATE_VALIDATED`/`CANDIDATE_NOT_VALIDATED`) ya están especificados en `add-controlled-daily-v4-external-pergamino/specs/experiment-runner/spec.md` y no se repiten aquí; el escenario de irreversibilidad de la Etapa C, también especificado allí, queda ahora satisfecho por los requirements "Ledger de protección del holdout de la Etapa C" y "Runner y evaluación única de la Etapa C" de este mismo delta. Las Decisiones 1, 2 y 3 de `docs/research/controlled-daily-v4-stage-b-c-decisiones-pendientes.md` (segmentación del bootstrap de B; identidad del holdout, secuencia de apertura y granularidad del registro de intento de C; política de `--overwrite` de C) fueron todas adoptadas como decisiones operativas de sendos encargos de implementación (Decisión 1: 2026-09-14; Decisiones 2 y 3: 2026-09-15) — ninguna se atribuye a una aprobación académica externa. La Decisión 4 de ese mismo documento (ubicación exacta de `depth_role`) tampoco se resuelve aquí, pero no bloquea ningún escenario de admisibilidad en su totalidad — la existencia del campo, su punto de verificación y la severidad de su rechazo (siempre error duro) ya están resueltos; solo su ubicación exacta permanece abierta. Fuera de alcance también: ejecución científica real de cualquier etapa, apertura real del holdout 2024-2025, Balcarce, e integración con MLflow.
