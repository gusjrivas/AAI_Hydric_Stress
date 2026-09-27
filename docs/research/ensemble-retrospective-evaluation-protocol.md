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

Emisiones admisibles: 2023-01-01 hasta 2023-12-31 menos el horizonte, ambas
fechas inclusive; target observado `soil_moisture(t+h) < P20` y siempre en
2023. Lookback minimo: 2022-12-26..2022-12-31 (seis dias previos mas el dia de
emision forman la ventana maxima de siete). Se asume disponibilidad
retrospectiva de observaciones diarias; no se acredita latencia operativa.

Los CSV mixtos se recorren secuencialmente. Solo se interpreta la fecha
estructural de filas fuera de rango; sus mediciones no se parsean ni agregan.
Se registra honestamente que sus bytes fueron leidos. El snapshot restringido
se crea antes de pandas y luego reutiliza loaders, agregacion, controles de 24
horas/horas unicas/finitud, sentinelas y join existentes. No hay imputacion.

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
calendario anterior es valido y no seco. Para +h se inspecciona exclusivamente
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
