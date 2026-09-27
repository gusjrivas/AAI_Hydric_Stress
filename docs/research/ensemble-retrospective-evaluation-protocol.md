# Protocolo congelado: evaluacion retrospectiva del ensamble 2023

> **Evaluacion retrospectiva exploratoria, no independiente: 2023 ya fue
> utilizado en analisis anteriores del proyecto.**

Este protocolo se congela junto con el evaluador antes de observar sus
metricas reales. No es un preregistro prospectivo ni repara la campana cerrada
`controlled_daily_v4_external_pergamino`.

## Objeto y periodo

Se evaluan los nueve bundles del run
`pergamino-ensemble-demo-2026-09-26T034114Z`: tres familias (regresion
logistica, Random Forest e HistGradientBoosting) por horizontes +1/+2/+3.
Antes de inferir se exige `run_manifest.status=completado`, carga exacta con el
loader vigente, identidades/hashes consistentes, sensor, familia, horizonte,
features, ventanas, P20 y umbral 0.5 contractuales, y entorno exactamente
compatible.

Identidades predeclaradas, obtenidas de las fuentes primarias del runtime antes
de la evaluacion:

- `run_manifest.json`: `8d9fd2614ca98c9e73ab65bc6627f99efc3b7ddc7d2ff0a456d53a0e21e8c943`.
- ensamble +1: `39d34b120ee1c7f2e0240e87b624e5b1210559f586c6567edfb981cdc14217f4`;
  +2: `5eac8f49d2bb49cb158e225181041cbca2ebc95f54cd4a228d17fc5136e5523a`;
  +3: `dbbd1605bf74308e1522a5c0f9ce83ee0cccc6a77ca58bc03a9adc3e77c46097`.
- snapshot diario contractual: `491cedeebd7e66e78e2a00be256caed628c014b60ea9b51931a09332ca605312`.

| h | familia | modelo | calibrador | contrato |
| --- | --- | --- | --- | --- |
| 1 | HGB | `161ed26f57f541987001987fe968bea441640491be4879cb92ac61af227f0b4c` | `9ef458ec9fd3f295a0dff73bc284031ecca1e501c630acbc2300c67ecd59d7eb` | `3280d3b9c5b78c31b44b10e9ceacf268ceb74181453bf5a582ab53f8ba8214af` |
| 1 | LR | `fa405ca5778bc33b6c177ac5b8bbf28e88f11cafb7457573e5ed9671bbf34fe0` | `62a5d10d307a64970041d920190dbe29f099818f4cc0d5739ddd503fb87c5b13` | `b3d02168c579ab212157c157ec25393ad0a106aacbec6bf07e4a0fb92a451b42` |
| 1 | RF | `a06f6841aa66a596378a30e57ca5f664976a24c2d053130b8ce650b018548ea7` | `1a5e7b810b9fbb393284aef193b6536dd3eb3bf9efcd307c8695b741b0eaa117` | `f7a266d0a2b35ee05cb93a8090ee5868070f0b7987f477e7d1559233c034f900` |
| 2 | HGB | `c21f51664eb053d5d2ee8eb9a8fb66aedc8656a4ae36334edbf896bdacaa102e` | `7fc5e3abc970182e0a7184e4e049d05bae092a5edf92225fff8509694ce3fad8` | `5a986429bd0aef24df31af526c5bf280da7c8cf9c7353797205b8408609c0bfa` |
| 2 | LR | `b15ad8741615af7c833fd5368e81c21247ebae5846a3e2c7a5f5a1239fbf43d3` | `66f710a81728700b78828c88fd1b17dda954cdb94a846d3df592aa7c8841142f` | `97e672c0840e306b936275cdfd3db1dfbd329361b1436a0d2359a188d5dde322` |
| 2 | RF | `60e34c9a9d1dd94a1aeabb77d6aa7b08a08cfc5f82b865bc66243a238046478b` | `d378e54f503610cfe5388bddaa66c82a60f615478df3d98a0900c64f1cb80d18` | `d1bd12d0316262c56264ff0b7f5d4eab84fedd38dd0599affb5aa4f4e824c34f` |
| 3 | HGB | `e191ee2c18c6bbb60c2e0ee81398a8e5cf5ba9b5eb1f75b98f62b3884baf1468` | `480e167666b1915fbba647ec4134a009091f20c54f1b26183561908d63b182db` | `19c7d909b7023a0b08063e541ecc59bfe697fb74bad1f6571f11a9898751a8e0` |
| 3 | LR | `b41b604063da408a5214efece49de930787c11842ba06b136b8e0307b26e1ff2` | `81c3ab0014b0ec8f5f6755b09b6fc2e6a39ad253f8fb17d9cfb1464f256e8fb1` | `f89750f5d2e4ca693ff0e392e005b319537e0dcb08030f2176c92c167a73a2e0` |
| 3 | RF | `c1aa9ecfbcf620e83c632fad15a39255b3538fa9f12cc8b638ac88c113dfb251` | `3a15ac2cdff13306f1100f97adc75387aa265f8b70c0dfd9fb2d24a97689fc78` | `55725056ac9848bd95236a39a35ac99cade1b9a0044586afbfece9d96c6044a9` |

