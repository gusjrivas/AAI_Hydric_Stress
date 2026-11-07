# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Coherencia terminológica con la memoria técnica

Los textos de las pantallas de presentación (Arquitectura, Caso de demostración, Laboratorio y Resultados) DEBEN usar los términos y las afirmaciones de la memoria técnica vigente. El número de modelos con alerta DEBE llamarse «acuerdo entre modelos» y NO DEBE presentarse como la regla de decisión, que es el promedio de las salidas contra el umbral de decisión. El umbral de humedad DEBE describirse como relativo (percentil 20 del entrenamiento). Los modos DEBEN llamarse «reproducción histórica» y no «replay». Los casos DEBEN rotularse según el origen de los datos declarado en la memoria. NO DEBEN mostrarse probabilidades como medida de riesgo en el recorrido histórico ni en el laboratorio. Los resultados DEBEN usar los nombres de métodos y configuraciones de la memoria, NO DEBEN mostrar el estado de gobernanza «FAIL por ejecución duplicada» y DEBEN describir la retroalimentación humana sin presentarla como una mejora uniforme. Los textos de las pantallas del video DEBEN redactarse en registro impersonal.

#### Scenario: Acuerdo sin regla de votación

- **GIVEN** un horizonte con dos de tres modelos con alerta y veredicto sin alerta
- **WHEN** se muestra la tarjeta de revisión
- **THEN** el texto dice «Acuerdo entre modelos»
- **AND** no aparece la palabra «votación».

#### Scenario: Umbral relativo

- **GIVEN** un umbral entregado por el backend con su unidad
- **WHEN** se muestra la definición de alerta
- **THEN** el texto indica que es el percentil 20 del entrenamiento.

#### Scenario: Laboratorio sin probabilidades

- **GIVEN** un pronóstico del laboratorio con alerta
- **WHEN** se muestra el último pronóstico y la leyenda de pronósticos emitidos
- **THEN** se lee «ALERTA» sin ninguna probabilidad.
