# Evaluación de evidencia de pronóstico para demostración, UI y memoria

**Estado:** evaluación documental dirigida; no es una nueva corrida experimental ni una aprobación del cierre científico.

**Base documental:** `44f8ad21ad9d301868f123500845c52e932faa3c` (`main`, con PR #222 incorporado).

**Fecha de evaluación:** 2026-09-27.

**HU:** HU4, HU5, HU6, HU7, HU8 y UI.

**Capacidades:** `predictive-modeling`, `human-feedback`, `architecture-integration`, `experiment-runner`, `scientific-closure`, `data-quality`, `data-ingestion` y `alerting-ui`.

**CRISP-DM:** evaluación y documentación.

**Impacto:** ninguno sobre configuración experimental, hipótesis aprobada, alcance o arquitectura. No se modificaron código, UI, políticas, modelos, datos, resultados, gates ni protocolos.

## 1. Respuesta ejecutiva

### 1.1 ¿Qué utilidad predictiva está demostrada?

Lo construido demuestra tres cosas diferentes, con fuerzas de evidencia distintas:

1. **Melchor Romero (`controlled_daily_v3`)** aporta una comparación formal histórica de ocho configuraciones para predecir a tres días el evento binario `humedad(t+3) < P20_train`. La evidencia vigente es parcial y mixta: la configuración `base` tuvo MCC medio cercano a cero (-0,0135) y quedó por debajo de persistencia tanto en F1 como en MCC; `recent_fraction_0.5` tuvo las mayores medias de la tabla formal (F1 0,6891; MCC 0,1417; AP 0,6546). Esto describe comportamiento dentro de ese sitio, año y diseño; no demuestra superioridad general ni anticipación de comienzos de episodio. Aproximadamente 24 % de los días de humedad fueron imputados causalmente y no existe un control limpio que caracterice ese efecto.
2. **Pergamino (`controlled_daily_v4`)** aporta evidencia numérica retrospectiva exploratoria a horizonte +3. En 2023, el candidato tuvo MCC 0,701 frente a 0,615 de persistencia, pero el intervalo pareado de la diferencia incluyó cero; el resultado cumplió una regla predeclarada de no inferioridad, no de superioridad. En 2024–2025, el MCC fue 0,665 frente a 0,573 y el intervalo de la diferencia excluyó cero, acompañado por mejor recall de días y episodios; también hubo 75 falsos positivos, dos episodios omitidos y calibración degradada. Por la desviación cronológica de gates, B y C no son confirmación protocolar: `SC-GOV-025`, `GF` y `sc-06-scientific-synthesis` permanecen en `FAIL`.
3. **Ensamble demostrativo de Pergamino** demuestra integración técnica real: nueve bundles —LR, Random Forest e HistGradientBoosting para +1/+2/+3—, nueve calibradores, carga, inferencia, emisión HTTP, idempotencia, acuerdo y review histórico. No existe una evaluación predictiva publicada y aplicable a esos nueve artefactos. Por ello, hoy no se les atribuye desempeño, calibración ni superioridad sobre modelos individuales o persistencia.

En todos los carriles el target es baja humedad relativa a un P20 congelado, no estrés fisiológico confirmado. La utilidad agronómica no está demostrada. La utilidad operativa defendible es más acotada: priorizar casos para que una persona **verifique el cultivo**, nunca activar riego automáticamente.

### 1.2 ¿Qué sabemos de la calidad de las probabilidades?

- En v3, la tabla formal vigente publica F1, MCC y AP medios, pero no Brier, curva de confiabilidad ni soporte por bin. No permite acreditar probabilidades operativas.
- En v4-B, el Brier del candidato fue 0,112560 frente a 0,149171 de persistencia. Ese valor agregado, sin una conclusión aplicable de confiabilidad, no prueba calibración adecuada.
- En v4-C, un Brier favorable (0,097512) convivió con sobreconfianza marcada: en el bin 0,9–1,0 la predicción media fue 0,964 y la frecuencia observada 0,663 (n=83). Es evidencia directa de que Brier bajo no basta y de que esos scores no deben narrarse como frecuencias operativas confiables.
- Los nueve bundles demostrativos poseen calibradores sigmoid ajustados en 2022, pero no una evaluación publicada de Brier/confiabilidad por familia, horizonte y población. Tener un calibrador entrenado no acredita calibración. El contrato lo reconoce: `display_probability=None`, `probability_status=not_qualified`.

### 1.3 ¿Qué política de decisión podemos justificar?

Podemos justificar como **contrato implementado**, no como política óptima, el umbral 0,5. En v4 fue fijado antes de evaluar; en el ensamble actual la alerta surge de:

`combined_alert = promedio(score_LR, score_RF, score_HGB) >= 0.5`.

`positive_votes` y `agreement_category` son metadata descriptiva. No gobiernan la alerta, no son porcentajes de riesgo y no prueban independencia entre modelos. La mayoría es una propuesta posterior pendiente, no implementada ni validada. Si falta un componente, el ensamble falla por entrada ausente; no se lo cuenta como voto negativo.

La evidencia disponible permite mostrar el equilibrio observado entre detección y falsas alertas, pero no elegir una política agronómica definitiva: faltan costos de omisión/alerta y criterios de uso acordados con especialistas o usuarios. La acción congruente con el alcance es “recomendar verificar”, con procedencia, horizonte, acuerdo, madurez y limitaciones visibles.

### 1.4 ¿Qué podemos mostrar hoy y cuál es la mínima brecha?

Hoy puede mostrarse el flujo completo de procedencia, control de calidad, pronóstico binario, acuerdo entre componentes, observación posterior, revisión y estado de elegibilidad, siempre separando evidencia histórica de una predicción individual. Melchor aporta el recorrido histórico de desarrollo; Pergamino aporta resultados exploratorios agregados y un ensamble operativo; el laboratorio sintético/mock permite demostrar fallas, calidad y estados controlados.

La brecha mínima es **una sola evaluación retrospectiva exploratoria, sin reentrenamiento, de los nueve bundles fijos sobre 2023**, con casos comunes, soporte, baselines, discriminación, calibración, episodios y cobertura por modelo/horizonte, más la combinación vigente por promedio. Esa evaluación no se ejecuta en esta entrega y no sería confirmatoria: 2023 ya fue utilizado en v4-B y en la demostración.

## 2. Alcance, autoridad y separación de evidencia

Esta evaluación usa sólo reportes agregados ya publicados, contratos, manifiestos y código. No abrió predicciones reservadas ni recomputó A/B/C/H. Tampoco abrió ni procesó en esta pasada los CSV ni los artefactos externos del runtime demostrativo. Sólo confirmó por metadatos que las rutas reportadas existen; sus hashes, contenido, compatibilidad e identidad quedan **referenciados** por el reporte de ejecución, no reverificados aquí.

La autoridad vigente se interpreta en este orden: protocolo y decisiones preejecución para el diseño; README, síntesis y GD-40 para el estado posterior. El texto preejecución que permanece en el protocolo v4 y el plan preejecución del ensamble son historia, no el estado final: GD-40 fija el `FAIL` de gobernanza, y el reporte de ejecución posterior fija qué demostración se realizó.

Los cinco conjuntos siguientes no son intercambiables:

- **A. Melchor Romero / v3:** un sitio, 2024, ocho configuraciones, Random Forest, +3. Su contrato usa 15 transformaciones temporales —lags 1/2/3 y medias móviles 3/7 sobre tres magnitudes—; `include_current=false` excluye las columnas actuales crudas como features independientes, mientras `roll_mean_3` y `roll_mean_7` sí incluyen el día de emisión.
- **B. Pergamino / v4:** un sitio de reanálisis, A 2015–2022, B 2023 y C 2024–2025, +3. `pergamino_features.v1` usa ocho features: tres valores actuales y cinco transformaciones sólo de humedad de suelo.
- **C. Ensamble demostrativo:** refit técnico nuevo, entrenamiento 2015–2021, calibración 2022, demo 2023, tres familias y +1/+2/+3. `producer_daily_h123_v1` usa 18 features: actual, lags 1/2/3 y medias móviles 3/7 para cada una de las tres magnitudes. No reutiliza artefactos ajustados de v4.
- **D. Review/recalibración/H:** review operativo del ensamble, review histórico aislado, recalibración legacy de un predictor y dos pistas científicas de H son circuitos distintos.
- **E. Calidad/simulación:** controles funcionales, anomalías inyectadas, generación estadística y sensor mock; no equivalen a eficacia predictiva de campo.

## 3. Matriz de evidencia

`ND` significa que el reporte agregado aplicable no publica el dato; no se lo completa por inferencia.

| Artefacto / sitio / horizonte | Período y soporte | Métricas disponibles | Baseline comparable | Utilidad respaldada | Límites y fuente |
| --- | --- | --- | --- | --- | --- |
| v3 `base`, Melchor Romero, +3 | Año 2024; dataset 357 filas tras limpieza; corte 2024-10-19; train n=199; test n=67, 39 positivos/28 negativos, prevalencia 0,5821; episodios ND; sin calibrador separado; 5 semillas sobre el mismo test | F1 0,5592±0,0287; MCC -0,0135; AP 0,5816 | Persistencia sobre el mismo test: F1 0,6000; MCC 0,0083. El artefacto formal también publica baselines constantes | Documenta discriminación débil: en F1 y MCC el modelo base no supera persistencia | Un sitio/año; seeds no independientes; ~24 % de humedad imputada; sin análisis de onset. Bloque agregado de `reference-v3-formal-results.json`; tabla formal; HU8 §8; protocolo v3 |
| v3 `recent_fraction_0.5`, Melchor Romero, +3 | Mismo test n=67, 39 positivos/28 negativos, prevalencia 0,5821; presupuesto supervisado 50 % reciente; episodios ND | F1 0,6891±0,0407; MCC 0,1417; AP 0,6546, mayores medias de la tabla | Persistencia sobre el mismo test: F1 0,6000; MCC 0,0083 | Resultado puntual favorable dentro del diseño; muestra sensibilidad al mecanismo de escasez | No es un componente de la hipótesis; mecanismo causal no demostrado; no acredita superioridad ni equivalencia. Mismas fuentes v3 |
| v3 `sinteticos` / `anomalias`, Melchor Romero, +3 | Mismo test n=67, 39 positivos/28 negativos, prevalencia 0,5821 y 5 semillas; episodios ND | Sintéticos: F1 0,5450±0,0986, MCC 0,0582, AP 0,6029. Anomalías: F1 0,5689±0,0395, MCC 0,0110, AP 0,5672 | Persistencia sobre el mismo test: F1 0,6000; MCC 0,0083; `base` como contraste pareado | Efectos mixtos; no se oculta el compromiso entre métricas | Generador normal multivariado; anomalías reales no etiquetadas; no demuestra mejora general. Tabla formal y HU8 §8 |
| v4-A, Pergamino, +3 | Desarrollo 2015–2022; OOF n=2184, 727 positivos; 3/3 folds por familia; bootstrap 5000/5000 | MCC: soft voting 0,7080; LR 0,6980; RF 0,6954; HGB 0,6858; intervalos pareados | Comparación interna sobre mismos folds/target | Cuatro familias técnicamente competitivas; LR elegida por simplicidad predeclarada | `SIN_GANADOR_ESTABLE`; ausencia de diferencia no demuestra equivalencia. Síntesis §§2–3 |
| v4-B, Pergamino, +3 | 2023; n=362; 96 positivos/266 negativos; 14 episodios, todos evaluables | Candidato: MCC 0,7014; P 0,6667; R 0,9375; F1 0,7792; Brier 0,1126; matriz [[221,45],[6,90]]; episode recall 12/14=0,8571. ΔMCC 0,0866, IC95% [-0,0146;0,2092] | Persistencia: MCC 0,6147; P 0,7234; R 0,7083; F1 0,7158; Brier 0,1492; matriz [[240,26],[28,68]]; episode recall 0,4286 | No inferioridad predeclarada; recall diario 0,9375 y 12/14 episodios anticipados | Exploratoria por `FAIL` de gates; no superioridad; 45 FP en 19 rachas; AP ND; una serie autocorrelacionada. Síntesis §4 |
| v4-C, Pergamino, +3 | 2024–2025; n=728; 128 positivos/600 negativos; 20 episodios, 19 evaluables, 1 censurado | Candidato: MCC 0,6648; P 0,6032; R 0,8906; F1 0,7192; Brier 0,0975; matriz [[525,75],[14,114]]; episode recall 0,9000. ΔMCC 0,0913, IC95% [0,0227;0,1784] | Persistencia: MCC 0,5734; P/R/F1 0,6484; Brier 0,1236; matriz [[555,45],[45,83]]; episode recall 0,5000 | Diferencia favorable puntual y por intervalo en esta serie; 16 anticipados, 1 mismo día, 2 omitidos | Exploratoria, no confirmatoria; 75 FP/26 rachas; calibración sobreconfiada; ~24 bloques efectivos; prevalencia 17,6 %. Sólo agregados publicados, sin reabrir holdout. Síntesis §5 |
| Nueve bundles demostrativos, Pergamino, +1/+2/+3 | Train 2015–2021: 2550/2549/2548 filas; calibración 2022: 364/363/362; una inferencia real al 2023-06-15 y recorrido técnico de 5 días/15 slots | Desempeño, AP, Brier, confiabilidad, matrices y episodios: ND. Evidencia técnica: 9 modelos + 9 calibradores, carga/inferencia/HTTP exitosos | No hay baseline evaluado para estos bundles | Demuestra empaquetado, linaje, inferencia multihorizonte e integración | No demuestra calidad predictiva/probabilística. Artefactos externos referenciados, no inspeccionados aquí. Reportes de ejecución y walkthrough |
| H simulada, Pergamino, +3 | 362 filas de evaluación de 2022; 20 eventos por seed (10 alerta/10 no alerta), 5 seeds | ΔMCC por correcciones: 3 positivos/2 negativos; sin intervalos; recalibración aplicada en 5/5 | `frozen`, `refit_no_corrections`, `refit_with_corrections` sobre mismos casos | Demuestra mecanismo de corrección/recalibración simulada | Efecto mixto, sin agregado inferencial; corrupción artificial; no beneficio humano. Síntesis §6.1 |
| H humana controlada, Pergamino, +3 | 20 revisiones de seed 0 | 20 ACCEPT; 0 REJECT/correcciones; `NO_RECALIBRATION`; 0/4 errores determinables detectados; concordancia 16/20 | Oráculo simulado corrigió 4/4 sobre esos eventos, sin convertirlo en comparación de pericia | Demuestra ejecución del procedimiento de aceptación en ese ejercicio | Un operador, cegamiento parcial, sin agrónomo; no acredita beneficio humano ni generaliza. Síntesis §6.2 |
| Calidad y sintéticos, Melchor/laboratorio, sin horizonte común de forecast | Dataset consolidado: 24,04 % faltante en humedad, 0 duplicados/fuera de rango; 10 anomalías extremas inyectadas; 366 filas sintéticas; sensor mock sin soporte de campo | 10/10 anomalías inyectadas detectadas; diferencia media de correlación 0,023; MAE lineal real 0,02312 vs sintético 0,02323 | Comparaciones internas específicas del componente | Demuestra controles, procedencia y capacidad de simular condiciones reproducibles | Extremos a 20 desvíos, normal multivariada y regresión lineal simple; no son desempeño del forecast final ni fallas reales de sensor. Spec `data-quality`; `mock_sensor.py` |

Las matrices de B y C permiten derivar los soportes de clase indicados porque están publicadas agregadamente. No se accedió a predicciones individuales. AP y prevalencia se informan juntas cuando existen; en v4 la síntesis no publica AP, por lo que queda ND. No se comparan Brier, F1 o precisión entre B y C como si sus poblaciones fueran equivalentes: la prevalencia cambia de 26,5 % a 17,6 %.

## 4. Evaluación por dimensión

### 4.1 Capacidad predictiva

**Discriminación diaria.** v3 muestra un base débil y resultados mixtos entre configuraciones. v4-B/C muestra que el candidato separó clases y, dentro de cada período, produjo MCC mayor que persistencia; sólo en C el intervalo pareado excluyó cero. El estatus exploratorio impide elevarlo a confirmación.

**Continuidad frente a comienzo de episodio.** El target pregunta si habrá baja humedad en `t+h`; no pregunta si el episodio comenzará en `t+h`. La persistencia puede acertar continuidad cuando hoy ya está seco. `episode_recall` agrega información útil, pero tampoco equivale por sí solo a detección de onset. En B se anticiparon 12/14 episodios; en C, 16 fueron anticipados, uno detectado el mismo día y dos omitidos entre 19 evaluables. Esos datos permiten hablar de anticipación observada en esos períodos, no de garantía operativa.

**Cobertura y exclusiones.** v3 conserva la amenaza de imputación en humedad. v4 requiere calendario completo y aborta ante huecos en vez de imputar. El runner demostrativo registró seis filas iniciales excluidas por falta de lookback en entrenamiento y ninguna por ese motivo en calibración. Para los bundles no hay aún cobertura de evaluación de 2023 publicada.

El runner demostrativo carga transitoriamente los CSV completos, pero recorta el rango permitido a 2015–2023 antes de la agregación diaria, del cálculo del P20, de las features y de los targets. Por lo tanto, 2024–2025 no intervino en entrenamiento, calibración ni demo. Esta contención ejecutable es distinta de la obligación de no reabrir la evaluación custodiada del holdout v4.

### 4.2 Calidad de probabilidades

Se deben separar tres niveles:

- un estimador que emite un score en [0,1];
- un calibrador ajustado;
- evidencia de confiabilidad sobre el modelo, horizonte y población de uso.

Sólo el tercer nivel permite narrar el score como frecuencia esperada. v4-C demuestra por qué: Brier y ROC-AUC favorables convivieron con sobreconfianza. Para el ensamble demostrativo sólo existen los dos primeros niveles; por eso la UI no debe exhibir `combined_probability` como “riesgo”. Unanimidad tampoco la convierte en alta probabilidad.

### 4.3 Utilidad de la decisión

La evidencia cuantifica algunos compromisos, no sus costos agronómicos. B ganó recall y `episode_recall` respecto de persistencia, pero perdió precisión y produjo más falsos avisos. C repitió ese patrón: 114 verdaderos positivos, 14 falsos negativos y 75 falsos positivos. No existe un costo acordado para una omisión frente a una visita innecesaria, ni un mínimo universal de MCC, precisión o recall.

Por ello, 0,5 es una referencia contractual y reproducible, no un óptimo. Tampoco se justifica cambiar a 0,7/0,8 ni adoptar mayoría a partir de esta evidencia. Esas decisiones requieren una comparación predefinida sobre casos comunes y un criterio de uso externo; elegir después el número que luzca mejor sería selección post hoc.

## 5. Qué aporta la arquitectura

| Componente | Aporte demostrado | Afirmación que no corresponde |
| --- | --- | --- |
| Ingesta y trazabilidad | Esquema, procedencia, hashes, ventanas temporales e identidad de artefactos | Que la fuente de reanálisis sea sensor de campo o validación agronómica |
| Calidad de datos | Faltantes, duplicados, rangos, causalidad, anomalías y origen sintético observables | Que detectar extremos inyectados pruebe fallas reales o mejore el forecast |
| Generación sintética / mock | Escenarios reproducibles y separados de datos reales; ejercicio técnico del flujo | Que equivalga a observación de campo o que sus métricas transfieran al ensamble |
| Modelado | Contratos temporales, familias comparables, bundles y horizontes explícitos | Que todos los modelos sean buenos o que compartir familia/sitio transfiera métricas |
| Alertas | Decisión binaria reproducible, horizonte, target date, acuerdo y linaje | Que `combined_probability` sea riesgo acreditado o que acuerdo sea independencia |
| Review operativo del ensamble | Registra `confirm`/`reject` respecto de `combined_alert` y estados de madurez | Que una revisión modifique bundles o sea medición independiente de campo |
| Review histórico | Demuestra, bajo reloj simulado y store aislado, persistencia e inmutabilidad | Que sea feedback real de productor/experto o que recalibre |
| Recalibración legacy | Endpoint manual HU5 que usa correcciones maduras para refitear un predictor y preservar linaje | Que recalibre el ensamble de nueve bundles |
| H simulada / humana | Simulada: correcciones y recalibración con efectos mixtos. Humana: 20 aceptaciones sin correcciones | Beneficio humano, eficacia agronómica o aprendizaje aplicado al ensamble |

En el review operativo: sin review corresponde `no_review`; antes de madurez, `waiting_target_maturity`; una revisión hecha antes de madurez requiere `requires_mature_revalidation`; una confirmación madura es `confirmation_only`; sólo una corrección `reject` madura del ensamble cae en `incompatible_source_model` por no existir una única `calibration_version`. `applied` no se alcanza en este repositorio.

Una etiqueta derivada de “confirmar/rechazar” expresa la revisión de la decisión binaria; no es una medición independiente de humedad ni un diagnóstico fisiológico.

## 6. Aplicación a UI, memoria y defensa

La UI debe conservar esta secuencia visual y semántica:

`datos/procedencia → calidad → forecast binario/horizonte → acuerdo → observación objetivo y madurez → review → efecto real`.

El último paso no debe insinuarse: si el review sólo fue registrado, el efecto real es “sin cambio de modelo”. Desempeño histórico debe rotular siempre modelo/artefacto, sitio, horizonte y período, separado del detalle de una predicción individual.

| Recorrido | Qué mostrar hoy | Qué demuestra | Evidencia predictiva que lo acompaña | Límite visible | Brecha para completarlo |
| --- | --- | --- | --- | --- | --- |
| Melchor histórico | Procedencia, calidad, imputación causal, contrato +3, tabla v3 y comparación de configuraciones | Desarrollo reproducible y lectura crítica de efectos mixtos | Medias F1/MCC/AP de la tabla formal; base débil y `recent_fraction_0.5` como mayor media, sin ranking causal | Un sitio/año; ~24 % imputado; sin soporte agregado completo de clase/episodio; target proxy | Ninguna para una demo histórica honesta; no usarla como prueba del ensamble Pergamino |
| Pergamino histórico | Contrato v4, A `SIN_GANADOR_ESTABLE`, B/C agregados, episodios, falsas alertas y curva/bin de confiabilidad de C | Evaluación temporal, comparación con persistencia y preservación de un resultado negativo/de gobernanza | B no inferior; C favorable en esta serie; ambos exploratorios | `FAIL` de gates; reanálisis, no campo; +3 solamente; C sobreconfiada | Ninguna para mostrar evidencia publicada; sí falta confirmación futura con datos nuevos para afirmaciones confirmatorias |
| Laboratorio sintético/mock + ensamble | Datos marcados sintéticos o reanálisis, controles de calidad, +1/+2/+3, componentes, votos/acuerdo, alerta combinada, madurez y review aislado | Integración funcional, manejo de estados e inmutabilidad | Ninguna métrica aplicable a los nueve bundles; sólo evidencia técnica de carga/inferencia | Probabilidad no calificada; review no aprende; mock no es campo; mayoría no implementada | Evaluación retrospectiva 2023 de los bundles fijos para asociar desempeño por artefacto/horizonte |

Para la memoria:

- **Capítulo 2:** target proxy, causalidad temporal, particiones, baselines, métricas, calibración, episodio/onset, gobernanza y límites inferenciales.
- **Capítulo 3:** arquitectura, contratos, bundles, procedencia, decisión por promedio, metadata de acuerdo y separación de circuitos HITL.
- **Capítulo 4:** resultados v3 y v4 en carriles separados, incluidos falsos avisos, omisiones, calibración degradada y `FAIL` de gobernanza.
- **Capítulo 5:** evaluación de nueve bundles, mayoría, datos nuevos/multisitio y validación con usuarios como trabajo posterior según qué afirmación se quiera sostener.

Para la defensa, la tesis defendible no es “el ensamble mejora”: es que se construyó un prototipo de IA trazable para anticipar baja humedad y apoyar verificación humana, se lo evaluó críticamente contra persistencia donde existe evidencia y se preservaron resultados mixtos, mala calibración y no conformidades sin transformarlos en éxitos.

## 7. Estado para el cierre

| Clasificación | Contenido |
| --- | --- |
| **Listo para usar** | Arquitectura y trazabilidad; contratos temporales; tabla v3 vigente; agregados v4 A/B/C/H con estado exploratorio; carga/inferencia técnica del ensamble; regla vigente promedio+0,5; walkthrough y review aislado; acción “verificar cultivo” |
| **Utilizable con limitación explícita** | v3 por sitio/año/imputación; B/C por gobernanza y reanálisis; episodios por definición disponible; Brier sólo junto con confiabilidad; datos sintéticos/mock sólo como laboratorio; H sólo dentro de cada pista |
| **Corrección necesaria** | En UI/memoria, no llamar probabilidad al score no calificado; no describir mayoría como política vigente; no mezclar revisión del ensamble con recalibración legacy; no mezclar métricas v4 con bundles; marcar textos preejecución históricos como superseded al citarlos |
| **Evidencia adicional necesaria** | Evaluación aplicable a los nueve bundles sobre casos comunes de 2023; criterio experto/uso para ponderar omisiones y falsas alertas si se quiere elegir política operativa |
| **Trabajo futuro que no bloquea la defensa** | Confirmación con datos nuevos, multisitio/campo, nueva calibración, evaluación de mayoría, umbrales alternativos predeclarados, validación longitudinal con usuarios y costos agronómicos |

La ausencia de evaluación del ensamble limita la afirmación “estos nueve modelos pronostican bien” y cualquier comparación promedio-versus-mayoría; no bloquea una demostración técnica rotulada como tal.

## 8. Única próxima tarea prioritaria

### Evaluación retrospectiva exploratoria 2023 de los nueve bundles fijos

**Pregunta.** ¿Qué discriminación, calidad probabilística, cobertura y comportamiento por episodios muestran LR, RF, HGB y el promedio vigente, por horizonte +1/+2/+3, sobre los mismos casos permitidos de 2023, y cómo se comparan con persistencia sin reentrenar ni elegir un umbral post hoc?

**Alcance.** Una ejecución de evaluación, separada de A/B/C/H, sólo con bundles fijos y datos permitidos hasta 2023. Mantener 0,5 como referencia contractual; describir votos/mayoría únicamente como alternativa preespecificada si el responsable la autoriza, sin cambiar la política vigente ni presentarla como validada. No abrir ni procesar 2024–2025.

**Viabilidad documental.** El runner define train 2015–2021, calibración 2022 y evaluación/demo 2023. El lookback máximo es de siete observaciones diarias incluyendo el día de emisión (`roll_mean_7`), por lo que evaluar desde el comienzo de 2023 requiere seis días previos con continuidad de calendario más ese día; esto concuerda con las seis primeras filas excluidas al comienzo absoluto de la ingesta. Para horizontes hasta +3, cada caso necesita además que su fecha objetivo observada permanezca dentro de 2023. En esta pasada se confirmó por metadatos, sin abrir ni procesar contenido, que existen las dos rutas de CSV, el directorio del runtime y su `run_manifest.json` referenciados por el reporte de ejecución. No se reverificaron sus hashes, contenido, compatibilidad ni autorización operativa. Antes de ejecutar se debe comprobar identidad y acceso autorizado; si falla esa comprobación, el bloqueo concreto es **identidad o acceso no acreditado del bundle fijo o del input 2023+lookback correspondiente**, y no se lo sustituye por fixtures.

**Artefactos requeridos.** Manifiesto e identidad de los 9 bundles; snapshots autorizados de entradas 2023 más lookback; contrato de target/P20 y features del demo; tabla de fechas comunes y exclusiones; observación de humedad para targets; baseline de persistencia sobre las mismas fechas; reporte agregado con n, positivos, negativos, prevalencia, episodios/evaluabilidad, matrices, MCC, precisión, recall, F1, AP, Brier, bins de confiabilidad, cobertura y falsos avisos.

**Criterio de aceptación.** (1) identidades y fechas verificadas antes de computar; (2) cero uso de 2024–2025; (3) cero refit/recalibración; (4) métricas por artefacto y horizonte sobre casos comparables, con indefiniciones explícitas; (5) persistencia evaluada sobre las mismas fechas; (6) continuidad y onset separados; (7) incertidumbre descrita sin tratar días correlacionados como réplicas independientes; (8) resultado rotulado “retrospectivo exploratorio, no independiente”: 2023 ya fue usado por v4-B y por la demostración; (9) resultados negativos preservados.

**Decisión habilitada.** Determinar si la UI puede asociar a cada modelo/horizonte un desempeño histórico exploratorio y si el promedio+0,5 merece conservarse como referencia demostrativa o debe quedar explícitamente “política sin evidencia suficiente”. No habilita declarar un umbral óptimo, superioridad del ensamble ni utilidad agronómica.

## 9. Contradicciones y brechas documentales no resueltas aquí

1. Las secciones históricas anteriores de `hu8-resultados-discusion-conclusiones.md` contienen números y conclusiones pre-formales incompatibles con §8 y la tabla v3 vigente. El propio documento declara esas secciones superseded. Esta evaluación usa §8 y `reference-v3-formal-table.md`; no reescribe el historial.
2. El protocolo v4 y el plan del ensamble conservan redacción preejecución. El estado posterior está fijado por README/síntesis/GD-40 y por el reporte real del ensamble, respectivamente. Se reconcilian por temporalidad y autoridad, no alterando las fuentes.
3. El bloque agregado formal v3 permite informar soporte por clase y baselines del caso `base`, pero no publica soporte por episodio. Ese dato queda ND en vez de reconstruirse desde predicciones.
4. No hay evaluación publicada aplicable a los nueve bundles. En esta pasada sólo se confirmó que las rutas externas reportadas existen, sin reverificar contenido, hashes o compatibilidad. La evaluación aplicable sigue siendo la brecha prioritaria.
5. No existe información de costos o umbrales de acción aportada por productores/agronomía. Por ello no puede resolverse documentalmente el intercambio entre falsas alertas y episodios omitidos.

## 10. Fuentes principales consultadas

- `openspec/scientific-closure/README.md`, `openspec/scientific-closure/traceability.md`, `openspec/scientific-closure/decisions.md` y `openspec/specs/scientific-closure/spec.md`.
- `docs/research/protocolo-experimental-v3.md`, el bloque agregado de `docs/research/reference-v3-formal-results.json`, `docs/research/reference-v3-formal-table.md` y `docs/research/hu8-resultados-discusion-conclusiones.md` §8. No se usaron sus predicciones individuales.
- `docs/research/scientific-closure-synthesis-2026-09-22.md` §§2–7.
- `docs/research/controlled-daily-v4-external-pergamino-manifest.yaml`, `docs/adr/0009-contratos-temporales-y-experimentos-controlados.md`, `docs/adr/0010-seleccion-modelos-controlled-daily-v4.md` y `docs/adr/0011-protocolo-controlled-daily-v4-external-pergamino.md`.
- `docs/design/ensemble-real-execution-report-2026-09-26.md` y `docs/design/ensemble-historical-walkthrough-report-2026-09-26.md`.
- `src/experiment_runner/pergamino_ensemble_demo_runner.py`, `src/predictive_modeling/ensemble_bundle.py` y `src/architecture_integration/producer_emission.py`.
- `src/human_feedback/operational_repository.py`, `src/human_feedback/historical_review_store.py`, `backend/app/routers/recalibration.py` y `src/human_feedback/recalibration.py`.
- `openspec/specs/data-quality/spec.md`, `openspec/specs/data-ingestion/spec.md` y `src/data_ingestion/mock_sensor.py`.
