# Síntesis del cierre científico — estado al 2026-09-20

Estado terminal de esta sesión: **preparación resuelta hasta el límite de lo
alcanzable localmente; ejecución científica BLOQUEADA por una precondición
normativa externa.**

Este documento es la síntesis exigida por SC-GOV-016 y SC-GOV-025. Distingue
en todo momento cuatro categorías: **hecho verificado**, **resultado**,
**inferencia** y **limitación o pendiente**. No contiene ningún resultado
científico, porque **ninguna campaña fue ejecutada**.

Autoridad: `docs/research/controlled-daily-v4-external-pergamino-protocol.md`,
[ADR-0011](../adr/0011-protocolo-controlled-daily-v4-external-pergamino.md),
[ADR-0010](../adr/0010-seleccion-modelos-controlled-daily-v4.md),
`docs/research/scientific-closure-decisions.md`. Esta síntesis **no** los
modifica, reinterpreta ni reemplaza.

---

## 1. Pregunta de investigación e hipótesis

**Pregunta.** ¿La arquitectura de modelado validada en `controlled_daily_v3`
transfiere su desempeño a una segunda fuente agroclimática externa
(reanálisis de Pergamino), bajo un protocolo temporalmente causal y con un
holdout final no observado?

**Hipótesis operativa predeclarada.** Existe al menos un candidato entre las
cuatro familias autorizadas cuyo MCC sobre predicciones out-of-fold de
2015–2022 supera de forma estable a sus rivales y, al evaluarse una única vez
sobre 2023, no resulta peor que la persistencia causal más allá del margen
práctico `δ = 0.05`.

**Estado de la hipótesis: NO EVALUADA.** No se produjo evidencia a favor ni en
contra. No es un resultado negativo: es ausencia de ejecución.

---

## 2. Datasets, procedencia y licencias

Dos productos de **reanálisis/modelado**, no mediciones de sensores propios de
campo. Esta distinción es normativa y se conserva en toda afirmación.

| Producto | Proveedor | Resolución | Archivo | Bytes | SHA-256 |
|---|---|---|---|---:|---|
| ERA5-Land humedad de suelo | Open-Meteo Archive API (modelo ERA5-Land) | horaria | `pergamino_era5land_soil_hourly_2015_2025.csv` | 3 954 003 | `318edffb89c64d5f500e35b5530e6064cb02f68b89bd28a71262c2ebb01f485f` |
| NASA POWER diario, comunidad AG | NASA POWER (MERRA-2 + CERES SYN1deg) | diaria | `pergamino_nasa_power_daily_2015_2025.csv` | 127 568 | `415b4f71abb78e419b765110f4a42c3f32587b204d12897812df9573c5c2202b` |

**Hecho verificado (2026-09-20).** Ambos hashes coinciden con el manifiesto
versionado `controlled-daily-v4-external-pergamino-manifest.yaml`, y la
validación de procedencia del propio runner
(`--stage A --validate-inputs-only --input-mode scientific`) devolvió exit 0
(`Provenance OK`). La copia lógica de respaldo es byte a byte idéntica
(`cmp` exit 0 en ambos archivos).

**Licencias — decisión GD-13, `ADMISSIBLE_WITH_EXPLICIT_LIMITATIONS`.**

- ERA5-Land vía Open-Meteo: CC-BY-4.0, términos oficiales verificados el
  2026-09-17. API gratuita reservada a uso no comercial. Obliga a atribuir
  Open-Meteo y Copernicus ERA5-Land y a registrar modificaciones.
- NASA POWER: **negativo verificado** — las páginas oficiales del propio
  proyecto publican la cita exigida pero **ninguna** licencia ni restricción de
  uso. La guía oficial de NASA ESDIS establece que *«data provided from a
  NASA-led mission are licensed as Creative Commons Zero (CC0)»* salvo
  restricción marcada, y que *«there are no restrictions on the use of these
  data»*. **Paso inferencial, declarado como tal:** aplicar esa cláusula a
  POWER exige asumir que «proyecto financiado por la NASA Earth Science
  Division» queda cubierto por «NASA-led mission». Eso es una **inferencia**,
  no una cita: no se encontró ningún documento oficial que lo afirme con esas
  palabras. Es el paso que sostiene la decisión. Este trabajo es investigación
  académica no comercial y cita según la guía oficial de POWER.

