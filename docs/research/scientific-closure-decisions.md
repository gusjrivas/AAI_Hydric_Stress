# Cierre científico: decisiones preejecución (2026-09-17)

Estado: DISEÑO CONGELADO ANTES DE IMPLEMENTAR. Autoriza preparación y tests con
fixtures, NO ejecuciones científicas, apertura de B/C, inicialización de ledgers
definitivos, tags ni merge. Prevalece sobre descripciones anteriores contradictorias.
HU2/HU3/HU4/HU5/HU7/HU8; capacidades data-ingestion, data-quality,
predictive-modeling, human-feedback, experiment-runner; CRISP-DM preparación,
modelado y evaluación. Hipótesis, alcance y arquitectura se conservan.
Impacto experimental: controles y métricas v4; nuevas evaluaciones separadas.
controlled_daily_v3 y sus resultados permanecen inmutables.

**Nota de integración (2026-09-20).** El encabezado anterior se conserva sin
modificación: describe el alcance de la autorización vigente el 2026-09-17, cuando
el diseño se congeló antes de implementar. La integración de este documento y del
protocolo vigente en `main` está autorizada por separado, como prerrequisito de la
condición 4 de ADR-0011, y los runners de A/B/C ya están implementados y verificados
con fixtures sintéticas. Esa integración **no** altera ninguna decisión congelada de
este documento y **no** autoriza ejecutar A, B ni C, abrir el holdout 2024–2025 ni
inicializar el ledger definitivo: esas restricciones siguen íntegramente vigentes.

## Contrato v3 / v4 (H02)
v3 utiliza 15 variables temporales (lags 1,2,3 y rolling 3,7 de humedad,
radiación y humedad relativa), include_current=false. Las medias móviles sí
incluyen el día actual. v4 utiliza ocho features ordenadas: soil_moisture,
RH2M, ALLSKY_SFC_SW_DWN, lag1, lag2, lag3, roll_mean_3, roll_mean_7.
Incluye valores actuales; sus transformaciones temporales se concentran en
humedad. No es réplica directa de v3. Una diferencia v3→v4 no es atribuible
exclusivamente al sitio, período o familia de modelo. La comparación interna
v4 exige este mismo contrato, fechas y target para todos sus candidatos.
La emisión supone disponibilidad de todas las observaciones diarias de t,
al cierre de ambos productos, no disponibilidad instantánea en campo.

## Soporte e indefiniciones (H03/H10)
Primaria: MCC. Tuning y congelamiento exigen al menos 2 folds válidos de los
3 predefinidos; se registra cada MCC, los indefinidos y sus soportes.
Train monoclase vuelve ese fold no evaluable; no se ajusta el estimador.
Si ninguna configuración satisface soporte, NO_VALID_SELECTION; no se escoge
la primera configuración. Fallo en cualquier familia del diseño comparativo
bloquea selección global: no se elimina un rival para favorecer otro.
Bootstrap: 5000 réplicas solicitadas, al menos 4000 válidas (80%). Para tests
reducidos se conserva 80%, redondeado hacia arriba. Cero o soporte insuficiente
no producen intervalo interpretable ni aprobación. Se registran cantidad y
proporción descartada. No cambiar estos mínimos después de observar resultados.
Una evaluación monoclase con entrenamiento válido conserva todas las
predicciones y métricas definibles, matriz 2x2, Brier y log loss.
MCC/AUC y balanced accuracy con y_true monoclase son indefinidos por convención;
AP sin positivos también. Precisión sin predicciones positivas y recall sin
positivos reales son indefinidos. JSON usa value:null, status:undefined,
undefined_reason y soporte. B monoclase nunca valida; C no se reabre.
~~MCC con predicción constante e y_true biclase conserva la convención 0.~~
Corrección preejecución 18/09, motivada por revisión matemática y fixtures:
también es indefinido por denominador nulo; se serializa null con razón explícita.
No se observaron datos reales ni B/C para esta corrección.
La selección global requiere además al menos dos outer folds con MCC definido
en cada familia; el global concatenado no sustituye ese soporte.

