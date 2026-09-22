# Trazabilidad de la evidencia hacia la memoria técnica — capítulos 2 y 3

**Nota de reconciliación.** Redactado originalmente en `feat/scientific-evidence-finalization`
(commit `7e63d1c`, corregido hasta `f355272`, PR #211) e incorporado aquí como
entregable de **RB-06**. Dos rondas de auditoría independiente lo revisaron
(informes preservados verbatim en `openspec/changes/sc-06-scientific-synthesis/reviews/`);
ambas terminaron en veredicto formal `FAIL` por defectos de gobernanza ajenos a
este contenido, y ese `FAIL` no se presenta como aprobación. La única adición de
esta reconciliación es la fila `2.12`, sobre imputación causal en la evidencia
de `controlled_daily_v3` citada en `2.3`.

Artefacto exigido por el criterio de aceptación de SC-GOV-025 («memoria caps. 2/3
trazada») y por el criterio de salida del gate `GF`. Cierra el bloqueo RB-06 que
levantó la auditoría final del complemento H.

**Este documento no edita la memoria LaTeX.** Fija qué evidencia puede usar cada
capítulo, qué resultado es utilizable, qué afirmación exacta está permitida, qué
limitación debe acompañarla siempre, qué tabla o figura conviene, y qué ajuste
queda pendiente. La redacción es trabajo posterior.

Fuente de los números: `docs/research/scientific-closure-synthesis-2026-09-22.md`,
que a su vez remite a la evidencia respaldada de `closure-campaign-2026-09-21` y
`hitl-complement-2026-09-21`. **Ningún número debe copiarse a la memoria desde
este documento sin pasar por la síntesis**, que es la fuente canónica.

---

## Advertencia estructural previa, que condiciona todo lo demás

`AGENTS.md` fija para este proyecto que el capítulo 2 justifica **metodología y
fundamento científico** y el capítulo 3 **arquitectura e implementación**. La
plantilla TTFA/LSE-UBA, en cambio, define el capítulo 2 como «Introducción
específica» —herramientas de terceros usadas en el capítulo 3—, el capítulo 3
como «Diseño e implementación» y reserva el capítulo **4** para «Ensayos y
resultados».

Las dos lecturas conviven mal en un punto concreto: **los resultados numéricos de
A, B, C y H no pertenecen ni al capítulo 2 ni al capítulo 3 bajo la plantilla.**
Este documento traza lo que corresponde a los capítulos 2 y 3 según el encargo, y
marca explícitamente, en la columna de ajuste pendiente, cada fila cuyo destino
natural bajo la plantilla es el capítulo 4. Resolver esa asignación es una
decisión del responsable, no de este artefacto.

---

## Capítulo 2 — metodología y fundamento científico

| # | Evidencia fuente | Resultado utilizable | Afirmación permitida | Limitación que debe acompañarla | Tabla o figura recomendada | Ajuste pendiente |
| --- | --- | --- | --- | --- | --- | --- |
| 2.1 | `controlled-daily-v4-external-pergamino-protocol.md`; ADR-0009; ADR-0011 | Diseño A→B→C con fronteras 2015–2022 / 2023 / 2024–2025, gap de 3 días y apertura única del holdout | «Se adoptó un protocolo temporalmente causal de tres etapas, con selección, validación temporal y holdout final de apertura única» | El diseño es retrospectivo; no hay evaluación en línea | Figura: línea de tiempo de las tres ventanas con el gap y el punto de apertura del holdout | Ninguno |
| 2.2 | `temporal-contract-check.json` | Contrato de ocho features idéntico en las tres etapas; target observado a t+3 no imputado; imputación causal sólo de entradas; P20 aprendido en train | «El contrato de variables y la definición del objetivo se mantuvieron idénticos en las tres etapas, y no se introdujo fuga temporal» | Verificación por atestación retrospectiva reconciliada con la evidencia, no por registro emitido durante la corrida | Tabla: las ocho variables con su origen (`soil_moisture`, `RH2M`, `ALLSKY_SFC_SW_DWN`, `lag1..3`, `roll_mean_3`, `roll_mean_7`) | Ninguno |
| 2.3 | `docs/research/reference-v3-formal-results.json`; protocolo v3 | Referencia histórica `controlled_daily_v3`, preservada y no recalculada | «El trabajo parte de una referencia previa validada, que se preserva y no se recalcula» | Es evidencia `REFERENCED` de otro diseño y otro sitio; no es un resultado de v4 | Ninguna; basta la cita | Verificar que la memoria no presente números de v3 y v4 en una misma tabla comparativa |
| 2.4 | ADR-0010; `selection_decision.json` | Regla de decisión predeclarada: margen práctico δ = 0,05 y desempate por simplicidad | «El criterio de selección y su regla de desempate se fijaron antes de observar resultados» | El desempate por simplicidad es una convención predeclarada, no una medición | Ninguna | Ninguno |
| 2.5 | `bootstrap.json` de A, B y C; `statistical-review.json` | Bootstrap por bloques no circulares de 30 días, 5000 réplicas, semilla 20250109; 5000/5000 válidas en las tres etapas | «La incertidumbre se cuantificó con bootstrap por bloques, adecuado a series autocorrelacionadas» | Intervalos percentiles **sin** corrección por multiplicidad ni calibración de cobertura; ~24 unidades efectivas en C | Tabla: réplicas solicitadas/válidas, segmentos y longitud de bloque por etapa | Declarar explícitamente la multiplicidad en A, donde se comparan seis pares |
| 2.6 | `stage_b_custody.json`; `holdout_status.json`; ledgers SQLite | Custodia por registro persistente: reserva previa a la lectura de valores en B; apertura única, nominal e irreversible en C | «La custodia del holdout se implementó como registro persistente de intento único, verificable de forma independiente» | SQLite no protege frente a un administrador del sistema; los resultados no tienen ancla en git | Figura: diagrama de secuencia reserva → ejecución → finalización, con marcas de tiempo | Ninguno |
| 2.7 | `claims.md`, sección final 2026-09-22 | Clasificación de afirmaciones en demostrada / respaldada con limitaciones / no demostrada / trabajo futuro | «Cada afirmación se clasificó según la evidencia que la sostiene, y las no sostenidas se declaran» | La clasificación es documental y no recomputa métricas | Tabla: las diez afirmaciones con su clasificación | Ninguno |
| 2.8 | `auxiliary/{R,N,S}/review.json`; GD-12 | Decisión de suficiencia por complemento, anterior a la ejecución y auditada de forma independiente | «El alcance de los complementos se delimitó antes de ejecutar, con revisión independiente de esa delimitación» | `NOT_REQUIRED` limita la afirmación; no significa que el complemento sea innecesario para el problema | Ninguna | Ninguno |
| 2.9 | `contract-H-frozen.json`; auditoría final de H | Diseño de tres brazos con maduración separada y dos pistas no intercambiables | «El aporte de las correcciones supervisadas se evaluó con un diseño de tres brazos preinscripto» | La pista humana **no** sostiene ninguna afirmación cuantitativa; cegamiento parcial declarado | Figura: los tres brazos con sus ventanas de train, feedback y evaluación | Ninguno |
| 2.10 | Síntesis 2026-09-22, secciones 7 y 8 | Inventario de amenazas a la validez interna y externa | «Se declaran las limitaciones de validez interna y externa del diseño» | Ninguna: esta fila **es** la limitación | Ninguna | Ninguno |
| 2.11 | GD-13; manifiesto de procedencia | Procedencia verificada por hash; licencias resueltas en sustancia | «Las fuentes se verificaron por hash y su admisibilidad se resolvió con decisión explícita» | Condición 2 de ADR-0011 sigue `PENDING_CONFIRMATION` en el manifiesto; fecha de adquisición efectiva `UNKNOWN` | Tabla: los dos productos con proveedor, resolución, bytes y SHA-256 | Actualizar el manifiesto es acción de quien integre en `main`; hasta entonces la limitación se declara |
| 2.12 | `docs/seguimiento-tareas.md` (verificación de cobertura); `reference-v3-formal-results.json`; `hu8-resultados-discusion-conclusiones.md` §8.4 | El dataset `melchor_romero_2024_consolidado` que produce la evidencia formal de v3 citada en `2.3` tiene 75,96 % de cobertura real en humedad de suelo; ~24 % de días son huecos imputados con `causal_ffill`, en las ocho configuraciones por igual | «La evidencia de referencia contiene una fracción de mediciones imputadas por continuidad causal, declarada y no caracterizada en su efecto» | **No** es evidencia de robustez ante mediciones ausentes; no hay condición limpia de comparación; no se afirma degradación con gracia | Ninguna | Ninguno. Añadido en la reconciliación 2026-09-22 (RB-03, dossier GD-12 §5) |

---

## Capítulo 3 — arquitectura e implementación

| # | Evidencia fuente | Resultado utilizable | Afirmación permitida | Limitación que debe acompañarla | Tabla o figura recomendada | Ajuste pendiente |
| --- | --- | --- | --- | --- | --- | --- |
| 3.1 | ADR-0003; `backend/`, `frontend/`, `src/` | Arquitectura de monorepo con fachada delgada y consumo de la API desde el frontend | «Se construyó una arquitectura de tres capas con separación estricta entre ingesta, modelado y presentación» | Sin ensayo con usuarios finales; sin medición de latencia operativa | Figura obligatoria: diagrama de bloques de la arquitectura completa | Ninguno |
| 3.2 | `src/experiment_runner/controlled_daily_v4/` | Runner de tres etapas con CLI `python -m experiment_runner.controlled_daily_v4.cli --stage {A,B,C}` | «El protocolo experimental se implementó como un runner con etapas explícitas y artefactos declarados» | El docstring del paquete todavía afirma que B y C no están implementadas (RK-19, abierto) | Figura: diagrama de estados del runner con sus compuertas | **Corregir RK-19 en un change propio antes de citar el paquete en la memoria**, o citar el defecto |
| 3.3 | ADR-0004; MLflow y MinIO | Registro de experimentos y almacenamiento de artefactos | «El seguimiento de experimentos se centralizó en un registro reproducible» | La campaña v4 se ejecutó en contenedor con evidencia en sistema de archivos, no a través del registro | Tabla: artefactos emitidos por etapa | Precisar en la memoria qué corridas pasan por el registro y cuáles no |
| 3.4 | `code_version.json`, `environment.json`, `resolved_config.json`, `input_hashes.json` | Identidad reproducible: commit ejecutable `214735e…`, imagen `sha256:55bc923e…`, semillas 42 y 20250109, huella del conjunto `8062605b…` | «Cada corrida registra commit, imagen, configuración, semillas, hashes de datos y entorno» | La identidad **documental** es distinta de la **ejecutable** y debe declararse aparte; la imagen no fue inspeccionable desde el entorno de validación Linux | Tabla: identidad de la campaña en una sola vista | Ninguno |
| 3.5 | `docker/experiment-v4/Dockerfile` y `constraints.txt` | Imagen inmutable con dependencias fijadas, base fijada por digest | «El entorno de ejecución se congeló en una imagen con dependencias fijadas por constraints» | `docker/experiment-v4/build.ps1` existe en esta rama y no en `main`; el runtime de contenedores no es alcanzable desde la distro WSL usada para validar | Ninguna | Ninguno |
| 3.6 | `src/human_feedback/`; HU5 | Circuito de retroalimentación con linaje temporal de las correcciones | «El circuito de retroalimentación humana está implementado de extremo a extremo y registra el linaje temporal de cada corrección» | **Evidencia técnica, nunca eficacia científica.** La implementación funcional no prueba beneficio | Figura: diagrama de secuencia del ciclo alerta → revisión → corrección → recalibración | Ninguno |
| 3.7 | `src/experiment_runner/scientific_auxiliary/auxiliary_hitl_v1.py` | Runner del complemento H con dos pistas separadas y no intercambiables | «El complemento de corrección supervisada se implementó como un runner propio, con identidad ejecutable distinta de la campaña principal» | La imagen de H es distinta de la de A/B/C por necesidad, no por elección; `pip freeze` idéntico, identidad de código distinta | Ninguna | Ninguno |
| 3.8 | HU6; `frontend/` | Interfaz del productor y flujo de decisión | «Se implementó una interfaz de apoyo a la decisión para el productor» | No se ensayó con usuarios; **el sistema es apoyo a la decisión, no automatización del riego** | Figura: captura del flujo de decisión | Si la memoria muestra probabilidades en la interfaz, debe declarar la calibración degradada del holdout |
| 3.9 | `scripts/check_scientific_closure.py`; `tests/test_scientific_closure_{checker,governance}.py` | Verificación mecánica de la gobernanza: checker exit 0, 33 + 15 pruebas | «La gobernanza del cierre se verifica mecánicamente, además de por revisión humana» | **Ningún PASS estructural equivale a cierre científico**, y el propio criterio de SC-GOV-020 lo dice | Ninguna | Ninguno |
| 3.10 | `/mnt/scientific-backup/…`; `recovery-rehearsal.json` | Respaldo externo con manifiesto, inventario, hashes y ensayo de recuperación | «La evidencia se respalda en soporte externo con verificación de integridad y ensayo de recuperación» | El ensayo acredita integridad y recuperabilidad de la copia, **no** resistencia a edición deliberada con privilegios; los resultados no tienen ancla en git | Ninguna | Ninguno |
| 3.11 | `scripts/readonly_role_sandbox.sh`; `tests/test_readonly_role_sandbox.py` | Aislamiento de sólo lectura para los roles revisores, con 11 pruebas | «Los roles revisores se ejecutan bajo un envoltorio que impone sólo lectura y ausencia de red» | El aislamiento cubre los comandos de shell del rol, **no** el proceso del subagente; los perfiles `.codex` no son cargables en este runtime | Ninguna | Ninguno |

---

## Resultados: dónde van y con qué texto

Las filas siguientes **no** pertenecen a los capítulos 2 ni 3 bajo la plantilla
TTFA. Se listan aquí para que la trazabilidad sea completa y para que el
capítulo que las reciba no las reformule.

| # | Evidencia fuente | Resultado utilizable | Afirmación permitida | Limitación que debe acompañarla | Tabla o figura recomendada | Ajuste pendiente |
| --- | --- | --- | --- | --- | --- | --- |
| R.1 | Etapa A | `SIN_GANADOR_ESTABLE`; MCC OOF 0,686–0,708 en las cuatro familias; candidato por desempate de simplicidad | «Ninguna familia se separó de las demás más allá del margen práctico; se seleccionó la más simple del conjunto de equivalencia» | **El modelo evaluado no es el de mejor MCC nominal**: ese fue `soft_voting`, a 0,0101 de distancia | Tabla: MCC OOF por familia con sus intervalos pareados | Destino: capítulo 4 |
| R.2 | Etapa B | `CANDIDATE_VALIDATED` por no inferioridad; Δ MCC 0,0866 con IC [−0,0146; 0,2092] | «El candidato resultó no inferior a la persistencia causal dentro del margen predeclarado» | **El intervalo incluye el cero**; la precisión del candidato (0,667) es inferior a la de la persistencia (0,723) | Tabla: candidato contra persistencia en 2023 | Destino: capítulo 4 |
| R.3 | Etapa C | Δ MCC 0,0913 con IC [0,0227; 0,1784], que excluye el cero; `episode_recall` 0,900 | «Sobre el holdout final el candidato superó a la persistencia en MCC, con el intervalo pareado excluyendo el cero» | ~24 unidades efectivas; sin corrección por multiplicidad; **una sola serie**. No es superioridad general | Tabla: candidato contra persistencia en 2024–2025 | Destino: capítulo 4 |
| R.4 | Etapa C, calibración | Bin 0,9–1,0: predicho 0,9643 contra observado 0,6627 (n = 83) | «La calibración de probabilidades se degradó en el holdout, con sobreconfianza creciente» | **Ni el Brier (0,0975) ni el ROC-AUC (0,9390) revelan el defecto** | Figura obligatoria: curva de calibración del holdout con la diagonal | Destino: capítulo 4. **Esta figura no puede omitirse** si la memoria muestra ROC-AUC |
| R.5 | Etapa C, operación | 75 días de falso aviso en 26 rachas; 3,09 FP cada 30 días; precisión de alerta 0,603; 2 episodios no detectados | «El sistema produce falsos avisos materiales y no detecta todos los episodios» | Métricas retrospectivas; sin medición de coste operativo del falso aviso | Tabla: matriz de confusión y métricas operativas de C | Destino: capítulo 4 |
| R.6 | Etapas A, B y C | Prevalencia 33,3 % → 26,5 % → 17,6 % | «La prevalencia de episodios decrece entre etapas, de modo que las métricas dependientes de prevalencia no son directamente comparables» | No existe artefacto que desagregue 2024 y 2025; **no se infiere** | Figura: prevalencia por etapa | Destino: capítulo 4 |
| R.7 | Complemento H, pista simulada | Deltas que aíslan correcciones: −0,0339 / +0,0084 / +0,0071 / +0,0044 / −0,0013 | «El mecanismo de corrección supervisada produce recalibración; los deltas son de signo mixto y no sostienen afirmación inferencial» | **Sin intervalos**, por diseño congelado; sin agregado entre semillas; cinco semillas no son cinco poblaciones | Tabla: MCC por semilla y brazo | Destino: capítulo 4 |
| R.8 | Complemento H, pista humana | `NO_RECALIBRATION`; 20 ACEPTAR; detección 0/4 frente a 4/4 del oráculo | «La intervención humana controlada no detectó ninguna de las cuatro etiquetas corrompidas que se le presentaron» | Un operador, 20 eventos, cegamiento parcial, sólo aceptación ejercitada; **no** es una medición de capacidad humana general | Tabla: los cuatro registros corrompidos con su humedad, etiqueta registrada y referencia | Destino: capítulo 4. **No presentarlo como fracaso del operador**: fija el alcance de la pista |

---

## Reglas de redacción que la memoria debe respetar

1. **No afirmar superioridad de la IA.** A terminó en empate práctico; B es no
   inferioridad; C es una ventaja en una sola serie con soporte efectivo reducido.
2. **No presentar ROC-AUC ni Brier sin la curva de calibración** del holdout.
3. **No atribuir mejora al feedback humano.** Los deltas son de signo mixto, sin
   intervalos, y la pista humana no produjo cambios.
4. **No convertir evidencia técnica en eficacia científica.** Pruebas verdes,
   checker en verde y suites completas acreditan software, no ciencia.
5. **No omitir el 0/4.** Es el hecho más saliente de la pista humana y debe
   aparecer junto a cualquier mención del circuito de retroalimentación.
6. **No presentar P20 como estrés fisiológico** ni el reanálisis como medición de
   sensores propios.
7. **No citar números desde este documento**: la fuente canónica es
   `docs/research/scientific-closure-synthesis-2026-09-22.md`.
8. **Declarar la limitación junto al resultado**, en el mismo párrafo o en la
   misma tabla, nunca en una sección de limitaciones lejana.

---

## Ajustes pendientes, consolidados

| ID | Ajuste | Responsable | Bloquea |
| --- | --- | --- | --- |
| AJ-01 | Decidir si los resultados de A/B/C/H van al capítulo 4 según la plantilla TTFA o al capítulo 2 según `AGENTS.md` | Responsable del trabajo | La redacción de los capítulos, no el cierre científico |
| AJ-02 | Corregir RK-19 —docstring de `controlled_daily_v4/__init__.py` que afirma que B y C no están implementadas— en un change propio | Change nuevo con su revisión | Citar el paquete en el capítulo 3 sin declarar el defecto |
| AJ-03 | Actualizar el manifiesto de procedencia con la licencia de NASA POWER (condición 2 de ADR-0011) | Quien integre este trabajo en `main` | Nada; hoy se declara como limitación |
| AJ-04 | Precisar qué corridas pasan por el registro de experimentos y cuáles se ejecutaron sólo en contenedor | Redacción del capítulo 3 | Nada |
| AJ-05 | Si la interfaz muestra probabilidades, declarar la calibración degradada junto a la captura | Redacción del capítulo 3 | Nada |

Ninguno de estos ajustes exige evidencia científica nueva ni reabrir el holdout.
