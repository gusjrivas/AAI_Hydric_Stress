# Registro de preparación

Actualización posterior: ver [auditoría final](final-preparation-audit.md).
El estado pendiente siguiente describe el checkpoint histórico 0a7e107.

Estado: preparación implementada y validada; auditoría final pendiente.
Autonomía operativa: BLOCKED por fallo de aprovisionamiento del sandbox.
No ejecución científica autorizada. Sesión iniciada 2026-09-18, continuada 19/09.
Base: ba539bd2f17f8a05da41f6ffff32d730a0152f07.
Worktree y rama iniciales confirmados, árbol limpio.
main inicial: f7c4ef72ebee9f745bd80deadcd8ad69d9183274.
origin/feat/scientific-closure inicial: ba539bd2f17f8a05da41f6ffff32d730a0152f07.

La evidencia de validación se completará con resultados realmente observados.
No se ejecutaron A/B/C ni auxiliares, no se inicializó ledger y no se abrieron
datasets/holdouts durante la preparación. Esta declaración se limita a la sesión.

## Validaciones observadas

- OpenSpec 1.13.1 (npx fijado): spec scientific-closure y diez changes sc-* válidos
  en modo strict/no-interactive. Avisos informativos: requisitos >500 caracteres.
- Prueba documental en imagen inmutable: 15 tests OK (padre 0.514 s).
  evidence_checker independiente: 15 OK, 0.572 s, exit 0.
  scientific_critic independiente: 15 OK, 0.576 s.
- Los tests comprueban TOML de cinco agentes y config, IDs, matriz, referencias,
  dependencias, gates declarados, estados/eventos/aprobación y rechazo de atajos.
- git diff --check sin errores; aviso Git de normalización LF→CRLF.
- codex-cli 0.155.1; doctor confirma config loaded y catálogo bundled contiene
  Terra/Sol/Luna con esfuerzos requeridos. No prueba carga/aislamiento efectivo
  de todos los perfiles en una campaña.
- codex doctor --summary --ascii --no-color: exit 1, sandbox provisioning
  recorded a structured failure. Las lecturas necesitaron escalación aprobada.
  No se cambió configuración global ni se reparó el entorno fuera de alcance.
- codex --strict-config features list rechazado: opción no soportada para features.
  Se conserva como comprobación no aplicable, no como validación exitosa.

Comando documental ejecutado (sin módulos científicos ni raw montado):

```powershell
docker run --rm --network none --read-only --tmpfs /tmp --mount 'type=bind,source=C:\Repo\AAI_Hydric_Stress_scientific_closure,target=/workspace,readonly' -e PYTHONDONTWRITEBYTECODE=1 -w /workspace sha256:55bc923efac009b1b6de45acc634774b7910d4829fdfd0b2c963dd5748b297af python -m unittest discover -s tests -p test_scientific_closure_governance.py -v
npx.cmd --yes @fission-ai/openspec@1.13.1 validate scientific-closure --type spec --strict --no-interactive
Get-ChildItem openspec/changes -Directory -Filter 'sc-*' | ForEach-Object { npx.cmd --yes @fission-ai/openspec@1.13.1 validate $_.Name --type change --strict --no-interactive; if ($LASTEXITCODE -ne 0) { throw 'Validation failed' } }
```

## Revisión independiente y correcciones

Explorador /root/scientific_explorer, gpt-5.6-terra/medium: primer intento
bloqueado por sandbox; segunda lectura con escalación completó inventario y
contraste de autoridad/alcance, sin veredicto final.
Checker /root/evidence_checker, gpt-5.6-luna/low: verificación mecánica y hashes.
Crítico /root/scientific_critic, gpt-5.6-sol/high: alias de gpt-5.6 resuelto
al nombre disponible en la herramienta; no degradación de familia documentada.
El orquestador fue único escritor; los revisores no editaron ni abrieron datos.

| Hallazgo | Corrección comprobada por crítico |
| --- | --- |
| CRIT-01 crítico | extra_gate explícito en A/B/C y auxiliares, incluye gates negativos |
| CRIT-02 alto | Transiciones con dueño orquestador, aprobación, eventos y auditoría |
| CRIT-03 alto | Permisos específicos al despachar etapa; no exigir B/C antes de A |
| CRIT-04 medio | selection_decision.json y único artifacts.py |
| CRIT-02R alto residual | Validación de estados legales y cinco contraejemplos adicionales |

Última respuesta del crítico: no quedan hallazgos materiales abiertos de su
revisión; no constituye auditoría final ni PASS de ningún change experimental.
Los diez changes continúan PLANNED y sin autorización científica.
Los gates son contratos declarativos que el orquestador verifica; no se ha
implementado un servicio automático que pueda invocar runners por su cuenta.

## Hashes del snapshot revisado

SHA-256 calculados por evidence_checker (bytes del worktree; Git puede normalizar
saltos de línea al materializar otra copia, por lo que también registrar commit):

| Archivo | SHA-256 |
| --- | --- |
| openspec/specs/scientific-closure/spec.md | 37716BC0D222BF29E5F63CC095C64DE76983D8061774BF410A11BACAFA540F57 |
| requirements.json | E12563E42D3A09DE0E4CC393BF927A76924375622DCA13431103C752D125C19E |
| changes.json | 96E8C47BAA45F134A428A534FBC5A3A75C041ECDADD3195287F9A6864A09472A |
| traceability.md | E144256263F24E159B342DD76E74AE192AD3C218881C7ECA69D949F893F719F6 |
| .codex/config.toml | 5D377E0B7F402E6F59957AEFCD3080BE046D258A31550A4B0159E514CD6445F0 |
| tests/test_scientific_closure_governance.py | 8260B1367BB757CAE38091B15EB3F07B483E3429C80E9546AF896DD48AA0831B |

## Checkpoints

08ff237 configuración OpenSpec; b06e7de especificación; 2624683 agentes;
e2193f2 matriz/inventario/afirmaciones; 9814570 planes/gates/changes.
El commit que contiene este registro agrega operación y pruebas documentales.
Un registro posterior conservará el resultado exacto de auditoría final.
No se considera ejecutado ni cerrado ningún sc-* por estos commits.

## Pendientes operativos

Sandbox funcional y permisos efectivos; resolución documentada de ADR-0011
respecto de correcciones no presentes en main; procedencia histórica/licencia
NASA; segunda copia independiente/ensayo de recuperación; suficiencia por
afirmación y autorización de cada etapa. No resolverlos mirando holdouts ni
alterando main. El prompt siguiente reanuda preparación, no ejecución científica.
