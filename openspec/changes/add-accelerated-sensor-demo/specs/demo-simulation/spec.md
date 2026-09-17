## ADDED Requirements

### Requirement: Preparación aislada y reproducible

La herramienta DEBE preparar explícitamente por CLI un sensor nuevo de demostración,
un manifiesto y un prefijo histórico sintético suficiente, sin sobrescribir recursos.

#### Scenario: Preparar una sesión

- **GIVEN** fechas pasadas, semilla e historial válidos y contrato operativo disponible
- **WHEN** se prepara una sesión
- **THEN** se asigna un sensor exclusivo, se registra la configuración y solo se publica historia anterior al primer día de reproducción
- **AND** todos los registros son sintéticos y una colisión con recursos existentes se rechaza sin sobrescritura.

#### Scenario: Configuración inválida

- **GIVEN** fechas no pasadas, período vacío o contrato no disponible
- **WHEN** se solicita preparación
- **THEN** se rechaza con motivo y no se inicia un worker ni una corrida experimental.

### Requirement: Avance diario causal mediante la API real

Cada paso DEBE incorporar exactamente el siguiente día calendario, verificarlo y
solicitar el pronóstico antes de avanzar. El dataset usado no DEBE contener días futuros.

#### Scenario: Completar varios días

- **GIVEN** sesión preparada con historia entrenable
- **WHEN** se ejecutan cinco pasos exitosos
- **THEN** se observan cinco fechas nuevas consecutivas de datos y cinco registros de pronóstico, cada uno solicitado antes de ingerir el día siguiente
- **AND** se conserva procedencia sintética, ET0 y fecha objetivo informada por el backend.

#### Scenario: Datos posteriores o fallo de pronóstico

- **GIVEN** un día ingerido
- **WHEN** se detecta una fecha posterior no autorizada o el pronóstico retorna error
- **THEN** se detiene el avance, se conserva el dato ya aceptado y se informa que no se confirmó el pronóstico
- **AND** no se inventa una alerta ni se alteran umbrales para continuar.

### Requirement: Pausa persistente y exclusión de ejecución

La herramienta DEBE mantener un único worker activo y persistir el cursor y fase.
Pausar DEBE impedir el siguiente paso sin abandonar escrituras en curso.

#### Scenario: Pausar y continuar

- **GIVEN** un paso en curso
- **WHEN** se solicita pausa
- **THEN** el estado indica pausa solicitada hasta resolver el paso y luego queda pausado
- **AND** continuar comienza desde el primer paso incompleto, sin duplicar registros ni rebobinar.

#### Scenario: Clientes o procesos duplicados

- **GIVEN** una sesión activa y una orden ya aceptada
- **WHEN** otro proceso intenta tomarla o se repite el request de control
- **THEN** el lock impide otro worker y el request duplicado devuelve el resultado registrado; una revisión obsoleta recibe 409.

### Requirement: Recuperación conservadora de resultados inciertos

La herramienta DEBE persistir la intención antes de cada POST y reconciliar sus
efectos antes de repetirlo. Un timeout no DEBE interpretarse como cancelación.

#### Scenario: Respuesta perdida con efecto comprobado

- **GIVEN** payload o pronóstico pendiente en el manifiesto, con request anterior terminado
- **WHEN** la lectura del estado persistido confirma el efecto esperado
- **THEN** se recupera el mismo registro, sin POST duplicado, y se conserva la secuencia.

#### Scenario: Reinicio con operación incierta

- **GIVEN** un reinicio o desconexión sin prueba de que el POST anterior terminó
- **WHEN** se intenta continuar
- **THEN** la sesión queda bloqueada y se explica la incertidumbre; no reintenta escrituras ni avanza automáticamente.

### Requirement: Separación de demostración y evidencia científica

La herramienta DEBE conservar modelos, datos, feedback y manifiestos de demo
identificables y separados de sensores existentes y artefactos experimentales.

#### Scenario: Finalizar la sesión

- **GIVEN** todos los pasos confirmados
- **WHEN** termina la reproducción
- **THEN** se preservan los registros como demostración sintética y no se calculan conclusiones de desempeño ni métricas HU7/HU8
- **AND** no se modifica el módulo de aumento sintético, el protocolo ni resultados históricos.
