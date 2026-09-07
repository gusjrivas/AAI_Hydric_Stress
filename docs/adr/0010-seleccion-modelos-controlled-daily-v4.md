# ADR-0010: Estrategia multimodelo para controlled_daily_v4

Estado: Aceptado
Fecha: 2026-09-07

## Contexto

El plan de proyecto aprobado contempla, para la evaluación del componente de modelado predictivo, una configuración baseline, un conjunto de modelos de referencia y modelos candidatos, y una evaluación comparativa de distintas técnicas de aprendizaje automático. Dicha evaluación incluye el ajuste de hiperparámetros y la comparación de desempeño, estabilidad y complejidad entre alternativas. El plan establece que la selección del modelo final debe fundamentarse en evidencia experimental y no en la complejidad del algoritmo. El plan no exige la utilización de técnicas de aprendizaje profundo ni la adopción de un algoritmo específico.

La iteración `controlled_daily_v3` constituye evidencia científica formal congelada bajo el tag `scientific-baseline-v3`. La incorporación de nuevos modelos candidatos corresponde, por lo tanto, a una iteración científica independiente, identificada provisionalmente como `controlled_daily_v4`.

Se deja registrado expresamente que el conjunto de test utilizado en `controlled_daily_v3` ya fue observado durante dicha iteración. En consecuencia, ese conjunto no podrá reutilizarse como test independiente para seleccionar modelos, ajustar hiperparámetros, definir pesos de un ensamble o sostener nuevas afirmaciones de carácter confirmatorio.

## Decisión

Se registran los siguientes candidatos para la comparación de la iteración `controlled_daily_v4`:

1. **Regresión Logística**: constituye la referencia lineal e interpretable del conjunto. Permite evaluar si la incorporación de complejidad no lineal aporta mejoras reales respecto de un modelo simple.

2. **Random Forest**: método de ensamble basado en bagging. Permite representar relaciones no lineales e interacciones entre variables predictoras.

3. **HistGradientBoostingClassifier**: método de ensamble basado en boosting. Aporta una estrategia secuencial complementaria a Random Forest y se integra con el ecosistema scikit-learn ya utilizado por el proyecto.

4. **Soft Voting**: ensamble probabilístico de los tres modelos anteriores. Se evalúa como candidato experimental adicional, utilizando inicialmente pesos iguales y predefinidos. No se asume que este ensamble deba superar necesariamente a los modelos individuales, y no se ajustarán pesos, calibradores ni umbrales utilizando el conjunto de test.

Los cuatro candidatos deberán utilizar las mismas variables predictoras, el mismo target, el mismo horizonte de anticipación, las mismas fronteras temporales y las mismas configuraciones de datos. Deberán además compartir el mismo protocolo de evaluación, con semillas y versiones registradas e hiperparámetros trazables, y aplicar prevención explícita de leakage temporal.

Cualquier calibración probabilística o ajuste de pesos deberá ejecutarse exclusivamente dentro de las particiones temporales de entrenamiento y validación, sin intervención del conjunto de test.

## Pregunta experimental

¿Los modelos de ensamble basados en bagging y boosting, individualmente o combinados mediante Soft Voting, mejoran de manera consistente el desempeño, la estabilidad temporal y la calidad probabilística respecto de un modelo lineal interpretable para la detección temprana de estrés hídrico?

## Criterios de comparación

La comparación entre candidatos deberá considerar, como mínimo:

- las métricas predictivas definidas por el protocolo experimental;
- la incidencia de falsos positivos y falsos negativos;
- la estabilidad entre folds temporales;
- la calidad o calibración de las probabilidades, cuando corresponda;
- la complejidad del modelo;
- el costo computacional;
- la interpretabilidad;
- las limitaciones y el dominio de validez de cada candidato.

La selección del modelo final no deberá basarse únicamente en la mejor métrica puntual observada.

## Alternativas consideradas

### XGBoost

No se descarta por insuficiencia técnica. Se posterga porque HistGradientBoostingClassifier ya permite incorporar una familia de boosting integrada directamente con scikit-learn, evitando por ahora una dependencia externa y una superficie adicional de configuración. Incorporar simultáneamente dos variantes de boosting aportaría, además, menor diversidad que comparar una familia lineal, una de bagging y una de boosting. XGBoost se mantiene como alternativa futura para datasets de mayor volumen, diversidad o cobertura temporal.

### Deep Learning

No resulta obligatorio según el plan aprobado. Se posterga porque su mayor complejidad debe justificarse con volumen, frecuencia, diversidad y cobertura temporal de datos suficientes, condiciones que la iteración actual no garantiza. Se mantiene como trabajo futuro para datasets multianuales o de mayor granularidad.

### Mantener únicamente los modelos actuales

Esta opción conservaría validez formal, pero ofrecería una comparación menos amplia entre sesgos inductivos, al no contrastar explícitamente enfoques lineales, de bagging y de boosting.

## Consecuencias

Consecuencias positivas:

- comparación de tres familias de modelado complementarias (lineal, bagging, boosting);
- presencia de dos técnicas de ensamble diferenciadas: bagging y boosting;
- evaluación adicional de un ensamble de modelos mediante Soft Voting;
- fortalecimiento del núcleo predictivo del sistema;
- mayor coherencia entre modelado, selección, registro y arquitectura MLOps;
- posibilidad de justificar empíricamente si la complejidad adicional aporta valor real.

Costos y riesgos:

- mayor costo experimental por la cantidad de candidatos a entrenar y comparar;
- mayor espacio de hiperparámetros a explorar;
- riesgo de sobreajuste dada la disponibilidad limitada de datos;
- necesidad de controlar la selección múltiple de modelos y el leakage temporal;
- necesidad de diferenciar explícitamente resultados confirmatorios de resultados exploratorios.

## Compatibilidad con los baselines

Se declara expresamente que:

- `scientific-baseline-v3` permanece inmutable;
- `technical-baseline-v1` permanece inmutable;
- `technical-baseline-v2` permanece inmutable;
- `controlled_daily_v3` no será modificado ni reinterpretado;
- la futura evidencia experimental se almacenará bajo un nuevo identificador, previsiblemente `controlled_daily_v4`;
- cualquier nuevo baseline científico se creará únicamente después de definir, ejecutar y validar el nuevo protocolo experimental;
- este ADR no autoriza por sí mismo la ejecución de experimentos.

## Condición previa para controlled_daily_v4

Antes de implementar o ejecutar la nueva iteración, deberá:

1. verificarse si existe un período temporal todavía no observado que pueda reservarse como nuevo holdout;
2. si no existe dicho período, clasificarse la nueva comparación como extensión exploratoria;
3. definirse el protocolo completo antes de observar nuevos resultados;
4. impedirse que el conjunto de test de `controlled_daily_v3` intervenga en selección, ajuste, calibración o ponderación de los nuevos candidatos;
5. mantenerse separadas la evidencia histórica y la nueva evidencia experimental.

## Relación con la arquitectura y la memoria

Esta decisión fortalece el componente predictivo, pero no modifica la hipótesis, el propósito, el alcance ni la arquitectura general definida en ADR-0001.

En la memoria técnica del trabajo final:

- el capítulo 2 documentará la decisión metodológica adoptada en este ADR;
- el capítulo 3 describirá la implementación multimodelo derivada de esta decisión;
- el capítulo 4 distinguirá explícitamente la evidencia de `controlled_daily_v3` de la eventual evidencia de `controlled_daily_v4`;
- el capítulo 5 registrará XGBoost, Deep Learning y las evaluaciones multianuales como trabajo futuro.