**Limitaciones de procedencia conservadas, no resueltas:**

1. La **fecha efectiva de adquisición** de ambos archivos permanece
   `UNKNOWN`. El proyecto informa 2026-09-08 sin verificación independiente.
   Las fechas de modificación en disco **no** fueron promovidas a fechas de
   adquisición.
2. Los **términos vigentes en el instante (desconocido) de adquisición** no
   fueron verificados. Solo se verificaron los términos publicados al momento
   de esta consulta, y se registran expresamente como vigentes, no históricos.
3. `downloaded_service_version` de NASA POWER permanece `UNKNOWN`.
4. La aplicabilidad de la cláusula CC0 de NASA ESDIS a NASA POWER es una
   **inferencia**, no un hecho citado (ver arriba).
5. El **manifiesto versionado no fue modificado**: sigue registrando
   `license_status: PENDING_CONFIRMATION` para NASA POWER y
   `acquisition_date_status: PENDING_CONFIRMATION` para ambas fuentes. Por eso
   la condición 2 de ADR-0011 se declara **resuelta en sustancia, no
   formalmente satisfecha contra el manifiesto**: actualizar esos campos es una
   acción documental reservada a quien integre este trabajo en `main`, porque
   el manifiesto forma parte de la identidad congelada verificada idéntica a
   `214735e`.
6. Los tres instantes exactos de recuperación de las páginas oficiales **no
   fueron capturados**; se sabe que ocurrieron durante esta sesión, el
   2026-09-20. Los revisores independientes no pudieron re-verificar esas URLs
   porque su sandbox no tiene red: son evidencia de una sola fuente y un solo
   observador.

---

## 3. Población, sitio y período

- **Sitio único:** Pergamino (lat. solicitada −33.89101, lon. −60.57462).
  ERA5-Land devuelve −33.899998/−60.6 por *snapping* a su grilla nativa
  (~0.1°); NASA POWER devuelve −33.891/−60.5746.
- **Profundidad principal:** humedad de suelo 0–7 cm. Sensibilidad separada
  7–28 cm, que **no** interviene en la selección.
- **Período:** 2015-01-01 a 2025-12-31. 96 432 registros horarios ERA5-Land;
  4 018 registros diarios NASA POWER.
- **Balcarce queda fuera** de esta iteración
  (`FUTURE_GEOGRAPHIC_VALIDATION`).

---

## 4. Protocolo, features y particiones

**Target.** `stress(t) = 1` si `soil_moisture(t+3 días) < P20_train`,
comparación **estrictamente `<`**, nunca `<=`. Horizonte 3 días. `P20_train`
se calcula exclusivamente con el train autorizado del fold/etapa.

**Umbral de decisión** fijo en `0.5` para los cuatro candidatos. No se ajusta
con A, B ni C.

**Contrato de ocho features** (`pergamino_features.v1`), distinto del de v3:
humedad de suelo 0–7 cm, humedad relativa RH2M, radiación
ALLSKY_SFC_SW_DWN, lags 1/2/3 días de humedad y medias móviles causales de 3
y 7 días de humedad. T2M y PRECTOTCORR quedan fuera del protocolo principal
por criterio metodológico previo.

**Fronteras temporales por etapa** (`target_timestamp`):

| Etapa | Train autorizado | Emisiones evaluables | Targets evaluables |
|---|---|---|---|
| A | ≤ 2022-12-31 | 2015-01-07 → 2022-12-28 | 2015-01-10 → 2022-12-31 |
| B | ≤ 2022-12-31 (modelo ya congelado) | 2023-01-01 → 2023-12-28 | 2023-01-04 → 2023-12-31 |
| C | ≤ 2023-12-31 (reentrenamiento) | 2024-01-01 → 2025-12-28 | 2024-01-04 → 2025-12-31 |

**Particiones de A.** Nested temporal CV: outer `TimeSeriesSplit(n_splits=3,
gap=3)`; inner `TimeSeriesSplit(n_splits=3, gap=3)` dentro de cada
`outer_train`.

---

## 5. Prevención de fuga de información

El protocolo declara y el código verifica:

- Invariante exigido en cada partición outer e inner:
  `max(target_timestamp_train) < min(feature_timestamp_validation)`.
