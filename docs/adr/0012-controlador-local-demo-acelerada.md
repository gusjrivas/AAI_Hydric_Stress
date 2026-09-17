# ADR-0012: Controlador local opcional de demostración acelerada

## Estado

**Propuesto**, 2026-09-17. Parte del change
[add-accelerated-sensor-demo](../../openspec/changes/add-accelerated-sensor-demo/proposal.md).
No implementado ni aceptado por este documento.

## Contexto

ADR-0007 define al mock como cliente HTTP, con historia inicial preparada por script.
ADR-0003 mantiene al backend como fachada delgada. La demostración solicita inicio,
pausa y continuación desde la UI, y una secuencia que sobreviva al cierre de pestaña.
Un temporizador React no satisface recuperación ni exclusión entre pestañas.

## Decisión propuesta

Agregar una herramienta de demostración en `scripts/demo_simulation/`, ejecutable
por CLI y con adaptador HTTP local FastAPI opcional. Su worker consume los endpoints
existentes de ingesta y pronóstico. No se aloja en el proceso del backend ni modifica
las capas internas de IA. Utiliza un manifiesto atómico y exclusión de proceso por sesión.

La preparación del dataset permanece como comando CLI explícito, sobre sensor nuevo.
El adaptador HTTP solo controla sesiones ya preparadas; no recibe nombres de archivos,
URLs de backend ni configuraciones científicas desde el navegador.

El servicio se habilita por perfil Docker `demo`, enlazado a loopback del host. La UI
descubre su disponibilidad solo si se configura su URL de control. No es dependencia
del arranque normal de la aplicación. CORS se limita al origen local configurado; las
mutaciones de control usan JSON y validación de Origin, sin cookies de autenticación.
No se publica en Internet en este alcance.

## Alternativas

- Scheduler en backend: mezcla la fachada con la orquestación de una demo y agrega actividad automática al proceso operativo.
- Temporizador en frontend: no sobrevive al cierre de pestaña y puede duplicarse entre clientes.
- Solo CLI: suficiente para la entrega 1, pero no satisface los controles solicitados en pantalla.

## Consecuencias

Se añade un proceso y configuración opcionales, con un contrato pequeño y pruebas
propias. La exclusión se impone en el controlador, no solo deshabilitando botones.
El backend operativo sigue usando sus contratos actuales; clientes ajenos al
controlador no adquieren garantías nuevas de exclusión. Se requieren sensores
exclusivos de demo y detección de cambios externos para poder detener la sesión.

No modifica ADR-0007 sobre preparación por CLI ni agrega servicios de serving,
modelos, protocolos de experimentación o un simulador agronómico. Una futura mejora
física del generador exige una decisión y pruebas separadas.
