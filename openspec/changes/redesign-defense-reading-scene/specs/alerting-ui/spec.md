# Spec delta: alerting-ui

## ADDED Requirements

### Requirement: Lectura rápida del recorrido histórico en modo defensa

La pantalla del recorrido histórico en modo defensa DEBE iniciar con un titular que resuma el veredicto de la emisión elegida, derivado únicamente de lo que devolvió el backend, y con un rótulo de datos pasados y otro de origen de datos. DEBE presentar, en una sola escena, la serie de humedad del suelo con el umbral del protocolo, un veredicto por horizonte con ícono y palabra y la votación de los modelos, y un control del reloj del recorrido. NO DEBE mostrar probabilidades, porcentajes ni puntajes por modelo. NO DEBE calcular ni afirmar que un pronóstico acertó o falló, y DEBE mostrar el dato real revelado con su procedencia. DEBE mantener visible un aviso de que es apoyo a la decisión y de que «sin alerta» no garantiza ausencia de estrés.

#### Scenario: Titular con la conclusión

- **GIVEN** una emisión cuyos tres horizontes el backend devolvió sin alerta
- **WHEN** se abre la pantalla
- **THEN** el titular indica que, según los modelos, no hay alerta de humedad baja en los tres días siguientes
- **AND** no aparece ninguna probabilidad.

#### Scenario: Votación separada del veredicto

- **GIVEN** un horizonte con alerta y dos de tres modelos con alerta
- **WHEN** se muestra la franja de veredictos
- **THEN** la celda indica alerta y «2 de 3 modelos indican alerta»
- **AND** la votación no se presenta como la regla de decisión.

### Requirement: Revisión humana de alertas y de ausencias de alerta

La pantalla DEBE permitir confirmar o rechazar el resultado de cada horizonte una vez revelado su dato, tanto si el veredicto fue alerta como si fue ausencia de alerta, con el mismo flujo de elección, comentario opcional y guardado, la misma idempotencia y las mismas reglas de apertura que la revisión existente. DEBE nombrar en la pregunta y en la confirmación la decisión revisada, DEBE indicar antes de revelar el dato que todavía no se puede revisar, y DEBE mantener visible que la revisión es de prueba técnica, aislada del historial operativo y sin efecto sobre reentrenamiento ni recalibración.

#### Scenario: Confirmar una ausencia de alerta

- **GIVEN** un horizonte sin alerta cuyo dato real ya fue revelado
- **WHEN** la persona elige «Confirmar resultado» y guarda
- **THEN** se envía la revisión con la acción de confirmar y la celda del horizonte muestra la revisión como confirmada.

#### Scenario: Rechazar una alerta

- **GIVEN** un horizonte con alerta cuyo dato real ya fue revelado
- **WHEN** la persona elige «Rechazar resultado» y guarda
- **THEN** se envía la revisión con la acción de rechazar y la celda del horizonte muestra la revisión como rechazada.

#### Scenario: Antes de revelar el dato

- **GIVEN** un horizonte cuyo dato real todavía no fue revelado por el reloj
- **WHEN** se elige ese horizonte
- **THEN** no se ofrece confirmar ni rechazar y se indica hasta qué día hay que avanzar el reloj.