## Inicio de episodios (H06)
Métrica descriptiva secundaria; nunca selecciona candidatos ni altera B.
Recibe fechas de emisión, fechas objetivo (=emisión+3 días), etiquetas y
alertas ordenadas, únicas, con segmentos explícitos. Una racha de targets=1
en fechas objetivo consecutivas define un episodio. No unir folds distintos
ni atravesar huecos. Una racha que comienza en el primer dato del segmento
o tras un hueco es censurada por izquierda: reportarla, no contar su inicio
como conocido. Para cada episodio con inicio conocido, usar la primera alerta
cuya fecha objetivo cae en él. Si emisión < inicio: anticipado; si emisión
>= inicio: detección no anticipada (desglosar mismo día y posterior); sin alerta:
no detectado. Lead = inicio - emisión, firmado en días calendario; mediana
solo entre episodios detectados. No contar cada día como episodio independiente.
Aviso falso: alerta cuya fecha objetivo tiene etiqueta 0; reportar días y
rachas contiguas de avisos falsos, sin confundirlos con riego innecesario.
Reportar n_días, positivos, episodios totales/evaluables/censurados, anticipados,
mismo día, posteriores y no detectados. Tasas y lead sin denominador quedan
indefinidos. episode_recall sigue siendo detección de cualquier día, nunca
evidencia de anticipación al inicio. A usa métricas por fold; el agregado OOF
respeta sus segmentos y cambios fold-local del P20.

## Custodia B (H07/H15)
Clave fija protocolo/sitio/profundidad/período 2023, independiente de candidato,
commit, output e intento. Un único registro persistente externo, con reserva
exclusiva ANTES de cargar valores B; candidato/configuración/hash/commit/imagen/
fuentes/instante quedan asociados al primer intento. Cambiar candidato o output
no habilita otro intento. Un fallo posterior a reservar bloquea automáticamente.
Recuperación permitida: SOLO leer artefactos completos con hashes verificados,
registrando un evento explícito y motivo técnico. Nunca reentrenar en recuperación.
Un intento incompleto exige análisis humano externo y documentado; no se libera
ni borra por CLI. No inicializar ningún registro científico en esta intervención.
Custodia única y backups son precondiciones operativas, no protección contra
edición manual maliciosa de registros. Mantener mismo commit e imagen A/B/C.

## Evaluaciones complementarias (H08/H09/H12/H13/H14)
Estado: DISEÑADAS, RUNNERS NO IMPLEMENTADOS, NO EJECUTADAS.
Quedan separadas de A→B→C y nunca consumen 2023–2025 ni Balcarce.
Usan solo Pergamino 2015–2022 ya autorizado para desarrollo; NO son validación
externa independiente. No informan selección de A ni ajuste posterior de B/C.
Seeds [0,1,2,3,4]; seeds no representan poblaciones independientes.
Artefactos nuevos por protocolo: configuración, commit/imagen/dependencias,
hashes fuente/derivado, fechas, semillas, predicciones por fecha, métricas,
soporte, advertencias y límites. Nunca sobrescribir v3.

### R: humedad continua t+3
ID auxiliary_soil_regression_v1. Target humedad 0–7cm observada de reanálisis
en t+3, m3/m3; emisión tras cierre de t; mismo contrato de ocho features v4.
Train targets <=2020-12-31; diagnóstico 2021 (emisiones 01-01..12-28);
evaluación 2022 (emisiones 01-01..12-28). Invariante última fecha objetivo
train < primera emisión de evaluación. No tuning ni elección usando 2021/2022.
Modelos fijos mínimos: StandardScaler+Ridge(alpha=1), RandomForestRegressor
(n_estimators=100,max_depth=8,min_samples_leaf=5,n_jobs=1,random_state=seed).
Baselines: persistencia de humedad actual y media de humedad objetivo de train.
MAE y RMSE en m3/m3, delta pareado frente a persistencia, n y fechas; bootstrap
30 días, 5000 réplicas, seed 20250109 y soporte de esta política. Sin mezclar
escalas con MCC/Brier. Reportar por año y semilla, sin declarar ganador global
de clasificación. Calendario diario preservado, forward-fill causal solo en
entradas, nunca target; no bfill, excluir objetivos ausentes y registrar soporte.
Scaler solo train. No clips ni ajuste posterior para mejorar errores.
Limitaciones: reanálisis, autocorrelación, un sitio, valores futuros no
fisiológicos; no equivale a clasificación P20.

