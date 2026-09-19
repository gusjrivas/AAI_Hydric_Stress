# Riesgos, limitaciones y bloqueos

| ID | Riesgo / evidencia | Control y responsable | Bloquea |
| --- | --- | --- | --- |
| RK-01 | Confundir tests con eficacia (EV-02/05) | Crítico exige artefactos reales autorizados | Cierre científico |
| RK-02 | Un sitio, reanálisis, proxy P20; UTC-3 versus LST y latencia | Auditor limita CL-01..03/09; no validación agronómica | Afirmaciones no respaldadas |
| RK-03 | Autocorrelación/soporte pequeño/comparaciones múltiples | Bloques/soporte fijos, sin significancia simultánea no corregida | Selección/interpretación si soporte falla |
| RK-04 | Custodia incompleta/manipulación administrativa | Registro único, backups, responsable; SQLite no protege del administrador | Etapa afectada y dependientes |
| RK-05 | Adquisición/licencia histórica desconocida | sc-02: evidencia documental o decisión explícita de admisibilidad conforme ADR | Ejecución mientras no se resuelva |
| RK-06 | Segunda copia y restauración no acreditadas | Ensayo fixtures y comprobación independiente antes de campaña | sc-02 y A |
| RK-07 | Precondición main de ADR-0011 frente a correcciones de rama | sc-02: decisión documentada sin hacer merge ni alterar main | A; no bloquea preparación |
| RK-08 | Forzar cuatro complementos o retirarlos por conveniencia | sc-01: evidencia→afirmación→brecha, revisar alcance total | Cierre global si UNRESOLVED |
| RK-09 | SHA de docs distinto a imagen, tag mutable | Identidad dual; usar ID inmutable verificado toda A/B/C | Ejecución si identidad no concuerda |
| RK-10 | Config TOML válida pero rol no cargado o permisos heredados | Verificar carga/modelo/sandbox efectivo; no lectores con escritura | Orquestación dependiente |
| RK-11 | Sandbox Windows no inicia procesos | Error reproducido setup refresh; no certificar independencia no realizada | Validaciones que necesiten ese entorno |
| RK-12 | Duración científica no medida | Medir pared/CPU/memoria al ejecutar; no extrapolar fixtures | No bloquea método; estimación pendiente |
| RK-13 | Cambiar código a mitad A/B/C o complementar mirando C | Único ejecutable congelado; auxiliares aislados sin alimentar selección | Campaña si ocurre |

Cada riesgo permanece abierto hasta evidencia de mitigación, no hasta redactar
un plan. Registro operativo: ID, estado, responsable, evidencia, siguiente acción,
fecha y cambios dependientes suspendidos. No reducir criterios después de resultados.