- `P20_train`, `sample_weight` y `StandardScaler` se ajustan **solo** con el
  train de cada fold.
- Historia cruda anterior a `feature_timestamp` sí puede alimentar
  lags/rolling (era observable en el momento real de emisión); ningún
  estadístico *aprendido* puede calcularse con filas cuyo `target_timestamp`
  exceda el corte de entrenamiento de esa etapa.
- Diciembre de 2022 no aporta filas evaluables a B, ni diciembre de 2023 a C:
  solo historia cruda.
**Regla implementada en código, NO en el protocolo** (la distinción importa:
este apartado se titula «el protocolo declara y el código verifica», y lo que
sigue solo existe en el código):

- En C, `--validate-inputs-only` está **prohibido**
  (`src/experiment_runner/controlled_daily_v4/cli.py`), y la validación de
  procedencia se difiere hasta después de la apertura durable del ledger. El
  motivo que da el propio código es que hashear el CSV completo alcanza también
  al tramo 2024–2025. El documento de protocolo **no** menciona esta regla:
  `grep -n 'validate-inputs-only'` sobre él no devuelve nada.
  Precisión necesaria: esta sesión **sí** calculó el SHA-256 de esos mismos CSV
  completos, en etapa A, donde el código lo permite explícitamente. Calcular un
  hash del archivo entero no es leer valores reservados, y ningún valor de
  2024–2025 fue inspeccionado. La restricción de C es una defensa adicional
  ligada a la apertura del holdout, no una prohibición general de hashear.

**Hecho verificado.** Los tests que ejercitan estas reglas
(`test_controlled_daily_v4_splits.py`, `..._stage_window.py`,
`..._features.py`, `..._scientific_closure.py`, entre otros) pasan: 486/486 en
el entorno reconstruido. **Esto es evidencia técnica sobre el software, no
evidencia científica sobre la hipótesis.**

---

## 6. Modelos, grillas y baselines

Cuatro candidatos, misma fecha, features, target, folds, horizonte y reglas de
imputación:

| Familia | Configuraciones | Notas |
|---|---:|---|
| Logistic Regression | 8 | `StandardScaler` fold-local, `lbfgs`, `max_iter=2000`, `C ∈ {0.01, 0.1, 1, 10}` × {sin ponderar, balanceado} |
| Random Forest | 24 | `n_estimators ∈ {100,300}`, `max_depth ∈ {4,8,None}`, `min_samples_leaf ∈ {5,20}` × 2 modos |
| HistGradientBoosting | 32 | `learning_rate ∈ {0.03,0.1}`, `max_iter ∈ {100,300}`, `max_leaf_nodes ∈ {15,31}`, `l2 ∈ {0,1}` × 2 modos, `random_state=42`, `early_stopping=False` |
| Soft Voting | sin grilla propia | Implementación propia, pesos fijos `(1/3,1/3,1/3)`, **nunca** ajustados con validación ni holdout |

Balanceo exclusivamente por `sample_weight` calculado con el train de cada
fold; nunca `class_weight`.

**Baselines.** Clase mayoritaria aprendida en train; **persistencia causal de
humedad** (`1` si `soil_moisture(feature_timestamp) < P20_train`); predictor
constante de estrés. Ninguno usa el target futuro. La persistencia causal es
el baseline formal de la compuerta de la Etapa B.

**Semillas normativas.** Modelo `42`; bootstrap `20250109`; 5 000 réplicas.

---

## 7. Métricas, soporte e indefiniciones

**Primaria:** MCC. **Secundarias:** average precision, balanced accuracy, F1,
precisión, recall, ROC-AUC, matriz de confusión, Brier, log loss, calibración
(10 bins). **Operativas:** tasa de alertas, FP/FN por 30 días, recall de
episodios y precisión de alertas.

Convenciones predeclaradas, no negociables tras observar resultados:

- Un fold monoclase se registra `NaN` **solo** en el reporte por fold; el MCC
  global se recalcula desde cero sobre la concatenación OOF.
- Average precision es `NaN` si no hay positivos reales; ROC-AUC es `NaN` si
  `y_true` es monoclase; log loss y matriz de confusión se calculan siempre
  con `labels=[0,1]`.
- **Ningún `NaN` se convierte en cero ni en un resultado favorable.**
  Serialización con envelope uniforme
  `{"value": …, "status": "defined"}` o
  `{"value": null, "status": "undefined", "undefined_reason": "…"}`.

