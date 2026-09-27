# Evaluacion retrospectiva exploratoria del ensamble Pergamino 2023

> **Evaluacion retrospectiva exploratoria, no independiente: 2023 ya fue
> utilizado en analisis anteriores del proyecto.**

Este informe interpreta la salida canonica de los nueve bundles demostrativos
fijos y documenta una duplicacion tecnica involuntaria de la ejecucion. No
repara campañas cerradas, no es confirmatorio y no
acredita utilidad agronomica, ahorro de agua ni probabilidades operativas.

## Respuesta ejecutiva

Los nueve artefactos estuvieron disponibles en todos los casos admisibles:
364/364 para +1, 363/363 para +2 y 362/362 para +3. Sobre este periodo, todos
los modelos y combinaciones tuvieron capacidad de clasificacion diaria, pero
el desempeño decrecio con el horizonte y la ventaja sobre persistencia no fue
general. El promedio vigente no demostro superioridad general frente a
persistencia ni frente a mayoria.

La señal mas consistente entre las comparaciones preespecificadas fue la
regresion logistica en +2 y +3: sus diferencias de MCC frente a persistencia
tuvieron IC95 pareados por encima de cero. Esto sigue siendo un resultado
exploratorio de un solo sitio/año ya usado antes, entre comparaciones multiples;
no selecciona un ganador confirmatorio.

Los scores no quedan acreditados como probabilidades operativas. La regresion
logistica obtuvo el menor Brier y mayor Average Precision entre los cuatro
metodos con score en los tres horizontes, pero las curvas de confiabilidad
muestran desajustes y poco soporte en varios bins. En particular, para el
promedio el bin 0.9--1.0 tuvo media/observado 0.958/0.913 (n=103) en +1,
0.930/0.833 (n=84) en +2 y 0.915/0.645 (n=31) en +3. Brier bajo o un calibrador
presente no bastan para declarar calibracion adecuada; `display_probability`
debe permanecer deshabilitado.

La politica justificable hoy es conservadora: conservar el promedio y umbral
0.5 como contrato vigente para recomendar **verificar el cultivo**, no para
activar riego. Es una referencia implementada, no un optimo demostrado. La
mayoria queda como comparacion secundaria: cambia deteccion por falsas alertas
y no muestra una ventaja uniforme. Elegir entre ambas exige costos de uso o
criterio experto que esta evaluacion no aporta.

Tres niveles no intercambiables resumen el alcance: (1) carga, inferencia,
linaje y cobertura acreditan **integracion tecnica**; (2) las metricas de 2023
acreditan solo **desempeno historico exploratorio no independiente** de estos
artefactos; (3) no existe **evidencia confirmatoria** nueva ni validacion
agronomica. Ningun resultado de `controlled_daily_v3` o de la campana v4 se
transfiere a estos nueve bundles.

## Identidad, ejecucion y custodia

- Rama: `feat/ensemble-retrospective-evaluation`.
- SHA ejecutable: `1e27ad46c1533dffd5b087c824f6e4cf710cbc17`.
- Protocolo SHA-256:
  `6525f639276d5f809a701336090c58cc9dce888bd49f092b97af792c90201fdf`.
- `execution_manifest.json` canonico SHA-256:
  `780386ff58b490a452d77f968e61efcd15b998a97d28de2f908ab1a346d9d33b`.
- `metrics.json` canonico SHA-256:
  `6a6a31d35196313061aa4363c98d422f4d1446a9f996d7af51cd93f762e67732`.
- Runtime de bundles:
  `C:\Repo\AAI_Hydric_Stress_ensemble_demo_runtime\pergamino-ensemble-demo-2026-09-26T034114Z`.
- Salida canonica completada (primera por orden temporal):
  `C:\Repo\AAI_Hydric_Stress_ensemble_retrospective_runtime\pergamino-ensemble-retrospective-2023-20260927T062026Z`.