La carga falla si no coinciden simultaneamente el manifiesto congelado, sus
hashes declarados, los bytes de cada archivo, las identidades de ensamble, el
snapshot, los cortes y `trained_through=2021-12-31` /
`calibrated_through=2022-12-31`.

Emisiones admisibles: 2023-01-01 hasta 2023-12-31 menos el horizonte, ambas
fechas inclusive; target observado `soil_moisture(t+h) < P20` y siempre en
2023. Lookback minimo: 2022-12-26..2022-12-31 (seis dias previos mas el dia de
emision forman la ventana maxima de siete). Se asume disponibilidad
retrospectiva de observaciones diarias; no se acredita latencia operativa.

Los CSV mixtos se recorren secuencialmente. Solo se interpreta la fecha
estructural de filas fuera de rango; sus mediciones no se parsean ni agregan.
Se registra honestamente que sus bytes fueron leidos. El snapshot restringido
se crea antes de pandas. El hash de fuente se calcula incrementalmente en esa
misma pasada; se registran tamano y `mtime_ns` inicial/final y cualquier cambio
bloquea la ejecucion. Luego se reutilizan loaders, agregacion, controles de 24
horas/horas unicas/finitud, sentinelas y join existentes. No hay imputacion.

La serie ERA5 diaria valida se conserva separada del `inner join` usado para
features. Target, persistencia y episodios se derivan de ERA5; una ausencia de
NASA afecta disponibilidad de inferencia, pero no borra una observacion ERA5.

## Metodos y casos

Por horizonte se comparan LR, RF, HGB, promedio aritmetico exacto de los tres
scores (politica vigente), persistencia determinista y mayoria secundaria
preespecificada (al menos dos votos positivos). Familias y promedio usan el
umbral contractual 0.5. Persistencia repite el estado observado en `t` usando
el P20 contractual. No se ajustan umbrales ni se interpreta la fraccion de
votos como probabilidad.

Las metricas principales usan la misma interseccion: target y estado actual
validos mas las tres inferencias disponibles. La disponibilidad y exclusiones
se informan tambien por componente. Una ausencia no es voto negativo.

## Metricas y probabilidad

Por metodo/horizonte: N, positivos, negativos, prevalencia, matriz TN/FP/FN/TP,
precision, recall, F1, MCC, falsas alertas y omisiones, con `undefined` cuando
el denominador matematico no existe. Se informa cobertura y diferencia de MCC
frente a persistencia en casos comunes. Para familias y promedio solamente:
Average Precision, Brier y confiabilidad en diez bins equal-width fijados
`[0,.1),...,[.9,1]`, con N y positivos. Persistencia es 0/1 determinista;
mayoria no es probabilistica. Brier no acredita por si solo calibracion.

Se separan: (A) clasificacion diaria; (B) casos no secos en t y secos en t+h;
(C) anticipacion de inicios. Un episodio son dias calendario consecutivos con
observacion valida bajo P20. Un hueco rompe el episodio y censura el borde: no
prueba recuperacion ni continuidad. Un inicio es determinable solo si el dia
calendario anterior es valido y no seco. Para el borde de 2023 se conserva el
lookback permitido y se consulta 2022-12-31: Jan 1 es determinable si ese dia
es valido y no seco, y queda censurado si esta seco o ausente. Esto no vuelve
admisible una emision anterior a 2023. Para +h se inspecciona exclusivamente
la emision `inicio-h`, dentro de 2023 y evaluable; un episodio se cuenta una
vez. Episodios se reportan descriptivamente, sin intervalos.

## Incertidumbre fijada

Comparaciones principales: bootstrap pareado de bloques moviles no circulares,
longitud 30 dias, semilla `20250109`, 5000 replicas, IC95 percentil. Los bloques
solo nacen dentro de segmentos de casos comunes consecutivos; cada segmento se
remuestrea por separado conservando exactamente su cantidad de casos, sin
envolver ni atravesar huecos. Un segmento menor a 30 dias hace indefinido el
procedimiento en vez de descartarlo. Se estima delta MCC de cada familia, promedio y mayoria
contra persistencia, y promedio contra mayoria. Replicas con MCC indefinido se
descartan y cuentan; un IC solo se informa con al menos 4000 de 5000 replicas
validas. No se remuestrean dias como independientes ni se calculan
IC de episodios. Multiples contrastes siguen siendo exploratorios.

## Salidas, limites y criterio de detencion

Una unica corrida real escribe en directorio externo nuevo: manifiesto de
ejecucion, snapshots opcionales restringidos, predicciones, metricas, resumen
UI versionado y reporte; registra SHA ejecutable/protocolo, argumentos,
entorno, hashes antes/despues y exclusiones. Se crea respaldo separado y se
verifica por SHA-256. Un fallo conserva el intento y no autoriza cambiar
criterios ni repetir para mejorar metricas.

No se ejecutan A/B/C/H ni entrenamiento/recalibracion; no se tocan holdout,
ledger, UI, politica, emisiones o feedback. El resultado puede sostener solo
desempeno historico exploratorio de estos artefactos en 2023, no utilidad
agronomica, ahorro de agua, superioridad confirmatoria ni probabilidad
operativa acreditada.
