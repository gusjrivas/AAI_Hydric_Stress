# Registro de decisiones de gobernanza

Todas son decisiones de preparación, no resultados científicos. Decisiones
GD-01..10: 2026-09-18; GD-11..12: 2026-09-19.

| ID | Decisión y fundamento | Impacto / autoridad |
| --- | --- | --- |
| GD-01 | Extender OpenSpec existente (project/specs/changes); agregar config spec-driven y capacidad scientific-closure | Encargo actual. No init destructivo ni migración de changes históricos |
| GD-02 | R/H/N/S condicionales por CL-05..08 y revisión de suficiencia global | Encargo actual prevalece sobre obligatoriedad indiscriminada en auditoría anterior; diseños congelados preservados |
| GD-03 | Separar PASS auditor, gate de candidato y cierre de tesis | Un resultado negativo puede cumplir protocolo y recibir PASS; no abre etapa bloqueada |
| GD-04 | Mantener SHA ejecutable auditado separado de SHA documental | Auditoría previa identifica 214735e42ee04f018156cd630591e798aadd8bf3 e imagen 55bc923efac0; toda nueva campaña debe verificar identidad completa |
| GD-05 | No modificar main para resolver ADR-0011 | Último cambio de protocolo (214735e) no es ancestro de main local (comprobado exit 1). La vigencia de la precondición ante correcciones posteriores queda por resolver por responsable; bloquea ejecución, no especificación |
| GD-06 | Usar OpenSpec CLI 1.13.1 por npx fijado, sin instalación global ni reemplazar dependencias científicas | npm view consultado; no había CLI global ni config.yaml |
| GD-07 | TOML autónomos en .codex/agents, agents.enabled y max_concurrent_threads_per_session=4 | Documentación oficial consultada; límite excluye padre. Runtime actual ofrece 4 slots totales: usar como máximo 3 hijos aquí |
| GD-08 | Conservar modelo solicitado gpt-5.6 en archivos | Documentación identifica alias de gpt-5.6-sol. Herramienta de colaboración ofrece nombre canónico; si se usa, registrar resolución sin afirmar degradación |
| GD-09 | Bloqueo de sandbox no equivale a hallazgo científico | Primer intento del explorador bloqueado por setup refresh; la segunda lectura con escalación completó la inspección, como registra preparation-validation.md. No emitió veredicto final |
| GD-10 | Readiness del sistema no es autorización para campaña | La siguiente sesión puede resolver preparación; A/B/ledger/C necesitan autorización explícita vigente y gates |
| GD-11 | Sustituir la instrucción operativa GD-08: los perfiles incompatibles `gpt-5.6` se reemplazan por `gpt-5.6-sol`, conservando medium/high/xhigh; Terra/medium y Luna/low se mantienen | Prompt vigente y catálogo local observado; requested/effective permanecen separados y el modelo efectivo no observable queda `null`. No acredita sandbox ni disponibilidad de campaña |
| GD-12 | Fijar antes de ejecución la suficiencia delegada: R `NOT_REQUIRED` para clasificación P20; H `REQUIRED` solo para correcciones simuladas; N `NOT_REQUIRED` sin afirmar detección reservada/fallas reales; S `NOT_REQUIRED` para el límite histórico de etiquetas+ruido, sin sensores ausentes | Autoridad delegada del prompt vigente, exploración y advisory crítico. CL-10 admite terminal negativo A/B, soporte insuficiente/onset indefinido, v3 `REFERENCED`, H auditado y límites; no certifica humano real, HU1 ni tesis completa. Pendiente crítica/auditoría de este snapshot |

Modelos configurados vigentes: explorer gpt-5.6-terra/medium; implementer
gpt-5.6-sol/medium; critic gpt-5.6-sol/high; auditor gpt-5.6-sol/xhigh;
checker gpt-5.6-luna/low. Registrar por sesión modelo y esfuerzo asignados,
efectivos cuando sean observables, sandbox nominal/efectivo y toda sustitución.
Un catálogo local no acredita carga del backend ni aislamiento.

Fuentes oficiales de formato y modelos consultadas con OpenAI Docs:
[agentes personalizados](https://developers.openai.com/fr-FR/docs/agent-configuration/subagents),
[catálogo de modelos](https://developers.openai.com/api/docs/models).
Estas fuentes establecen formato/alias, no garantizan disponibilidad por cuenta
ni imposición efectiva del sandbox en otra sesión.
