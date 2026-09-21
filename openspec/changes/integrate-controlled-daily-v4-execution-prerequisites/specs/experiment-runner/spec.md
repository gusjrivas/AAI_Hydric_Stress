# Spec delta: experiment-runner (prerrequisitos de ejecución de controlled_daily_v4)

> Estado de este delta (2026-09-20): los requirements siguientes quedan
> **implementados e integrados**, verificados **exclusivamente con pruebas
> sintéticas**. Ninguna ejecución científica real de las Etapas A, B o C se
> realizó. El holdout 2024–2025 permanece cerrado y el ledger definitivo no
> está inicializado. La existencia de estos mecanismos y de sus fixtures no
> demuestra eficacia real de ningún candidato.

## ADDED Requirements

### Requirement: Contrato de features ejecutable y serializado

El runner DEBE exponer el contrato de features efectivo como dato serializable
(`pergamino_features.v1`) y escribirlo en `resolved_config.json` de las Etapas
A, B y C, y en el contrato congelado de transferencia de la Etapa A. El
contrato DEBE describir las ocho features del protocolo v4, los lags, las
ventanas móviles, la inclusión del valor actual y el horizonte.

El contrato v4 NO DEBE describirse como heredado de `controlled_daily_v3` sin
modificación: son contratos distintos, y una diferencia de desempeño v3→v4 no
identifica por sí sola un efecto de sitio, período o modelo.

#### Scenario: La Etapa B científica rechaza un contrato congelado divergente

- **WHEN** una ejecución científica de la Etapa B lee un contrato congelado cuyo
  `feature_contract` difiere del contrato ejecutable vigente
- **THEN** la ejecución se rechaza antes de leer valores de entrada, entrenar o
  predecir, y el intento no se consume

### Requirement: Pisos de soporte predeclarados para selección y bootstrap

La selección DEBE exigir al menos **dos** folds con MCC definido de los tres
previstos, y al menos el **80 %** de réplicas bootstrap válidas. Estos pisos
son predeclarados y no DEBEN relajarse para obtener un resultado favorable.

Si una familia no satisface el soporte de folds, la Etapa A DEBE terminar en
`NO_VALID_SELECTION`, sin candidato transferible, conservando los diagnósticos
de los folds ya evaluados. La compuerta de la Etapa C DEBE aplicar el mismo
piso de réplicas válidas que el propio bootstrap, para que B y C no discrepen.

#### Scenario: Soporte de réplicas insuficiente

- **WHEN** el bootstrap pareado produce menos del 80 % de réplicas válidas
- **THEN** no se reporta intervalo, se conservan los diagnósticos con
  `replicas_valid`, `discarded_fraction` y `support_sufficient`, y la Etapa C no
  se admite sobre ese resultado

### Requirement: Métricas indefinidas y evaluaciones monoclase

El MCC DEBE ser indefinido cuando la verdad **o** la predicción es constante.
La exactitud balanceada DEBE ser indefinida con verdad monoclase. Toda métrica
indefinida DEBE serializarse como `null` acompañada de estado, razón y soporte
— nunca como `NaN` ni como un cero sustituto.

Las evaluaciones monoclase de las Etapas B y C DEBEN conservar sus predicciones
y las métricas que sí son definibles, y NO DEBEN registrar el resultado de un
procedimiento que no se ejecutó: si el bootstrap no se intenta por evaluación
monoclase, no se acumula una razón de bootstrap sin réplicas válidas. Una Etapa
B monoclase NO DEBE abrir la Etapa C.

#### Scenario: Evaluación monoclase en la Etapa B

- **WHEN** el período evaluable de la Etapa B resulta monoclase
- **THEN** se persisten las predicciones y las métricas definibles, el bootstrap
  no se ejecuta ni se reporta como fallido, se registra la razón de la evaluación
  monoclase, y el veredicto no habilita la Etapa C

### Requirement: Métricas de inicio de episodio

El runner DEBE calcular métricas descriptivas de inicio de episodio sobre la
fecha objetivo `t+3`, distinguiendo anticipación, detección en el día de inicio,
detección tardía y omisión, y reportando días de anticipación, falsos avisos
(días y rachas) y soporte.

Los episodios cuyo inicio coincide con el comienzo de un segmento o con un
hueco de calendario DEBEN censurarse **por izquierda** y NO DEBEN entrar en el
denominador. Estas métricas miden cobertura y anticipación descriptiva; NO
DEBEN interpretarse como evidencia de eficacia operativa.

#### Scenario: Episodio censurado por izquierda

- **WHEN** un episodio comienza en la primera fila de un segmento o inmediatamente
  después de un hueco de calendario
- **THEN** se cuenta como censurado y se excluye del denominador de anticipación

### Requirement: Custodia del primer intento científico de la Etapa B

Una ejecución científica de la Etapa B DEBE reservar el intento en un registro
persistente compartido **antes** de parsear, agregar o analizar los valores de
entrada — el hash de los archivos sí se calcula antes, porque forma parte de la
metadata de la reserva —, dejando
registrados candidato, commit, imagen inmutable, configuración, hashes de
entradas y productor, y entorno. La reserva DEBE finalizarse autenticando los
artefactos producidos por hash.

Un segundo intento científico DEBE rechazarse. La recuperación DEBE ser de solo
lectura, exigir una razón técnica explícita y verificar los hashes registrados;
NO DEBE reentrenar, predecir ni cambiar el candidato. Un registro ausente o
incompleto DEBE fallar cerrado y exigir revisión manual, sin comando de
liberación ni reinicialización.

#### Scenario: Segundo intento científico de la Etapa B

- **WHEN** ya existe un intento reservado para la clave de la Etapa B
- **THEN** el nuevo intento se rechaza y solo se admite recuperación explícita de
  solo lectura

### Requirement: Preflight de metadatos previo a la ejecución

El preflight DEBE validar que checkout, datos crudos, evidencia, ledger y
backups son directorios disjuntos y preexistentes, que la identidad de código
es limpia y conocida, y que la imagen se identifica por digest inmutable.

El preflight NO DEBE leer valores de las entradas, calcular features,
inicializar ningún ledger ni abrir ningún período reservado. Su resultado
`PREPARED_NOT_AUTHORIZED` NO constituye autorización de ejecución.

#### Scenario: Preflight sobre rutas solapadas

- **WHEN** evidencia o ledger quedan dentro del checkout, o dos de las rutas se
  solapan
- **THEN** el preflight falla explícitamente y no escribe ningún artefacto
