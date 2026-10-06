$ErrorActionPreference = 'Stop'
if ((git branch --show-current) -ne 'feat/hu6-backend-soporte-ui') { throw 'Rama inesperada' }
$utf8 = New-Object System.Text.UTF8Encoding($false)
function ReadDoc([string]$relative) { return [IO.File]::ReadAllText((Join-Path (Get-Location).Path $relative)).Replace("`r`n","`n") }
function WriteDoc([string]$relative,[string]$content) { [IO.File]::WriteAllText((Join-Path (Get-Location).Path $relative),$content,$utf8) }
$p='openspec/changes/add-daily-multihorizon-predictors/design.md'
$s=ReadDoc $p
$start=$s.IndexOf('Soporte mínimo propuesto:')
$end=$s.IndexOf('El score de decisión es calibrated')
if ($start -lt 0 -or $end -le $start) { throw 'Sección no encontrada' }
$replacement=@'
### Qué se evalúa y qué no acredita
El evento es humedad observada bajo el umbral congelado, proxy relativo; no
diagnóstico fisiológico. La referencia de evaluación son mediciones futuras
observadas, sin imputar targets ni sustituirlos por feedback selectivo.
Una salida predict_proba, buena clasificación, mejor Brier o mejor log-loss
no demuestran por sí solos calibración. Las dos últimas métricas combinan
calibración y capacidad discriminativa. Repetir cinco semillas mide sensibilidad
del entrenamiento; no agrega cinco muestras independientes ni más días observados.

### Manifiesto previo obligatorio
Antes del ajuste, el manifiesto MUST fijar también:
- población, sensor/sitio, procedencia, horizonte, evento y uso pretendido;
- fecha de congelamiento, hash de datos y declaración de exposición previa;
- diez intervalos de probabilidad de igual amplitud (incluyendo 1 en el último),
  minimum_bin_count y minimum_class_count, ambos enteros positivos;
- tolerancias numéricas epsilon_ece y epsilon_bin en (0,1), expresadas en
  puntos de probabilidad, con justificación de la precisión útil para la UI;
- minimum_coverage en (0,1], proporción mínima de casos en intervalos con soporte;
- número mínimo de bloques temporales distintos que se exige para evaluar;
- método de incertidumbre por bloques temporales, longitud de bloque en días,
  tratamiento de huecos, número de réplicas y semilla de remuestreo;
- ventanas de estabilidad temporales no solapadas dentro de evaluación, con
  fechas fijadas y los mismos criterios de soporte y tolerancia;
- semilla de despliegue elegida de antemano; nunca elegir la de mejor resultado.

Los valores de soporte, tolerancia y longitud de bloque requieren justificación
usando el uso previsto, conocimiento del dominio o únicamente datos de
entrenamiento. Este change NO inventa una tolerancia universal ni considera
20 casos por clase garantía suficiente. Esos valores quedan como decisión
explícita de la tarea 1, previa al primer ajuste. Manifiesto incompleto bloquea
calificación: assessment_result=insufficient_evidence, motivo
incomplete_assessment_plan. No inferir valores por defecto para obtener aprobación.

### Evaluación directa y dependencia temporal
Publicar por horizonte: gráfico de confiabilidad, probabilidad media,
frecuencia observada, diferencia firmada, número de casos/eventos y banda de
incertidumbre por intervalo. Mostrar también intervalos vacíos y no respaldados.
Informar F1, precisión, recall, MCC, AP, prevalencia, Brier y log-loss; comparar
modelo calibrado, raw, climatología ajustada en entrenamiento y persistencia
sobre exactamente las mismas fechas. Definir clipping numérico de log-loss
en el manifiesto, igual para todos; no ocultar fallos de baselines.

ECE se define como suma de n_b/N por abs(frecuencia_b - probabilidad_media_b)
sobre los intervalos no vacíos del conjunto evaluado. Es diagnóstico dependiente
del agrupamiento, no prueba suficiente por sí solo ni garantía punto a punto.
No omitir intervalos de poco soporte del cálculo para mejorar la cifra.
Coverage es la proporción de observaciones en intervalos con minimum_bin_count;
publicar además el rango de probabilidades respaldado por esos intervalos.

Estimar incertidumbre con remuestreo por bloques de días contiguos de los pares
(probabilidad, resultado), conservando dependencia temporal. No usar bootstrap
iid de filas ni contar semillas o horizontes como observaciones independientes.
Usar nivel nominal 95%; el algoritmo debe construir límites superiores
simultáneos para ECE y errores absolutos de intervalos respaldados, en la familia
completa de horizontes, semillas y ventanas evaluadas. Predeclarar construcción
(por ejemplo, corrección de multiplicidad sobre intervalos por bloques), réplicas
y supuestos. Si la serie no permite estimarlos de forma estable con los bloques
mínimos predeclarados, declarar insufficient_evidence, no bandas de ancho cero
como certeza. Verificar el estimador de incertidumbre con fixtures conocidos.