- Respaldo verificado:
  `D:\AAI_Hydric_Stress_ensemble_retrospective_backup\pergamino-ensemble-retrospective-2023-20260927T062026Z`.
- Estado canonico: `completado`; inicio `2026-09-27T06:28:11Z`, fin
  `2026-09-27T06:30:35Z`; arbol Git limpio.
- Integridad: 8 archivos actuales iguales entre salida y respaldo; 0
  diferencias. `backup_verification.json` enumera los 7 archivos que existian
  antes de escribirse el propio comprobante. Los hashes de los bundles
  antes/despues fueron identicos.
- Entradas: hashes crudos coincidentes con el manifiesto; una sola pasada
  secuencial; valores 2024--2025 no fueron parseados ni agregados. Se
  conservaron 8904 filas ERA5 horarias y 371 filas NASA del intervalo
  2022-12-26..2023-12-31. El frame diario tuvo 371 dias, sin duplicados ni
  faltantes en las cuatro variables utilizadas.

### Desviacion de ejecucion unica

El controlador perdio la sesion de consola de la primera corrida mientras se
emitian advertencias repetidas. Una lectura temprana encontro el manifiesto aun
`iniciado`; un control posterior no encontro el proceso. Sin releer el
manifiesto luego de que terminara, se inicio por error una segunda corrida a
`2026-09-27T06:31:17Z`, 42 segundos despues del cierre real de la primera. La
segunda salida y respaldo se preservan en:

- `C:\Repo\AAI_Hydric_Stress_ensemble_retrospective_runtime\pergamino-ensemble-retrospective-2023-attempt2-20260927T063059Z`;
- `D:\AAI_Hydric_Stress_ensemble_retrospective_backup\pergamino-ensemble-retrospective-2023-attempt2-20260927T063059Z`.

Esto es una desviacion del requisito de corrida unica y no se presenta como
cumplimiento. No hubo cambio de SHA, protocolo, artefactos, entradas, periodo,
reglas, umbrales o semillas, ni observacion de metricas antes de lanzar la
duplicacion. Ambas corridas finalizaron `completado`, con bundles inmutables y
respaldos verificados. Sus cuatro productos cientificos son byte-identicos:

- `metrics.json`: `6a6a31d35196313061aa4363c98d422f4d1446a9f996d7af51cd93f762e67732`;
- `predictions.csv`: `9b773b186db56e35963ba6538f2f932cd6bab21487fce81568f88c8be02e9194`;
- `ui_summary.json`: `2b640b360671e03fac9f8223380395667eb8d62df9845d39a2f9f508ce660998`;
- `report.md`: `ee7ce7104793183ad48cb2a354620dfb051fb6022496cf22722176587fef10a7`.

La primera salida se declara canonica exclusivamente por precedencia temporal,
no por desempeño. La duplicacion no se usa como replica independiente ni como
evidencia adicional de incertidumbre, reproducibilidad o calidad.

### Veredicto de gobernanza postejecucion

La auditoria cientifica independiente final emitio **FAIL** para el cierre del
change: la segunda corrida comenzo despues de que la primera ya habia terminado
correctamente, por lo que no se cumplio el requisito predeclarado de ejecutar
una sola vez. La preservacion, identidad de resultados y explicacion de la
desviacion no convierten ese incumplimiento en PASS. T05 y T06 permanecen
abiertas y no se realizara una tercera ejecucion.

El auditor verifico a la vez que este FAIL es de gobernanza y no invalida la
trazabilidad del resultado numerico canonico: recomputo las 18 matrices y
MCC/Brier, y los 12 Average Precision, sin discrepancias; confirmo integridad,
cobertura, episodios, bootstrap, confiabilidad, limitaciones y
`display_probability=false`. Por ello la primera salida sigue siendo utilizable
solo como evidencia retrospectiva exploratoria no independiente, nunca como
resultado confirmatorio ni como replica doble.

## Resultados diarios sobre casos comunes

### Soporte y condiciones