### H: HITL prospectivo
ID auxiliary_hitl_v1. Inicial: RF fijo (100 árboles,max_depth=8,min_samples_leaf=5,
n_jobs=1,seed) sobre targets 2015–2020. P20 de ese train permanece congelado.
Adquisición de feedback durante 2021; cierre de recalibración tras maduración
de targets <=2021-12-31; evaluar emisiones 2022-01-01..2022-12-28, tras disponer
de esa maduración. Misma matriz de ocho features y fechas para tres brazos:
modelo congelado; refit con datos 2015–2021 sin correcciones; refit idéntico con
correcciones. No usar filas de recalibración en evaluación.
Presupuesto 20 eventos por seed: muestreo temporal estratificado de 2021,
10 alertas y 10 no-alertas; si estrato insuficiente, reportar no evaluable,
sin completar mirando 2022. Selección solo con predicciones emitidas en 2021.
Escenario simulado: invertir con stream independiente 10% de etiquetas de
entrenamiento de 2021 antes del refit; revisor simulado restituye etiqueta
limpia en las 20 fechas revisadas, dejando confirmaciones sin cambio.
Registrar todos los eventos, etiqueta original/corregida, model_id, timestamps
de emisión/target/validación y origen=simulado; validated_at >= fin del día
objetivo. No afirmar feedback humano genuino ni eficacia agronómica.
Feedback real futuro necesita protocolo de revisión y procedencia propia.
Métricas MCC, AP, Brier, F1, FP/FN y episodios; delta con/sin correcciones
aísla correcciones, delta refit/congelado combina actualización temporal.
Sin seleccionar semillas favorables, sin adaptar presupuesto por resultados.
Limitaciones: simulación de error, pocas correcciones, presupuesto artificial.

### N: anomalías reservadas
ID auxiliary_anomalies_v1. IsolationForest(contamination=.05,n_estimators=100,
random_state=seed), fit solo entradas 2015–2020. Evaluación reservada 2022;
2021 no interviene. Variables físicas humedad/RH/radiación, escalas solo train.
Dos condiciones aparte del limpio: spikes en 5% de fechas, ±3 sigma_train
(signo aleatorio); bloques stuck de 3 días que cubren hasta 5% de fechas,
copiando el último valor anterior. Elegir posiciones con stream independiente
por seed; no solapar bloques, no inventar días ni usar valores futuros.
Inyectar solo evaluación; etiquetas de corrupción conocidas, no etiquetas de
anomalías reales. Registrar columna, fecha, tipo, magnitud, seed y valor previo.
Contar TP/FP/TN/FN, precisión, recall/detección, tasa de falsas alarmas y
soporte por tipo y en limpio. Sin positivos, recall indefinido; sin avisos,
precisión indefinida. La demostración existente se preserva como funcional.
No interpretar extremos inyectados como validación de fallas reales de sensores.

### S: escasez y ruido, matriz de cuatro condiciones
ID auxiliary_robustness_v1. RF fijo de R pero clasificador, P20 limpio congelado,
train 2015–2020, evaluación 2022; misma evaluación/target por seed. Sin tuning.
1. Base: todas las etiquetas y mediciones disponibles.
2. Etiquetas: conservar 50% del train elegible mediante coverage estratificado,
   sin borrar mediciones ni alterar features/P20.
3. Mediciones: enmascarar bloques de 3 días hasta 10% de días del test, mismas
   posiciones para las tres variables; no tocar referencia objetivo.
4. Ruido: gaussiano de sigma=0.3*sigma_train limpio en entradas test solamente.
No cruzar factores: cuatro condiciones, cinco seeds, veinte evaluaciones.
Generar features DESPUÉS de perturbar entradas, sobre grilla diaria completa.
Forward-fill causal con historia train; registrar máscara, cobertura y edad
de última observación; target jamás imputado. Comparar sobre fechas comunes,
registrar toda exclusión. Persistencia recibe la misma observación alterada.
Métricas MCC/AP/Brier/F1/FP/FN y episodios; delta pareado contra base e
intervalos por bloques como R. No confundir intensidad hipotética con ruido
real ni coverage/recent históricos con falta de mediciones.