### Regla de presentación, por horizonte
Para calificar un horizonte, todas las semillas previstas, el período completo
y cada ventana de estabilidad predeclarada deben ser evaluables. Se requiere:
1. Soporte por clase, bloques y coverage al menos iguales a lo predeclarado.
2. Límite superior de ECE <= epsilon_ece y de cada error absoluto por intervalo
   respaldado <= epsilon_bin. Que una banda amplia incluya la diagonal NO basta:
   se necesita acotar el error dentro de la tolerancia, no solo no detectar error.
3. Como controles adicionales de utilidad: Brier calibrado menor que climatología
   y no mayor que raw, y log-loss calibrado no mayor que raw.

Estos controles acotan una afirmación de calibración agrupada en el dominio y
períodos evaluados. No acreditan todas las condiciones agronómicas ni probabilidades
fuera de rangos respaldados. La inferencia solo publica porcentaje cuando el
horizonte califica, el bundle exacto coincide, la procedencia/sitio/unidades son
compatibles y el intervalo de su probabilidad tiene soporte en las evaluaciones
requeridas. Fuera de ese rango, display_probability=null con motivo
unsupported_probability_range; no extrapolar la calificación.

assessment_result=passed solo cuando se cumplen todos los requisitos.
Con evidencia suficiente pero tolerancias/controles incumplidos: failed.
Con soporte, plan o incertidumbre insuficientes: insufficient_evidence.
Sin evaluación: not_evaluated. No transformar ausencia de evidencia en éxito.
Salvo passed compatible, display_probability=null y probability_status=not_qualified.
Con passed compatible: probability_status=development_assessed y evidencia enlazada.
El informe conserva motivos, límites y casos no evaluables, además de predicciones
por fecha, hashes de modelos/calibradores, manifiesto y comando reproducible.

Solo es evaluación de desarrollo. Datos sintéticos acreditan funcionamiento,
no probabilidades reales. Una afirmación de validación externa exige datos reales
independientes y autorización/protocolo separado, sin reutilizar holdouts
protegidos. Ni esta corrección ni su implementación autorizan abrirlos.
Modificar el plan después de examinar resultados exige nueva versión y declarar
exploratorios los datos ya consultados; cambiar versión no los vuelve independientes.

'@
$s=$s.Substring(0,$start)+$replacement+"`n"+$s.Substring($end)
$s += @'