| h | candidatos/comunes | cobertura | P20 | umbral | pos/neg | prevalencia | caso B | episodios | inicios det. | censura izq./der. | HGB/LR/RF disponibles | exclusiones |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | ---: |
| +1 | 364/364 | 1.0000 | 0.3131 | 0.5000 | 112/252 | 0.3077 | 14 | 14 | 14 | 0/1 | 364/364/364 | 0 |
| +2 | 363/363 | 1.0000 | 0.3131 | 0.5000 | 112/251 | 0.3085 | 23 | 14 | 14 | 0/1 | 363/363/363 | 0 |
| +3 | 362/362 | 1.0000 | 0.3131 | 0.5000 | 112/250 | 0.3094 | 31 | 14 | 14 | 0/1 | 362/362/362 | 0 |

`Caso B` significa estado no seco en `t` y observacion bajo P20 en `t+h`.
Todos los metodos de cada horizonte usan los mismos casos comunes; la
disponibilidad individual se conserva para no ocultar fallos.

`Pos` es la cantidad de targets bajo P20. AP y Brier solo corresponden a
familias y promedio; persistencia es una prediccion determinista y mayoria no
es un modelo probabilistico.

| h | metodo | N | Pos | TN/FP/FN/TP | precision | recall | F1 | MCC | AP | Brier |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| +1 | HGB | 364 | 112 | 228/24/1/111 | 0.8222 | 0.9911 | 0.8988 | 0.8560 | 0.8912 | 0.0586 |
| +1 | LR | 364 | 112 | 231/21/7/105 | 0.8333 | 0.9375 | 0.8824 | 0.8287 | 0.9472 | 0.0526 |
| +1 | RF | 364 | 112 | 230/22/5/107 | 0.8295 | 0.9554 | 0.8880 | 0.8376 | 0.8799 | 0.0629 |
| +1 | promedio | 364 | 112 | 230/22/5/107 | 0.8295 | 0.9554 | 0.8880 | 0.8376 | 0.9054 | 0.0550 |
| +1 | persistencia | 364 | 112 | 239/13/14/98 | 0.8829 | 0.8750 | 0.8789 | 0.8255 | N/A | N/A |
| +1 | mayoria | 364 | 112 | 230/22/4/108 | 0.8308 | 0.9643 | 0.8926 | 0.8447 | N/A | N/A |
| +2 | HGB | 363 | 112 | 207/44/5/107 | 0.7086 | 0.9554 | 0.8137 | 0.7310 | 0.7066 | 0.1139 |
| +2 | LR | 363 | 112 | 222/29/6/106 | 0.7852 | 0.9464 | 0.8583 | 0.7941 | 0.8756 | 0.0770 |
| +2 | RF | 363 | 112 | 208/43/6/106 | 0.7114 | 0.9464 | 0.8123 | 0.7278 | 0.7366 | 0.1042 |
| +2 | promedio | 363 | 112 | 211/40/4/108 | 0.7297 | 0.9643 | 0.8308 | 0.7566 | 0.7834 | 0.0937 |
| +2 | persistencia | 363 | 112 | 230/21/23/89 | 0.8091 | 0.7946 | 0.8018 | 0.7146 | N/A | N/A |
| +2 | mayoria | 363 | 112 | 210/41/4/108 | 0.7248 | 0.9643 | 0.8276 | 0.7520 | N/A | N/A |
| +3 | HGB | 362 | 112 | 184/66/8/104 | 0.6118 | 0.9286 | 0.7376 | 0.6155 | 0.6192 | 0.1528 |
| +3 | LR | 362 | 112 | 211/39/11/101 | 0.7214 | 0.9018 | 0.8016 | 0.7079 | 0.8153 | 0.1042 |
| +3 | RF | 362 | 112 | 191/59/7/105 | 0.6402 | 0.9375 | 0.7609 | 0.6514 | 0.6441 | 0.1407 |
| +3 | promedio | 362 | 112 | 198/52/7/105 | 0.6688 | 0.9375 | 0.7807 | 0.6804 | 0.6874 | 0.1258 |
| +3 | persistencia | 362 | 112 | 222/28/31/81 | 0.7431 | 0.7232 | 0.7330 | 0.6159 | N/A | N/A |
| +3 | mayoria | 362 | 112 | 192/58/6/106 | 0.6463 | 0.9464 | 0.7681 | 0.6634 | N/A | N/A |