**Soporte mínimo exigido** (protocolo, sección «Condiciones de interpretación y
soporte previas a ejecución» — numerada «16», duplicando a «16. Provenance»;
presente en la rama y **ausente de `main`**): al menos 2 de 3 folds con MCC definido por familia y al menos
4 000 de 5 000 réplicas bootstrap válidas. Si una familia no lo satisface, A
termina `NO_VALID_SELECTION`, sin candidato transferible.

**Bootstrap.** Moving block **no circular**, bloques de 30 días, 5 000
réplicas, semilla `20250109`, *segment-aware*: ningún bloque cruza el límite
entre dos `outer_val`. Limitación documentada y aceptada: sesgo de borde del
moving block clásico. Margen práctico `δ = 0.05`, fijado antes de observar
resultados.

---

## 8. Resultados

### 8.1 Etapas A, B y C

| Etapa | Estado | Artefactos | Holdout |
|---|---|---|---|
| A | **NO EJECUTADA** | ninguno | — |
| B | **NO EJECUTADA** | ninguno | custodia sin reservar |
| C | **NO EJECUTADA** | ninguno | **2024–2025 CERRADO**, ledger **NO INICIALIZADO** |

**No existe ninguna métrica, predicción, modelo ajustado ni comparación
producida por esta sesión sobre datos de Pergamino.** Ninguna afirmación de
desempeño puede sostenerse.

**Causa exacta.** La condición previa 4 de ADR-0011 —
*«Ninguna ejecución puede comenzar sin que este ADR y el protocolo detallado
ya estén mergeados en `main`»* — no está satisfecha:

- El ADR **sí** está en `origin/main`, byte-idéntico
  (`a8dabbc4b85367d5fb473195972870fb5c7de43ed5726a99910e3fed8c83d9cb`).
- El **protocolo detallado** en `origin/main` es una versión **anterior**
  (`4853fb64…` frente a `e3fa7b66…` en la rama; 42 adiciones / 2 eliminaciones).
  Le falta la sección titulada «Condiciones de interpretación y soporte previas
  a ejecución», que es precisamente donde se declaran los criterios normativos de
  soporte e interpretación bajo los que se juzgaría una corrida. Precisión: esa
  sección está numerada «16» en la rama, duplicando a «16. Provenance», que sí
  está en `main`; por eso debe identificarse por título y no por número. El
  defecto de numeración es preexistente y no se corrigió aquí porque el
  protocolo integra la identidad congelada verificada idéntica a `214735e`.
- La implementación del runner de A/B/C tampoco está en `main`: el commit
  ejecutable declarado `214735e…` **no** es ancestro de `origin/main`.

Tratar esto como satisfecho exigiría inferir una excepción, que `plan.md`
prohíbe explícitamente. Resolverlo exige un merge a `main`, fuera de la
autorización de esta sesión.

### 8.2 Estudios complementarios

Decisión de suficiencia vigente (GD-12), tomada **antes** de ejecutar y
auditada en el alcance de `sc-01`:

| Estudio | Decisión | Estado real | Justificación |
|---|---|---|---|
| R — humedad continua a t+3 | `NOT_REQUIRED` | no ejecutado | El alcance aprobado se limita a clasificación P20; no se afirma desempeño sobre humedad continua |
| H — HITL | `REQUIRED` | **no ejecutado, runner inexistente** | Es el único complemento activo; sostenerlo exigiría tres brazos y 20 eventos/seed |
| N — anomalías | `NOT_REQUIRED` | no ejecutado | No se afirma detección sobre corrupciones reservadas |
| S — robustez | `NOT_REQUIRED` | no ejecutado | El límite histórico es escasez de etiquetas más ruido, **no** ausencia de sensores |

`NOT_REQUIRED` **no** es `PASS` y **no** significa experimento ejecutado.
H permanece `REQUIRED` y sin evidencia: su ausencia es un pendiente explícito,
no una decisión de suficiencia.

### 8.3 Resultados verificados de esta sesión (técnicos, no científicos)