## Referencias y trazabilidad de la corrección
- [scikit-learn: calibración, curvas y límites de Brier/log-loss](https://scikit-learn.org/stable/modules/calibration.html).
- [Dimitriadis, Gneiting y Jordan: diagramas de confiabilidad e incertidumbre](https://arxiv.org/abs/2008.03033).
La elección específica de bloques, tolerancias y regla de aceptación es una
propuesta de diseño operacional del proyecto; no un umbral universal de esas
referencias. HU4, Épica 2, predictive-modeling; CRISP-DM modelado/evaluación.
No cambia controlled_daily_v3/v4, configuraciones formales, hipótesis, alcance,
capas de arquitectura ni resultados HU7/HU8. Aporte a capítulos 2 y 3: límites
de la evidencia y publicación honesta de probabilidades.
'@
WriteDoc $p ($s+"`n")
$p='openspec/changes/add-daily-multihorizon-predictors/specs/predictive-modeling/spec.md'
$s=ReadDoc $p
$s += @'

### Requirement: Calificación directa con incertidumbre y alcance limitado
El sistema MUST aplicar el manifiesto y la regla de presentación de design.md:
tolerancias previas, soporte por clase e intervalo, cobertura, estabilidad y
límites de error con incertidumbre temporal. MUST NOT acreditar calibración
usando únicamente Brier/log-loss, una diagonal dentro de una banda amplia o
repeticiones de semillas. MUST evaluar el proxy observado por horizonte sin
reemplazar targets por opiniones humanas ni datos sintéticos.

#### Scenario: Métricas globales mejoran pero calibración directa falla
- **GIVEN** soporte suficiente y mejor Brier/log-loss que las referencias
- **WHEN** un límite de error supera la tolerancia predeclarada
- **THEN** assessment_result=failed y display_probability=null.

#### Scenario: Plan no completado antes del ajuste
- **WHEN** faltan tolerancias numéricas, soporte o método de incertidumbre congelados
- **THEN** se bloquea la calificación con incomplete_assessment_plan, sin defaults favorables.

#### Scenario: Incertidumbre o cobertura insuficientes
- **WHEN** faltan bloques temporales o coverage no alcanza el mínimo
- **THEN** assessment_result=insufficient_evidence y no se publica porcentaje.

#### Scenario: Banda amplia compatible con calibración perfecta
- **WHEN** la banda incluye error cero pero su límite superior excede epsilon_bin
- **THEN** no se califica ese horizonte por ausencia de evidencia de precisión suficiente.

#### Scenario: Probabilidad en un intervalo no respaldado
- **GIVEN** un horizonte aprobado con cobertura parcial declarada
- **WHEN** una inferencia cae en un intervalo sin soporte exigido
- **THEN** display_probability=null con unsupported_probability_range.

#### Scenario: Varias semillas sobre los mismos días
- **WHEN** se agregan los resultados de las cinco semillas
- **THEN** se informa sensibilidad sin multiplicar el tamaño de la muestra observada.

#### Scenario: Evaluación solo con datos sintéticos o ya explorados
- **WHEN** se genera el informe de calibración
- **THEN** se declara ese alcance y no se acredita validación independiente en condiciones reales.
'@
WriteDoc $p ($s+"`n")
$p='openspec/changes/add-daily-multihorizon-predictors/tasks.md'
$s=ReadDoc $p
$s=$s.Replace('Versionar contrato y manifiesto de evaluación ANTES de ajustar modelos.','Versionar contrato y manifiesto completo ANTES de ajustar: justificar y fijar tolerancias, soporte, cobertura, bloques, ventanas, multiplicidad y semilla de despliegue.')
$s += @'
- [ ] 10. Implementar diagnósticos directos por intervalo e incertidumbre temporal con límites simultáneos; comprobarlos con fixtures de calibración conocida y mala calibración.
- [ ] 11. Probar mejora de Brier sin aprobación directa, banda amplia, plan incompleto, soporte insuficiente, ventanas inestables y rango sin respaldo.
- [ ] 12. Publicar informe reproducible por horizonte con fechas, predicciones, conteos, intervalos, comparación de referencias y límites de generalización.
'@
WriteDoc $p ($s+"`n")
$p='openspec/changes/add-producer-forecast-api/api-contract.md'
$s=ReadDoc $p
$s += @'

## Evidencia de calibración y publicación (corrección del criterio)
assessment_reference identifica un informe inmutable con assessment_result:
not_evaluated | insufficient_evidence | failed | passed, motivos, versión/hash
del manifiesto, artefactos evaluados, dominio, rangos respaldados y diagnósticos
con incertidumbre definidos en add-daily-multihorizon-predictors/design.md.
No alcanza un Brier/log-loss favorable para obtener passed.
La respuesta de un slot available agrega probability_reason_code nullable:
not_evaluated | incomplete_assessment_plan | insufficient_evidence |
calibration_criteria_failed | unsupported_probability_range |
incompatible_assessment. Es null si el porcentaje se publica.
En unavailable es null: reason_code ya explica la indisponibilidad del predictor.
Un informe passed no habilita porcentajes fuera de su rango/dominio ni para
otro bundle. En esos casos probability_status=not_qualified y
display_probability=null, aunque la alerta binaria siga disponible.
El ejemplo de slot disponible anterior presupone probability_reason_code=null.
development_assessed significa evidencia limitada al desarrollo, no validación
agronómica o externa. El detalle del informe debe poder recuperarse mediante
GET /sensors/{sensor_id}/assessments/{assessment_reference}, de solo lectura,
con el mismo aislamiento y política de acceso; desconocido o de otro sensor:404.
No devolver rutas locales ni permitir acceso arbitrario a archivos.
'@
$s=$s.Replace('"probability_status": "development_assessed",','"probability_status": "development_assessed",'+ "`n" + '  "probability_reason_code": null,')
WriteDoc $p ($s+"`n")
$p='openspec/changes/add-daily-multihorizon-predictors/proposal.md'
$s=ReadDoc $p
$s += @'

## Corrección del criterio de evidencia
Se exige evaluación directa de calibración con incertidumbre temporal, soporte,
cobertura y estabilidad por horizonte. Brier/log-loss quedan como controles
complementarios. Tolerancias numéricas y método estadístico se justifican y
congelan antes del ajuste; hasta completar ese plan no hay calificación.
No cambia protocolos formales ni autoriza nuevos experimentos HU7/HU8.
'@
WriteDoc $p ($s+"`n")
$p='docs/seguimiento-tareas.md'
$s=ReadDoc $p
$pos=$s.IndexOf("`n")
$note=@'

## 2026-09-18 — Corrección de evidencia de calibración (solo specs)
HU4/HU6; predictive-modeling y architecture-integration; CRISP-DM modelado,
evaluación de desarrollo e integración. Se corrige el criterio de publicación:
Brier/log-loss no bastan; se exigen diagnósticos directos, incertidumbre temporal,
soporte, cobertura y tolerancias previas. API distingue motivos de no calificación.
No se ejecutaron experimentos ni se modificaron código, protocolos v3/v4,
configuraciones formales o resultados históricos HU7/HU8. Hipótesis, alcance
y arquitectura intactos. Documentación propuesta para capítulos 2 y 3.
'@
WriteDoc $p ($s.Substring(0,$pos+1)+$note+"`n"+$s.Substring($pos+1))