Prevalencia: 0.3077 (+1), 0.3085 (+2) y 0.3094 (+3). No hubo
exclusiones ni indisponibilidad individual; esto describe este snapshot y no
garantiza cobertura futura.

## Comparaciones pareadas e incertidumbre

IC95 de `MCC(metodo)-MCC(referencia)`, bootstrap pareado no circular de bloques
de 30 dias, 5000/5000 replicas validas. Los IC son exploratorios y no corrigen
multiplicidad.

| h | comparacion | delta MCC | IC95 | replicas validas |
| --- | --- | ---: | --- | ---: |
| +1 | HGB - persistencia | 0.0305 | [-0.0187, 0.0709] | 5000/5000 |
| +1 | LR - persistencia | 0.0032 | [-0.0383, 0.0467] | 5000/5000 |
| +1 | RF - persistencia | 0.0121 | [-0.0322, 0.0652] | 5000/5000 |
| +1 | promedio - persistencia | 0.0121 | [-0.0322, 0.0652] | 5000/5000 |
| +1 | mayoria - persistencia | 0.0193 | [-0.0286, 0.0780] | 5000/5000 |
| +1 | promedio - mayoria | -0.0072 | [-0.0257, 0.0000] | 5000/5000 |
| +2 | HGB - persistencia | 0.0164 | [-0.0533, 0.0948] | 5000/5000 |
| +2 | LR - persistencia | 0.0795 | [0.0269, 0.1662] | 5000/5000 |
| +2 | RF - persistencia | 0.0132 | [-0.0536, 0.1015] | 5000/5000 |
| +2 | promedio - persistencia | 0.0420 | [-0.0221, 0.1197] | 5000/5000 |
| +2 | mayoria - persistencia | 0.0375 | [-0.0309, 0.1150] | 5000/5000 |
| +2 | promedio - mayoria | 0.0045 | [0.0000, 0.0174] | 5000/5000 |
| +3 | HGB - persistencia | -0.0004 | [-0.1276, 0.0930] | 5000/5000 |
| +3 | LR - persistencia | 0.0920 | [0.0096, 0.1945] | 5000/5000 |
| +3 | RF - persistencia | 0.0355 | [-0.0931, 0.1375] | 5000/5000 |
| +3 | promedio - persistencia | 0.0645 | [-0.0423, 0.1541] | 5000/5000 |
| +3 | mayoria - persistencia | 0.0475 | [-0.0696, 0.1372] | 5000/5000 |
| +3 | promedio - mayoria | 0.0170 | [-0.0128, 0.0681] | 5000/5000 |

Solo LR frente a persistencia en +2 y +3 tuvo limite inferior estrictamente
positivo. Los demas intervalos cruzaron o tocaron cero; ausencia de diferencia
no demuestra equivalencia.

## Deteccion, falsas alertas y episodios

El promedio frente a mayoria expresa un intercambio, no una eleccion resuelta:

| h | promedio FP/FN | mayoria FP/FN | persistencia FP/FN |
| --- | --- | --- | --- |
| +1 | 22/5 | 22/4 | 13/14 |
| +2 | 40/4 | 41/4 | 21/23 |
| +3 | 52/7 | 58/6 | 28/31 |

Hubo 14 episodios observados bajo P20, todos con inicio determinable para los
tres horizontes; uno quedo censurado a derecha. Deteccion descriptiva de
inicios (detectados/14):

