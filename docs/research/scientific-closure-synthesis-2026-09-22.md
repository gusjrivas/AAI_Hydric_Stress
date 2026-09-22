# Síntesis científica canónica del cierre — 2026-09-22

**Nota de reconciliación.** Este documento se redactó originalmente en la rama
`feat/scientific-evidence-finalization` (commit `7e63d1c`, revisado y corregido
hasta `f355272`, PR #211) y se incorpora aquí, a `feat/scientific-closure`, como
entregable de **RB-04**. Su contenido de resultados fue verificado por dos
rondas de auditoría independiente cuyos informes se preservan verbatim en
`openspec/changes/sc-06-scientific-synthesis/reviews/` (recomputación de 91/91
y 100/100 hashes, 72 métricas recalculadas en Python puro sin discrepancias,
correcciones `F-07`/`F-08` ya incorporadas al texto). **Las dos rondas
terminaron en veredicto formal `FAIL`, por defectos documentales de gobernanza
ajenos a estos resultados** (ver esos informes); ese `FAIL` no se presenta aquí
como aprobación, y el estado de `SC-GOV-025`/`GF` no se deriva de él. La única
adición de esta reconciliación es la sección 5, ítem (e), sobre imputación
causal en la evidencia de `controlled_daily_v3`.

Esta es la síntesis exigida por SC-GOV-016 y SC-GOV-025 **sobre los resultados
efectivamente obtenidos**. Supersede, sólo en lo relativo a resultados, a
`scientific-closure-synthesis-2026-09-20.md`, que se conserva íntegro y que fue
escrito antes de cualquier ejecución: aquel documento declara explícitamente que
«no contiene ningún resultado científico, porque ninguna campaña fue ejecutada».
Las secciones de procedencia, licencias y diseño de aquel documento siguen
vigentes y no se repiten aquí.

Esta sesión **no** ejecutó A, B, C ni H, **no** abrió el holdout, **no** repitió
auditorías históricas y **no** generó evidencia científica nueva. Todos los
valores provienen de la evidencia respaldada y verificada de las campañas
`closure-campaign-2026-09-21` y `hitl-complement-2026-09-21`, y cada uno se
puede rastrear al artefacto que lo publica.

El documento distingue en todo momento cinco categorías: **resultado** (lo que
la evidencia dice), **limitación** (lo que acota ese resultado), **validez
interna**, **validez externa** y **trabajo futuro**. Las inferencias se marcan
como tales y nunca se presentan como resultados.

---

## 1. Pregunta, hipótesis y respuesta

**Pregunta.** ¿La arquitectura de modelado validada en `controlled_daily_v3`
transfiere su desempeño a una segunda fuente agroclimática externa —reanálisis
de Pergamino— bajo un protocolo temporalmente causal y con un holdout final no
observado?

**Hipótesis operativa predeclarada.** Existe al menos un candidato entre las
cuatro familias autorizadas cuyo MCC sobre predicciones out-of-fold de 2015–2022
supera de forma **estable** a sus rivales y, al evaluarse una única vez sobre
2023, no resulta peor que la persistencia causal más allá del margen práctico
δ = 0,05.

**Respuesta, en dos partes.**

1. La primera mitad de la hipótesis —existencia de un ganador **estable**— quedó
   **refutada**. La Etapa A terminó en `SIN_GANADOR_ESTABLE`.
2. La segunda mitad —no inferioridad frente a persistencia— quedó **satisfecha**
   para el candidato fijado por el desempate predeclarado, y el holdout final
   confirmó una ventaja en MCC. Esto **no** rehabilita la primera mitad: el
   modelo evaluado no es el mejor de su grilla, es el más simple de un conjunto
   de equivalencia.

Esta combinación es un resultado válido del protocolo. No es un defecto de
software ni un fracaso experimental.

---

## 2. Objeto, identidad e integridad

| Elemento | Valor |
| --- | --- |
| Protocolo | `controlled_daily_v4_external_pergamino`, congelado antes de ejecutar |
| Sitio | Pergamino (lat −33,9 / lon −60,6). Reanálisis, **no** sensores propios |
| Variable de respuesta | Episodio P20 de humedad de suelo a t+3, **binario** |
| Profundidad de decisión | `soil_moisture_0_to_7cm` (`primary_selection`) |
| Contrato de features | `pergamino_features.v1`, ocho variables idénticas en A, B y C |
| Commit ejecutable A/B/C | `214735e42ee04f018156cd630591e798aadd8bf3` |
| Imagen A/B/C | `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af` |
| Semillas | modelo 42; bootstrap 20250109 |
| Huella del conjunto | `8062605b…38931`, 2913 filas |
| Integridad verificada | 91/91 hashes del respaldo de A/B/C, recomputados de forma independiente por el auditor de H |
| Ledger del holdout | `holdout.sqlite`, estado `CONFIRMADA`, un registro, apertura única e irreversible |

Las ocho features son `soil_moisture`, `RH2M`, `ALLSKY_SFC_SW_DWN`, `lag1`,
`lag2`, `lag3`, `roll_mean_3` y `roll_mean_7`, con horizonte de tres días.

---

## 3. Resultado — Etapa A (desarrollo y selección, 2015–2022)

**Resultado: `SIN_GANADOR_ESTABLE`.** Ninguna familia se separó de las demás más
allá del margen práctico δ = 0,05. El candidato se fijó por el desempate de
**simplicidad predeclarado**, no por desempeño.

| Familia | MCC OOF global | Δ puntual frente al máximo nominal |
| --- | ---: | ---: |
| `soft_voting` | 0,708028 | — (máximo nominal) |
| `logistic_regression` | **0,697968** | 0,010059 |
| `random_forest` | 0,695372 | 0,012655 |
| `hist_gradient_boosting_classifier` | 0,685799 | 0,022229 |

**El modelo seleccionado no es el de MCC más alto.** El máximo nominal lo obtuvo
el ensamble `soft_voting`; la regresión logística quedó segunda, a 0,0101 de
distancia. Las tres diferencias son menores que δ = 0,05, de modo que el conjunto
de equivalencia abarca las cuatro familias y la regla de desempate —la familia
más simple— seleccionó la regresión logística. La razón registrada es literal:
`tie_break_simplicity_predeclarada_no_superioridad`.

**Soporte.** Tres de tres outer folds definidos en las cuatro familias, sobre un
mínimo exigido de dos. Bootstrap por bloques no circulares de 30 días sobre tres
segmentos de 728 observaciones: 5000 de 5000 réplicas válidas, cero descartadas,
sobre un mínimo exigido de 4000. `warnings.json` vacío.

**Intervalos pareados al 95 %.** Cinco de los seis pares incluyen el cero. El
único que lo excluye es `soft_voting` frente a `hist_gradient_boosting_classifier`
([0,000658; 0,049069]), y su límite inferior es de orden 10⁻⁴: una separación sin
relevancia práctica frente a δ = 0,05. El par que gobierna la decisión,
`logistic_regression` frente a `soft_voting`, da [−0,026747; 0,004064] e incluye
el cero.

**Configuración congelada.** `ScaledLogisticRegression` con C = 1,0,
regularización L2, solver `lbfgs`, `max_iter` 2000 y ponderación
`sample_weight_balanced`. Umbral de decisión 0,5. P20 de entrenamiento final
0,302667, aprendido sobre train y nunca sobre validación. MCC mediano de la
segunda pasada de congelamiento 0,716280, con folds [0,716280; 0,658721;
0,732069].

**Sensibilidad 7–28 cm.** Corrida declarada `sensitivity_only_no_selection_effect`,
que **no** alimenta la selección. Coincide con la principal en el desenlace
(`SIN_GANADOR_ESTABLE`), en la familia elegida y en la regla de desempate.
Difiere en que el conjunto de equivalencia se reduce a tres familias. Su MCC es
más alto (0,820–0,872 frente a 0,686–0,708), y el propio registro de ejecución
advierte, literalmente, que «el MCC más alto a 7-28 cm NO indica un mejor
modelo»: un target definido sobre una capa más profunda y más inercial es
intrínsecamente más predecible, y comparar ambos números es comparar dos
problemas distintos.

**Limitaciones de A.** Cinco semillas y tres folds no son cinco ni tres
poblaciones. Los intervalos son percentiles sin corrección por multiplicidad
—se comparan seis pares— ni calibración de cobertura. El desempate por
simplicidad es una convención predeclarada, no una medición. Un empate práctico
no demuestra equivalencia: demuestra que el soporte disponible no separa.

---

## 4. Resultado — Etapa B (evaluación retrospectiva exploratoria, validación temporal 2023)

**Corrección 2026-09-22 (`decisions.md` GD-40, tras el hallazgo M-01/RK-20 de
la auditoría RB-05).** Los números de esta sección no cambian y siguen siendo
evidencia real. Lo que cambia es su estatus epistémico: la auditoría
independiente que debía preceder a esta etapa (Gate A `PASS`) se registró
*después* de que B ya hubiera corrido, de modo que B **no** puede
presentarse como validación confirmatoria gobernada por el protocolo
secuencial predeclarado. Se presenta aquí como **evaluación retrospectiva
exploratoria**. Detalle en la §7.4 de este documento y en
`openspec/scientific-closure/decisions.md` GD-38/GD-40.

**Resultado: `CANDIDATE_VALIDATED` por no inferioridad.** Las dos condiciones
predeclaradas se cumplen: MCC del candidato estrictamente positivo (0,701363) y
límite inferior del intervalo pareado ≥ −0,05 (observado −0,014553).

| Métrica sobre 2023 (n = 362) | Candidato | Persistencia causal |
| --- | ---: | ---: |
| MCC | 0,701363 | 0,614744 |
| F1 | 0,779221 | 0,715789 |
| Precisión | 0,666667 | 0,723404 |
| Recall | 0,937500 | 0,708333 |
| Brier | 0,112560 | 0,149171 |
| `episode_recall` | 0,857143 | 0,428571 |
| Matriz de confusión | [[221, 45], [6, 90]] | [[240, 26], [28, 68]] |

**Δ MCC puntual = 0,086619, con intervalo al 95 % [−0,014553; 0,209198].**
**El intervalo incluye el cero.** La compuerta B es de **no inferioridad**, no de
superioridad, y el propio registro de gobernanza lo enuncia en mayúsculas. B
**no** demuestra que el candidato sea mejor que la persistencia.

**Episodios.** Catorce episodios, los catorce evaluables, cero censurados: doce
anticipados, ninguno el mismo día, dos no detectados (onsets 2023-01-24 y
2023-04-29). Mediana de adelanto con signo: 3,0 días. Cuarenta y cinco días de
falso aviso repartidos en diecinueve rachas, con tasa de alerta 0,3729 —el
candidato alerta un día de cada 2,7— frente a una prevalencia de 96/362 = 26,5 %.

**Custodia.** Intento único, `attempt_id 7eb5bb7c…`. La reserva se registró a las
03:51:14,549 UTC y la finalización a las 03:51:29,229 UTC; el arranque precede a
la reserva por 19 milisegundos. Cero reintentos, `recover_stage_b = false`,
integridad SQLite `ok`. Bootstrap: 5000/5000 réplicas válidas sobre un segmento
de 362 observaciones, bloques de 30 días.

**Métricas nulas con razón, no sustituidas por cero.** El MCC de las dos líneas
de base constantes es `null` con razón `constant_prediction`; su precisión es
`null` con razón `no_predicted_positives`; los bins de calibración vacíos son
`null` con razón `no_observations_in_bin`. Esto es conformidad con el protocolo,
no un defecto.

**Limitaciones de B.** Una sola apertura, un solo año, 362 observaciones diarias
autocorrelacionadas. El intervalo incluye el cero. La precisión del candidato
(0,667) es **inferior** a la de la persistencia (0,723): la ventaja en MCC y en
`episode_recall` se paga con más falsos avisos.

---

## 5. Resultado — Etapa C (evaluación retrospectiva exploratoria, holdout final 2024–2025)

**Corrección 2026-09-22 (`decisions.md` GD-40, tras el hallazgo M-01/RK-20 de
la auditoría RB-05).** Mismo tratamiento que la Etapa B: los números no
cambian, pero la auditoría independiente de la Etapa B se registró *después*
de que C ya hubiera corrido, de modo que C tampoco puede presentarse como
validación confirmatoria del holdout gobernada por el protocolo secuencial.
Se presenta como **evaluación retrospectiva exploratoria**. El holdout
2024–2025 **no se reabre** por esta corrección ni por ninguna otra razón —
sigue siendo una apertura única, nominal e irreversible; lo que se corrige
es únicamente cómo se describe epistémicamente el resultado ya obtenido.
Detalle en la §7.4 y en `decisions.md` GD-38/GD-40.

**Resultado: favorable frente a la persistencia en MCC, con el intervalo pareado
excluyendo el cero.** El holdout se abrió **una única vez**, de forma nominal,
durable e irreversible, el 2026-09-21T04:06:11Z, con autorización explícita del
responsable y registro en el ledger (`attempt_id 2121cdc9…`, estado
`CONFIRMADA`). No se reabrió ni se releyó para decidir nada, ni entonces ni
después.

| Métrica sobre 2024–2025 (n = 728) | Candidato | Persistencia causal |
| --- | ---: | ---: |
| MCC | 0,664770 | 0,573438 |
| F1 | 0,719243 | 0,648438 |
| Precisión | 0,603175 | 0,648438 |
| Recall | 0,890625 | 0,648438 |
| Brier | 0,097512 | 0,123626 |
| ROC-AUC | 0,939049 | 0,786719 |
| `episode_recall` | 0,900000 | 0,500000 |
| Tasa de alerta | 0,259615 | 0,175824 |
| Matriz de confusión | [[525, 75], [14, 114]] | [[555, 45], [45, 83]] |

*Corrección tras el hallazgo `F-08`: la primera versión de esta tabla imprimía «—» en el ROC-AUC y el `episode_recall` de la persistencia. La evidencia sí los publica (0,786719 y 0,500000) y ambos favorecen al candidato, de modo que omitirlos no inflaba nada; pero «—» se lee como «no disponible» y no lo estaban.*

**Δ MCC puntual = 0,091333, con intervalo al 95 % [0,022658; 0,178418].** El
intervalo **excluye** el cero. Éste es el único resultado de la campaña en el que
una diferencia frente a la persistencia se separa del cero.

**Y debe leerse junto con cuatro hechos que lo acotan.**

**(a) Calibración degradada.** Las probabilidades del candidato están
sistemáticamente sobreconfiadas en el holdout, y el defecto crece con la
confianza:

| Bin de probabilidad | Predicho medio | Observado | n |
| --- | ---: | ---: | ---: |
| 0,0–0,1 | 0,022901 | 0,000000 | 372 |
| 0,1–0,2 | 0,142833 | 0,000000 | 62 |
| 0,7–0,8 | 0,756720 | 0,552632 | 38 |
| 0,8–0,9 | 0,857707 | 0,619048 | 21 |
| 0,9–1,0 | 0,964296 | 0,662651 | 83 |

Cuando el modelo dice 96 %, acierta 66 %. El registro de ejecución lo declara sin
atenuar, y añade el punto que importa para la memoria: **ni el Brier (0,0975) ni
el ROC-AUC (0,9390) revelan este defecto.** Dos métricas agregadas excelentes
conviven con una calibración inservible para una decisión basada en umbral de
probabilidad. Un sistema de apoyo a la decisión que muestre probabilidades al
productor **no** puede presentarlas como frecuencias esperadas.

**(b) Falsos avisos.** Setenta y cinco días de falso aviso en veintiséis rachas
sobre dos años: en promedio 3,09 falsos positivos cada 30 días. La precisión de
alerta es 0,603: cuatro de cada diez alertas no corresponden a un episodio.

**(c) Episodios no detectados.** Veinte episodios, diecinueve evaluables, uno
censurado. Dieciséis anticipados, uno el mismo día (2025-12-07), ninguno tardío y
**dos no detectados**: los onsets de 2024-12-12 y 2025-02-23, ambos con
`lead_days` nulo. Mediana de adelanto con signo: 2,0 días, un día menos que en B.

**(d) Deriva de prevalencia.** La prevalencia de episodios cae etapa a etapa:
33,3 % en el out-of-fold de A (727/2184), 26,5 % en B (96/362) y 17,6 % en C
(128/728). El objeto de evaluación se vuelve progresivamente más raro, y las
métricas dependientes de prevalencia no son directamente comparables entre
etapas. La evidencia publica la prevalencia agregada del bienio; **no** existe un
artefacto que la desagregue en 2024 y 2025 por separado, y no se infiere.

**(e) Imputación causal en la evidencia de referencia v3, no en A/B/C.**
*Añadido en la reconciliación del 2026-09-22, no estaba en la versión de
`f355272`. Corregido tras el hallazgo `F-01` de la auditoría de esa
reconciliación (`review-audit-reconciliation.md`): la redacción original citaba
`temporal-contract-check.json` como verificación de que la campaña A/B/C/H
imputa causalmente sólo sobre entradas. Ese artefacto no contiene ningún campo
ni control de imputación; sus cinco `leakage_checks` cubren fronteras
temporales, contaminación de P20 y el contrato de ocho features, no
imputación.* La campaña A/B/C/H usa entradas de reanálisis (ERA5-Land, NASA
POWER) sobre Pergamino y **no imputa**: el runner de v4 exige calendario diario
completo y aborta ante huecos en lugar de repararlos
(`controlled_daily_v4/features.py::validate_continuous_daily_calendar`,
`ingestion.py::aggregate_era5_daily`; verificado por grep, sin campo
`imputation` en el paquete v4). `causal_ffill` es una propiedad del contrato de
**v3**, no de v4 (`predictive_modeling/contract.py`,
`PIPELINE_VERSION = "controlled_daily_v3"`). Esto **no** es lo mismo que la
evidencia de referencia `controlled_daily_v3` (Melchor Romero), citada en
`claims.md` para CL-04 y CL-08: ese dataset tiene 75,96 % de cobertura real en
humedad de suelo, es decir ~24 % de días con huecos del producto satelital
imputados por `causal_ffill`, en las ocho configuraciones formales por igual,
sin caracterización de su efecto. Ver `hu8-resultados-discusion-conclusiones.md`
§8.4 y el dossier de suficiencia GD-12. No afecta las métricas de A, B, C ni H
reportadas en este documento —la garantía real de v4 (calendario completo o
aborto) es más estricta que la enunciada originalmente, no más débil—; sí acota
lo que la evidencia de v3 puede sostener
cuando se cita para justificar la suficiencia de S (robustez).

**Soporte efectivo.** Bootstrap 5000/5000 réplicas válidas, bloques de 30 días
sobre un segmento de 728 observaciones. El registro de gobernanza declara que,
con bloques de 30 días sobre 728 observaciones diarias autocorrelacionadas, el
número de unidades efectivamente independientes es **del orden de 24**. Un
intervalo que excluye el cero con ~24 unidades efectivas, sin corrección por
multiplicidad y sin calibración de cobertura, sostiene un resultado favorable en
esta serie; **no** sostiene una afirmación de superioridad general.

**Contaminación de P20 evitada.** El P20 de entrenamiento de C es 0,300275,
calculado sobre targets ≤ 2023-12-31. El registro deja constancia de que un P20
contaminado con el holdout habría dado 0,301917. La diferencia es pequeña y por
eso mismo vale registrarla: la conformidad no se mide por la magnitud del error
que se evitó.

---

## 6. Resultado — Complemento H (corrección supervisada con humano en el ciclo)

H es el **único** complemento activado (`REQUIRED` por GD-12). Corrió **una sola
vez**, con identidad ejecutable propia —imagen `experiment-v4-hitl-complement`,
distinta y declaradamente distinta de la de A/B/C—, construida con el mismo
Dockerfile y las mismas `constraints.txt`, y con `pip freeze --all` idéntico al
de la imagen histórica.

**Diseño.** Tres brazos sobre las **mismas** 362 filas de evaluación de 2022:
`frozen` (modelo congelado, targets ≤ 2020-12-31, sin refit),
`refit_no_corrections` (refit 2015–2021 con las etiquetas tal como quedan tras la
corrupción simulada) y `refit_with_corrections` (refit idéntico con las
correcciones del revisor aplicadas). Feedback exclusivamente en 2021; intersección
entre eventos revisados y filas de evaluación **igual a cero**; P20 congelado
único (0,318617) para las tres ventanas. Veinte eventos por semilla, estratificados
10 alertas / 10 no alertas, en cinco semillas congeladas (0–4). Fracción de
corrupción 0,10, con stream pseudoaleatorio independiente.

**Dos pistas separadas y no intercambiables** (GD-28): `simulated_supervised_feedback`,
que es el diseño congelado, y `controlled_human_feedback`, una intervención humana
controlada con su propio protocolo.

### 6.1 Pista simulada

MCC por semilla y brazo:

| Semilla | `frozen` | `refit_no_corrections` | `refit_with_corrections` |
| ---: | ---: | ---: | ---: |
| 0 | 0,453707 | 0,510678 | 0,476741 |
| 1 | 0,475442 | 0,431719 | 0,440070 |
| 2 | 0,479627 | 0,482246 | 0,489338 |
| 3 | 0,446347 | 0,502817 | 0,507204 |
| 4 | 0,464042 | 0,469509 | 0,468237 |

El contraste que **aísla las correcciones** es `refit_with_corrections` menos
`refit_no_corrections`: −0,033937 / +0,008351 / +0,007091 / +0,004388 / −0,001271.
**Signo mixto: tres positivos y dos negativos.**

El segundo contraste, `refit_no_corrections` menos `frozen`, mide la
**actualización temporal sin ninguna corrección**: +0,056971 / −0,043723 /
+0,002619 / +0,056470 / +0,005466, también de signo mixto. Es el efecto de
reentrenar con un año más de datos, y **no contiene aporte alguno de las
correcciones**. *Corrección tras el hallazgo `F-07` de la revisión
independiente: la redacción anterior lo describía como «el contraste que mezcla
la actualización temporal con las correcciones». Los cinco números eran
correctos; el rótulo era falso y atribuía a las correcciones una contribución
—+0,056971 en la semilla 0— que no tienen. El artefacto de origen lo nombra
`delta_temporal_update_mcc`, aunque el campo del propio `track_simulated.json` lleva la
etiqueta ambigua `combines_temporal_update`; recomputé los tres contrastes desde
los valores por brazo y confirmé que ese campo es, en efecto,
`refit_no_corrections − frozen`. En esa recomputación el valor de la semilla 4
resulta **+0,005466**, no +0,005467 como figuraba en la lista del informe: es un
redondeo del transcriptor, no un error de la evidencia, y se corrige aquí sin
tocar el informe, que se preserva verbatim.*

Para completitud, el contraste `refit_with_corrections` menos `frozen`, que sí
mezcla ambos efectos, da +0,023034 / −0,035372 / +0,009711 / +0,060857 /
+0,004195.

**No hay intervalos, y no por omisión.** El diseño congelado de H **no**
predeclara bootstrap, y los propios artefactos lo dicen: «deltas puntuales sin
intervalo de incertidumbre […] no sostienen ninguna afirmación inferencial, ni de
mejora ni de deterioro». **Tampoco existe un agregado entre semillas**: el
contrato establece que se reporta por semilla y que cualquier agregado es
descriptivo.

La recalibración se aplicó en las cinco semillas (`RECALIBRATION_APPLIED`), con
4, 4, 2, 1 y 1 correcciones efectivas y **cero rechazos** en todas. El mecanismo
de corrección y de recalibración queda demostrado **por esta pista**.

### 6.2 Pista humana controlada

Un operador experimental autorizado revisó los veinte registros de la semilla 0.
El paquete quedó anclado en git a las 16:57:51Z, **dos horas y diecisiete minutos
antes** de que el operador respondiera (19:14:26Z), y la respuesta quedó anclada
trece segundos antes de ejecutar. La preinscripción descansa sobre git, no sobre
lo que dicen los documentos, y fue verificada de forma independiente.

**Resultado: `NO_RECALIBRATION`.** Veinte decisiones de ACEPTAR, cero RECHAZAR,
cero CORREGIR, cero cambios efectivos. El contrato declaraba
`no_change_is_a_valid_outcome: true` **antes** de que el operador viera nada, y
esa anterioridad fue verificada en git. **No es un fallo.**

**Y debe enunciarse junto a su consecuencia, sin atenuar.** Cuatro de los veinte
registros presentados tenían la etiqueta invertida por el generador de corrupción:
`H-SC-004` (humedad 0,351958, etiqueta registrada 1), `H-SC-008` (0,473958, 1),
`H-SC-009` (0,408083, 1) y `H-SC-020` (0,249458, 0), todos contra el P20 congelado
0,318617. El operador **aceptó los cuatro**. **Tasa de detección humana: 0 de 4.**
Sobre exactamente los mismos eventos, el oráculo simulado corrigió **4 de 4**. La
concordancia global con la regla determinista fue 16/20, y el motivo que el
operador invocó —el umbral— es aritméticamente incorrecto para esos cuatro
registros. La decisión se conserva literal y no se reinterpreta.

Como la pista humana no produjo cambios, sus dos brazos de refit son idénticos y
su delta que aísla correcciones es exactamente 0,0. **La pista humana no sostiene
ninguna afirmación cuantitativa.**

**Limitaciones de H que deben acompañar siempre a cualquier lectura.**

1. Detección humana 0/4 frente a 4/4 del oráculo, sobre los mismos eventos.
2. La pista humana ejercitó **sólo la aceptación**. Corrección y recalibración
   quedan demostradas únicamente por la pista **simulada**. **Rechazo** y
   **recalibración sucesiva** no fueron ejercitados por **ninguna** pista
   científica: sólo por la suite con fixtures, que por contrato no es evidencia
   científica, y que la auditoría final **no** pudo reverificar (AUD-H-09).
3. El cegamiento fue **parcial y declarado antes** de la intervención: el paquete
   mostraba la observación madurada y el P20, de modo que la etiqueta correcta era
   determinable y las instrucciones enunciaban la regla. La pista humana prueba el
   cumplimiento de un procedimiento dictado, **no** criterio propio, pericia ni
   juicio bajo incertidumbre. Además el operador es el autor del código y del
   generador de corrupción: el cegamiento frente a él es nominal.
4. Un único operador, veinte eventos, cinco semillas que no son cinco poblaciones,
   reanálisis de un solo sitio, deltas puntuales sin intervalo. La corrupción de la
   pista simulada es un **modelo de error artificial**, no una medición de la tasa
   de error de un revisor real.
5. No hubo intervención de un agrónomo ni validación agronómica de campo. Ningún
   documento vigente la exige para cerrar H, HU5 ni el gate GF —`openspec/project.md`
   la excluye del alcance, ADR-0011 dice «nunca validación agronómica in situ» y el
   diseño congelado ordena no afirmar eficacia agronómica—, y está declarada como
   limitación y trabajo futuro por el propio operador.
6. Los **resultados** de H no tienen ancla en git: viven en un montaje escribible
   protegido por un manifiesto alojado en ese mismo montaje. Las **entradas**
   —contrato, paquete y respuesta— sí están ancladas y fueron verificadas.
   Exposición estructural idéntica a la de A/B/C y preexistente.

---

## 7. Validez interna

**Lo que sostiene la validez interna.**

- **Causalidad temporal verificada.** Fronteras 2015–2022 / 2023 / 2024–2025 sin
  solapamiento, gap de tres días, target observado a t+3 **no imputado**, P20 y
  transformaciones aprendidos en train y aplicados a validación. El contrato de
  ocho features es idéntico en las tres etapas. Verificado en
  `temporal-contract-check.json` (cinco `leakage_checks` de fronteras,
  contaminación de P20 y contrato de features) y recomprobado por auditoría
  independiente. **Corrección tras el hallazgo `F-01`:** la campaña **no
  imputa** entradas; el runner de v4 aborta ante huecos del calendario diario
  en vez de repararlos (ver ítem (e) de la sección 5). `causal_ffill` es una
  propiedad del contrato de v3, no de v4.
- **Preinscripción.** El protocolo, el margen δ = 0,05, la regla de desempate por
  simplicidad, las dos condiciones de la compuerta B y el contrato de H estaban
  congelados y anclados en git **antes** de producir los resultados que gobiernan.
  En el caso de H, la anterioridad se verificó en objetos git, no en prosa.
- **Apertura única.** B se reservó en un registro persistente **antes** de analizar
  valores; C se abrió una sola vez con ledger. Ambos ledgers fueron releídos en
  modo sólo lectura por un auditor independiente y están en el estado declarado.
- **Reproducibilidad de las métricas.** El auditor de H recomputó 72 métricas desde
  los CSV de predicciones con implementaciones propias en Python puro, sin
  `sklearn`, con cero discrepancias a tolerancia 1e-9.
- **Integridad.** 91/91 hashes del respaldo de A/B/C verificados de forma
  independiente; ningún archivo modificado después de la campaña.

**Lo que la acota.**

- **Multiplicidad sin corregir.** En A se comparan seis pares de familias con
  intervalos percentiles sin corrección ni calibración de cobertura. Un intervalo
  que excluye el cero en ese conjunto no equivale a una prueba con nivel
  controlado.
- **Soporte efectivo reducido.** Observaciones diarias autocorrelacionadas: ~24
  unidades efectivas en C. Los intervalos son más anchos de lo que su n nominal
  sugiere, y el bootstrap por bloques mitiga pero no elimina el problema.
- **Un único modelo congelado.** Tras A no se exploró nada más. Esto protege
  contra el sobreajuste al holdout y, a la vez, impide saber si otra familia
  habría rendido distinto en 2024–2025.
- **Calibración no corregida.** No se aplicó ningún método de recalibración de
  probabilidades, y el protocolo congelado no lo predeclaraba.
- **Sustitución de roles declarada.** Los cinco perfiles `.codex/agents` no son
  cargables en este runtime; las revisiones independientes se ejecutaron con otro
  runtime en sesiones separadas de sólo lectura. Se documenta la sustitución y
  **no** se la presenta como equivalencia.

### 7.4 Gobernanza de gates: hallazgo M-01/RK-20 (2026-09-22)

**Añadido 2026-09-22, tras la auditoría independiente RB-05
(`openspec/changes/sc-06-scientific-synthesis/reviews/review-audit-rb05-codex-FAIL.md`,
veredicto `FAIL`) y la aceptación administrativa del responsable
(`decisions.md` GD-38, GD-40).** El protocolo predeclarado exige que cada
etapa sea auditada independientemente **antes** de autorizar la siguiente
(Gate A → autoriza B; Gate B → autoriza C). El registro de gobernanza
(`changes.json`) y las marcas de tiempo de sistema de archivos de los
artefactos de auditoría muestran que, en la ejecución real del
2026-09-21, **B se ejecutó antes de que existiera el veredicto de auditoría
independiente de A, y C se ejecutó antes de que existiera el veredicto de
auditoría independiente de B** — verificado por dos fuentes primarias
independientes entre sí. La secuencia *computacional* fue A→B→C, cada etapa
corrida una sola vez, con custodia técnica y exit 0 verificados; lo que no
puede certificarse es que la compuerta de auditoría *gobernó* esa secuencia
como el protocolo exige.

**Qué significa esto para los resultados.** Los números de las secciones 3, 4
y 5 no cambian y no están invalidados: son evidencia numérica real,
recomputada de forma independiente. Lo que cambia es su lectura: B y C
**dejan de poder presentarse como validación confirmatoria gobernada por el
protocolo secuencial** y se presentan en este documento como **evaluación
retrospectiva exploratoria**. Esta distinción no es cosmética — es la
diferencia entre "el candidato superó una compuerta que sólo se abre si la
etapa anterior fue aprobada de forma independiente" y "el candidato produjo
estos números en una ejecución donde esa compuerta no operó como estaba
diseñada".

**Qué no cambia.** El holdout 2024–2025 no se reabre por este hallazgo ni por
ningún otro motivo derivado de él. No se reejecuta B ni C. `SC-GOV-025` y el
gate `GF` cierran en `FAIL`, no en `PASS_WITH_LIMITATIONS`: la aceptación
administrativa de esta desviación (`GD-40`) no equivale a su reparación
científica. Una confirmación futura del alcance de HU7/HU8 requiere una
campaña nueva, con gates verificados en tiempo real, sobre datos no
utilizados previamente por `controlled_daily_v4`.

---

## 8. Validez externa

La validez externa de estos resultados es **estrecha**, y conviene decirlo antes
que cualquier otra cosa sobre ellos.

- **Un solo sitio.** Pergamino. Balcarce no alimenta la comparación principal. No
  hay evidencia de generalización geográfica.
- **Reanálisis, no medición.** ERA5-Land vía Open-Meteo y NASA POWER son productos
  de reanálisis y modelado, no sensores propios en campo. El trabajo **no** mide
  humedad de suelo: consume una estimación de un modelo atmosférico.
- **Proxy, no fisiología.** P20 es un percentil empírico de humedad de suelo, no
  una medición de estrés hídrico del cultivo. No hay validación fisiológica ni
  agronómica.
- **Retrospectivo, no operativo.** Todas las métricas de anticipación son
  retrospectivas sobre series completas. No hay medición de latencia, de
  disponibilidad del dato en tiempo real ni de utilidad para una decisión de riego.
  El desfase UTC-3 frente a hora local solar permanece como límite estructural.
- **Ventana temporal corta.** Un año de validación y dos de holdout, con
  prevalencia decreciente. La variabilidad interanual de una serie agroclimática
  es mayor que la que tres años pueden capturar.
- **Sin usuarios.** No hubo ensayo con productores. HU5 y HU6 están implementadas
  y son evidencia **técnica**; su utilidad operativa no fue medida.

---

## 9. Limitaciones que deben acompañar cualquier lectura

1. `SIN_GANADOR_ESTABLE` en A: el modelo evaluado es el más simple de un conjunto
   de equivalencia, **no** el de mejor desempeño nominal.
2. La compuerta B es de **no inferioridad**; su intervalo incluye el cero.
3. En C, el intervalo excluye el cero, pero con ~24 unidades efectivas, sin
   corrección por multiplicidad y sobre una sola serie.
4. **Calibración degradada en C**, invisible en Brier y ROC-AUC.
5. Falsos avisos materiales: 3,09 cada 30 días en C; precisión de alerta 0,603.
6. Dos episodios no detectados en B y dos en C.
7. Deriva de prevalencia 33,3 % → 26,5 % → 17,6 % entre etapas.
8. H: detección humana 0/4; sólo aceptación; cegamiento parcial; sin intervalos;
   **sin mejora atribuible al feedback**.
9. Rechazo y recalibración sucesiva no ejercitados por ninguna pista científica.
10. Sin intervención de agrónomo ni validación de campo.
11. Condición 2 de ADR-0011 (licencia NASA POWER) sigue `PENDING_CONFIRMATION` en
    el manifiesto; fecha de adquisición efectiva `UNKNOWN`.
12. Los resultados científicos no tienen ancla en git; su integridad descansa en
    manifiestos alojados en el mismo montaje escribible.
13. Dos `git push` durante la fase de preparación incumplieron una cláusula
    explícita; la desviación está reconocida (RK-14) y **no** subsanada.
14. La sustitución de los perfiles de rol está declarada y no subsanada.

Ninguna de estas limitaciones exige evidencia científica nueva para ser
declarada, y ninguna se atenúa en este documento.

---

## 10. Trabajo futuro

| Línea | Evidencia nueva que exigiría |
| --- | --- |
| Validación agronómica de campo | Campaña prospectiva con observación humana independiente de si las predicciones se corresponden con la realidad |
| Recalibración de probabilidades | Método predeclarado (Platt, isotónica) con su propio conjunto de calibración causal, y reevaluación que **no** reutilice este holdout |
| Beneficio real del feedback humano | Revisores múltiples, cegamiento efectivo, rechazo y recalibración sucesiva ejercitados, y tamaño muestral que admita intervalos |
| Generalización geográfica | Réplica del protocolo v4 en al menos un segundo sitio, con procedencia y holdout propios |
| Desempeño sobre humedad continua | Complemento R: diseño congelado, runner validado, MAE/RMSE en m³/m³ contra persistencia |
| Detección reservada de corrupciones | Complemento N: fit sólo en train, inyección reservada conocida, matriz de confusión y soporte |
| Robustez ante mediciones ausentes | Complemento S: cuatro condiciones fijas, cinco semillas, target limpio común, máscaras e imputación registradas |
| Sensores propios en campo | Ingesta real con procedencia, calibración y custodia propias; hoy el trabajo consume reanálisis |
| Utilidad operativa | Ensayo con productores, medición de latencia y de disponibilidad del dato en tiempo real |

---

## 11. Lo que esta campaña **no** afirma

Superioridad general de IA, ensambles o aprendizaje profundo. Validación
agronómica, eficacia de campo o ahorro de agua. Estrés fisiológico de cultivos.
Mejora causada por el feedback humano. Capacidad humana de detectar errores de
etiqueta. Generalización geográfica. Anticipación operativa o latencia de alerta.
Robustez ante sensores caídos. Desempeño sobre humedad continua. Detección
reservada de corrupciones. Que este cierre certifique HU1 o la tesis completa.

El sistema es **apoyo a la decisión**, no automatización del riego, y esa
distinción no es retórica: con una precisión de alerta de 0,603 y una calibración
sobreconfiada, un accionamiento automático sería indefendible con esta evidencia.