| Id | Resultado | Valor |
|---|---|---|
| V-01 | Suite `controlled_daily_v4` en entorno reconstruido | 486/486 en 994,22 s |
| V-02 | Gobernanza + checker formal | 48 pasadas + 14 subtests |
| V-03 | Enforcement de solo lectura por rol | 8/8 |
| V-04 | Checker formal | exit 0 |
| V-05/06 | ruff 0.16.6 y black 26.5.1 sobre archivos propios de la rama | exit 0 |
| V-07 | OpenSpec 1.13.1 `--strict`, alcance scientific-closure | 11/11 |
| V-08 | Consistencia de dependencias (23 paquetes) | compatible |
| V-09 | Identidad de procedencia de ambos CSV | exit 0 |

**Hecho verificado adicional, relevante para la identidad ejecutable.**
`src/`, `docker/` y `pyproject.toml` en `HEAD` son **byte-idénticos** al
commit ejecutable declarado `214735e42ee04f018156cd630591e798aadd8bf3`
(`git diff --stat` vacío). Entre ambos commits solo se agregaron dos archivos
de tests de gobernanza.

**Hallazgo verificado sobre el `constraints.txt` histórico.** El
`constraints_sha256` registrado en el entorno histórico
(`d47cdb8c…`) es exactamente el SHA-256 de la **representación CRLF** del
mismo archivo cuyo hash LF es `aa05b7b1…`. Es una diferencia de fin de línea
del checkout Windows, no una divergencia de contenido: los *pins* son
idénticos.

### 8.4 Resultados negativos válidos de esta sesión

Se registran como resultados, no como fallas a corregir:

1. **NASA POWER no publica licencia.** Verificado en dos páginas oficiales del
   proyecto: solo exigencia de cita. La admisibilidad se resolvió apoyándose
   en la política general de NASA ESDIS, no en un documento de POWER que no
   existe.
2. **La imagen aprobada no es inspeccionable desde este entorno.** No se
   reconstruyó ni se reclamó equivalencia.
3. **No hay almacenamiento físicamente independiente disponible.** La segunda
   copia es lógica y se declara como tal.
4. **El comando documentado de A/B/C no era invocable.** El paquete carece de
   `__main__.py`; el módulo real es `…controlled_daily_v4.cli`. Corregido en
   el runbook.
5. **El identificador del CLI de OpenSpec estaba equivocado.** El paquete npm
   `openspec` es un placeholder `0.0.0`; el real es
   `@fission-ai/openspec@1.13.1`.

---

## 9. Reproducibilidad

**Entorno de esta sesión: RECONSTRUIDO, no la imagen histórica.**

- Ruta: `/home/gus/scientific-closure-runtime/env/venv-v4`.
- Python **3.11.16**, la misma versión de parche que declara el entorno
  histórico.
- Paquetes instalados con `-c docker/experiment-v4/constraints.txt`: el set
  resultante es **idéntico** al `pip-freeze.txt` histórico (23 paquetes, tras
  excluir `pip`/`setuptools`/`wheel`, que el creador de entornos no siembra):
  numpy 2.4.6, pandas 3.0.5, scipy 1.17.1, scikit-learn 1.9.0, pyarrow 25.0.1,
  joblib 1.6.0, threadpoolctl 3.6.0, pytest 9.1.1, ruff 0.16.6, black 26.5.1.
- **No se construyó ningún contenedor.** No existe digest de imagen para este
  entorno. La imagen aprobada
  `sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af`
  **no** fue inspeccionada, exportada ni reconstruida, y **no se afirma
  ninguna equivalencia con ella**.

**Comandos exactos, salidas, códigos de salida, duraciones y hashes** quedan
en `openspec/scientific-closure/readiness-resolution-linux-2026-09-20/`:
`runtime-environment.json`, `code-identity-and-adr0011.json`,
`container-runtime-and-image.json`, `provenance-and-licence-assessment.json`,
`storage-and-backup-independence.json`, `structural-validation.json`,
`validation-results.json`, `recovery-rehearsal.json`,
`role-sandbox-enforcement.json`, `agent-capabilities.json`,
`authorizations.json`, `execution-manifest.json`, `blocker-reassessment.json`.

---

## 10. Limitaciones y amenazas a la validez

Se conservan explícitamente, sin evidencia que permita modificarlas:

1. **P20 es un proxy.** El target es un percentil de humedad de reanálisis, no
   estrés hídrico fisiológico medido. Nada en este trabajo autoriza a afirmar
   estrés fisiológico.