| h | HGB | LR | RF | promedio | persistencia | mayoria | total/inicios det. | censura izq./der. |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| +1 | 13/14 | 8/14 | 9/14 | 9/14 | 0/14 | 10/14 | 14/14 | 0/1 |
| +2 | 10/14 | 8/14 | 10/14 | 10/14 | 3/14 | 10/14 | 14/14 | 0/1 |
| +3 | 11/14 | 6/14 | 11/14 | 9/14 | 3/14 | 11/14 | 14/14 | 0/1 |

En los casos diarios no secos en `t` que estaban bajo P20 en `t+h`, el
promedio detecto 9/14, 19/23 y 24/31; mayoria 10/14, 19/23 y 26/31;
persistencia 0 en los tres horizontes por construccion. Estos resultados
distinguen anticipacion de continuidad seca, pero no tienen intervalos de
episodios ni costos agronomicos.

## Calidad probabilistica

- Brier y AP empeoran en general al extender el horizonte. LR fue el metodo
  con score con menor Brier y mayor AP en +1/+2/+3 en este periodo.
- Los diez bins fijos, sus conteos, positivos, score medio y frecuencia
  observada estan en `metrics.json`; varios bins intermedios tienen soporte
  pequeño o nulo.
- El promedio muestra sobreestimacion en su bin superior, creciente hacia +3.
  HGB +3 es especialmente ilustrativo: bin 0.9--1.0, n=46, score medio 0.924
  y frecuencia observada 23/46=0.500.
- Esto no autoriza interpretar un score individual como riesgo agronomico ni
  habilitar su presentacion como probabilidad acreditada.

## Recomendacion para producto, UI y memoria

Para la demostracion, presentar por separado:

1. procedencia y calidad de datos;
2. horizonte, scores por familia y disponibilidad;
3. promedio contractual y alerta a 0.5;
4. votos/acuerdo como informacion distinta, nunca como porcentaje de riesgo;
5. observacion posterior bajo P20;
6. revision humana y su efecto real (si no hubo recalibracion, decirlo).

La UI puede consumir `ui_summary.json` con su version de esquema, pero debe
mostrar permanentemente: “historico exploratorio no independiente”, sitio,
periodo, horizonte, N/prevalencia, target de baja humedad y la accion
“verificar cultivo”. Debe mantener `display_probability=false`. Las metricas
historicas no son certeza de una prediccion individual.

Recomendacion concreta para la siguiente entrega: integrar primero una vista
read-only de evidencia historica por horizonte desde `ui_summary.json`, con
una tarjeta de alerta actual separada de un panel de acuerdo de modelos y de
la observacion posterior. No cambiar promedio por mayoria: mostrar el
intercambio FP/FN y dejar la eleccion de politica pendiente de criterio
externo de costos/uso.

## Limitaciones

- Un sitio, un año y datos ya usados antes: no hay independencia confirmatoria.
- El target es baja humedad contra P20 congelado, no estres fisiologico.
- Disponibilidad diaria retrospectiva asumida; latencia operativa no validada.
- Sin costos agronomicos, intervencion, ahorro de agua ni evaluacion de riego.
- Dependencia entre modelos; unanimidad no implica alta probabilidad.
- Episodios descriptivos sin IC; comparaciones multiples exploratorias.
- Advertencias repetidas de scikit-learn sobre nombres de features no
  alteraron identidades, scores ni estado, pero deben conservarse en el log.

## Artefactos fuente

En la salida canonica: `execution_manifest.json`, `predictions.csv`,
`metrics.json`, `ui_summary.json`, `report.md`, `backup_verification.json` y
`restricted_inputs/`. El log de la ejecucion duplicada esta junto a su carpeta
de salida con sufijo `.log`. Este informe referencia esos artefactos; no
duplica las predicciones fechadas ni las curvas completas.

Las tablas agregadas versionadas, derivadas sin leer predicciones, estan en
`docs/research/tables/ensemble-retrospective-2023/`. Sus CSV conservan la
precision numerica del JSON fuente y representan valores no disponibles como
campo vacio mas `status`/`reason`, nunca como cero. El README de ese directorio
registra hashes, identidad ejecutable/protocolo y comando de regeneracion.
