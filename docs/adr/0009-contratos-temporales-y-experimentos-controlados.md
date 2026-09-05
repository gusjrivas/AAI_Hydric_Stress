# ADR-0009: Contratos temporales y evidencia experimental controlada

Estado: aceptado por el autor mediante aprobación del plan de auditoría, 2026-09-05.

La tercera auditoría identificó contratos de columnas crudas registrados como si
fueran variables efectivas, ruido calibrado con test y aplicado también al target,
confusión entre escasez y recencia, targets imputados y reutilización de períodos
entrenados en el ciclo de feedback. Las correcciones anteriores se mantienen.

Se adopta el protocolo `docs/research/protocolo-experimental-v3.md`: calendario diario,
objetivo observado congelado, validación de contrato completo antes de cargar,
transformaciones ajustadas dentro de folds y bundle congelado en inferencia;
escenarios pareados y separación entre emisión, recalibración y evaluación posterior.

La arquitectura modular de ADR-0001 no cambia. Estas decisiones implementan sus
contratos y la trazabilidad de feedback pendiente; no añaden infraestructura.
Los modelos históricos permanecen almacenados y no se cargan automáticamente sin
contrato verificable. Las corridas históricas se conservan. La UI mantiene una alerta
emitida por sensor/día y ahora usa las rutas por sensor ya decididas en ADR-0008.

HU7 «completa» sigue significando anomalías+sintéticos sobre modelado predictivo;
no constituye evidencia experimental de mejora por retroalimentación humana.
