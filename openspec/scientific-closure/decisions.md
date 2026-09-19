# Registro de decisiones de gobernanza

Todas son decisiones de preparación, no resultados científicos. Fecha 2026-09-18.

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

Modelos configurados: explorer gpt-5.6-terra/medium; implementer
gpt-5.6/medium; critic gpt-5.6/high; auditor gpt-5.6/xhigh;
checker gpt-5.6-luna/low. No sustitución silenciosa. Si el proveedor rechaza
un modelo, registrar solicitado/efectivo, motivo, esfuerzo y pérdida posible.
Elegir el disponible más próximo y revalidar rol; si no conserva capacidad
necesaria, BLOCKED. No sustituir simplemente por una recomendación más nueva.

Fuentes oficiales de formato y modelos consultadas con OpenAI Docs:
[agentes personalizados](https://developers.openai.com/fr-FR/docs/agent-configuration/subagents),
[catálogo de modelos](https://developers.openai.com/api/docs/models).
Estas fuentes establecen formato/alias, no garantizan disponibilidad por cuenta
ni imposición efectiva del sandbox en otra sesión.