2. **Un solo sitio.** Pergamino. No hay portabilidad geográfica demostrada ni
   demostrable con este diseño.
3. **Alineación temporal aproximada.** ERA5-Land se agrega por día civil
   America/Argentina/Buenos_Aires; NASA POWER reporta en LST. El cruce por
   fecha es una aproximación entre dos agregaciones diarias distintas, no una
   equivalencia horaria.
4. **Latencias.** Las latencias publicadas de ambos productos pueden consumir
   o superar el horizonte nominal de 3 días. **No puede afirmarse anticipación
   operativa prospectiva** sin evidencia adicional propia.
5. **Adquisición histórica parcialmente desconocida** (§2).
6. **Los fixtures no sirven para estimar tiempos científicos reales.** Los
   994,22 s de la suite corresponden a datos sintéticos.
7. **Reanálisis, no sensores.** Pergamino es un producto de
   reanálisis/modelado. No debe describirse como evidencia de campo de
   sensores propios.
8. **Evidencia técnica ≠ evidencia científica.** 486 tests verdes acreditan el
   software, no la hipótesis.
9. **Metadatos históricos ≠ runtime verificado.** El
   `preexecution-environment.json` histórico describe un entorno que esta
   sesión **no** pudo verificar vivo.
10. **Copia lógica ≠ respaldo físicamente independiente.**
11. **Conducta de solo lectura ≠ enforcement técnico.** El enforcement ahora
    existe y está probado, pero cubre los comandos ejecutados a través del
    envoltorio, no el proceso del subagente en sí.

---

## 11. Alcance de cada afirmación y afirmaciones NO sostenidas

**Sostenido por evidencia de esta sesión:**

- La implementación congelada de A/B/C pasa su suite completa de pruebas
  sintéticas en un entorno con los *pins* exactos del protocolo.
- La identidad de ambos CSV coincide con el manifiesto versionado.
- El código de runner en `HEAD` es byte-idéntico al commit ejecutable
  declarado.
- Existe un mecanismo reproducible y probado de solo lectura por rol.
- La admisibilidad de licencias está decidida con evidencia de fuente oficial,
  con los límites del §2.

**NO sostenido — y explícitamente no afirmado:**

- Cualquier valor de MCC, AP, recall de episodios u otra métrica sobre
  Pergamino.
- Superioridad, equivalencia o inferioridad de cualquier candidato frente a
  cualquier otro o frente a la persistencia causal.
- Transferibilidad temporal de la arquitectura de v3.
- Estrés fisiológico, mejora general, anticipación operativa prospectiva,
  portabilidad geográfica o eficacia del HITL con humanos reales.
- Que la imagen histórica exista, sea íntegra o sea equivalente a algo.
- Que los términos de licencia vigentes al instante de adquisición fueran los
  verificados hoy.
- Que HU1 u otros entregables fuera de esta sesión estén completos.

---

## 12. Vínculo con la memoria técnica

- **Capítulo 2 (metodología y fundamento científico):** §§1, 4, 5, 6, 7 y 10 de
  este documento aportan el diseño causal, el contrato de features, las
  convenciones ante casos degenerados, el bootstrap *segment-aware* y las
  amenazas a la validez. El §8.1 debe citarse tal cual: el protocolo está
  formalizado y verificado en software, y **no ejecutado**.
- **Capítulo 3 (arquitectura, custodia y reproducibilidad):** §§2, 9 y 10
  aportan procedencia, identidad ejecutable, entorno reconstruido, custodia de
  entradas, ensayo de recuperación y los límites de respaldo y aislamiento.

---

## 13. Pendientes para alcanzar un terminal científico

En orden de dependencia:

1. **Satisfacer la condición 4 de ADR-0011** integrando en `main` el protocolo
   detallado vigente y la implementación de A/B/C (acción externa: PR y merge).
2. **Habilitar la inspección de la imagen aprobada**, o decidir y registrar
   formalmente que la campaña fija una identidad ejecutable nueva.
3. **Proveer un respaldo físicamente independiente**.
4. Ejecutar A una única vez; auditar; solo entonces B; solo entonces C.
5. Resolver H (`REQUIRED`) o revisar su decisión de suficiencia con auditoría.

Ninguno de estos pasos puede darse por cumplido con evidencia parcial.
