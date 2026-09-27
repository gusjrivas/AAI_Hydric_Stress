# Tasks

- [x] T01 Congelar protocolo, identidades, periodo, metricas y bootstrap antes
  de observar resultados reales.
- [x] T02 Implementar filtrado secuencial 2022-12-26..2023-12-31 y reutilizar
  ingesta, controles e inferencia existentes sin fit/recalibracion.
- [x] T03 Implementar casos comunes, metricas, calibracion, episodios y
  bootstrap pareado preespecificado.
- [x] T04 Probar causalidad, bordes, custodia, indefiniciones, politica y
  preservacion de hashes con fixtures sinteticos.
- [ ] T05 Congelar snapshot ejecutable, verificarlo independientemente y solo
  entonces ejecutar una vez sobre las entradas autorizadas.
- [ ] T06 Custodiar salida externa y respaldo, interpretar resultados sin
  sobreafirmaciones y someter el snapshot final a critica/auditoria.

Las casillas no acreditan PASS por si mismas; las actualiza el orquestador solo
despues de evidencia y revision independientes.

T05 queda abierta con `FAIL`: hubo dos ejecuciones completas, aunque sus
productos cientificos son byte-identicos y la primera fue fijada como canonica
por precedencia temporal. T06 queda abierta porque la auditoria final emitio
`FAIL` de gobernanza por esa desviacion. No se autoriza una tercera ejecucion;
el resultado canonico conserva uso exclusivamente exploratorio.
