# CI y hook de trazabilidad OpenSpec/ADR/seguimiento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar las dos piezas de automatización del ciclo de vida definidas en ADR-0003: integración continua (lint + tests) para el código Python existente, y un hook de Claude Code que bloquea `gh pr create` cuando el cambio no referencia el plan de tesis (OpenSpec/HU) o no actualiza el seguimiento de tareas.

**Architecture:** Un workflow de GitHub Actions corre `ruff`, `black --check` y `pytest` sobre `src/` y `tests/` en cada PR contra `main`. Un hook `PreToolUse` de Claude Code, filtrado a comandos `gh pr create`, invoca un script bash que inspecciona el diff de la rama contra `main` y decide `allow`/`deny` antes de que el PR se abra.

**Tech Stack:** GitHub Actions, Ruff, Black, pytest (ya en uso), bash + jq (hook script), Claude Code hooks (`PreToolUse`, `.claude/settings.json`).

**Spec:** `docs/adr/0003-stack-web-y-ciclo-de-vida-automatizado.md`

## Global Constraints

- El CI cubre solo el código Python existente hoy (`src/`, `tests/`); no se crea scaffolding de `backend/` ni `frontend/` (ADR-0003, sección "Alternativas consideradas").
- El job de CI debe apuntar a `src/` como carpeta completa, no a un paquete específico (`src/data_ingestion`), de modo que cubra automáticamente los paquetes de ML que se agreguen en HU3 (`src/data_quality`) y HU4 (`src/predictive_modeling`) sin modificar el workflow.
- El hook se guarda en `.claude/settings.json` (committeado, no en `settings.local.json`, que está gitignorado).
- El script del hook debe ejecutar en Git Bash (entorno Windows del usuario): usar `jq`, no asumir utilidades solo-Unix no disponibles en Git Bash.
- Si `jq` no está disponible en el entorno, el hook debe fallar abierto (permitir, con aviso), nunca bloquear por un problema de tooling ajeno a la trazabilidad real.

---

### Task 1: Linter y formateador Python (Ruff + Black)

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: comandos `ruff check src tests` y `black --check src tests`, consumidos por Task 2 (workflow de CI).

- [ ] **Step 1: Agregar Ruff y Black como dependencias de desarrollo**

Editar `pyproject.toml`, sección `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
    "black>=24.0",
]
```

- [ ] **Step 2: Agregar configuración de Ruff y Black**

Agregar al final de `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.black]
line-length = 100
target-version = ["py310"]
```

- [ ] **Step 3: Instalar las dependencias de desarrollo**

Run: `pip install -e ".[dev]"`
Expected: instala `ruff` y `black` sin errores.

- [ ] **Step 4: Formatear el código existente con Black**

Run: `black src tests`
Expected: reformatea archivos si hace falta (o "All done!" si ya están formateados), sin errores.

- [ ] **Step 5: Corregir hallazgos de Ruff**

Run: `ruff check src tests --fix`
Expected: corrige automáticamente lo corregible; si queda algo sin corregir automáticamente, arreglarlo a mano hasta que `ruff check src tests` termine sin errores.

- [ ] **Step 6: Verificar que todo pasa limpio**

Run: `ruff check src tests && black --check src tests && pytest`
Expected: los tres comandos terminan en éxito (exit code 0).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src tests
git commit -m "chore: agrega ruff y black, formatea código existente"
```

---

### Task 2: Workflow de CI en GitHub Actions

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `ruff check src tests`, `black --check src tests`, `pytest` (Task 1).
- Produces: check de GitHub Actions llamado `python-quality`, visible como status check en cada PR.

- [ ] **Step 1: Crear el workflow**

Crear `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  python-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Instalar dependencias
        run: pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check src tests

      - name: Formato (black)
        run: black --check src tests

      - name: Tests (pytest)
        run: pytest
```

- [ ] **Step 2: Validar la sintaxis YAML localmente**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
Expected: no imprime error (YAML válido). Si `python -c` con `yaml` falla por falta del módulo, alternativa: `pip install pyyaml` primero, o simplemente revisar visualmente la indentación (2 espacios, consistente) antes de continuar.

- [ ] **Step 3: Reproducir localmente los mismos pasos que correrá el CI**

Run: `ruff check src tests && black --check src tests && pytest`
Expected: éxito (ya verificado en Task 1, Step 6; se repite acá para confirmar que nada cambió).

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: agrega workflow de GitHub Actions (ruff, black, pytest)"
```

- [ ] **Step 5: Verificar que el workflow corre de verdad en GitHub**

Este paso requiere push y un PR real, así que se verifica junto con el cierre de este mismo plan (ver sección "Verificación final" más abajo), no en este punto intermedio.

---

### Task 3: Hook de trazabilidad OpenSpec/ADR/seguimiento

**Files:**
- Create: `.claude/hooks/check-pr-traceability.sh`
- Create: `.claude/settings.json`

**Interfaces:**
- Consumes: JSON de stdin con forma `{"tool_name": "Bash", "tool_input": {"command": "..."}}` (contrato de hooks de Claude Code).
- Produces: JSON de salida con forma `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"|"deny", "permissionDecisionReason": "..."}}`.

- [ ] **Step 1: Escribir el script del hook**

Crear `.claude/hooks/check-pr-traceability.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

allow() {
  echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}'
  exit 0
}

deny() {
  local reason="$1"
  printf '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": %s}}\n' \
    "$(printf '%s' "$reason" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '"%s"' "$reason")"
  exit 0
}

if ! command -v jq >/dev/null 2>&1; then
  allow
fi

input="$(cat)"
command_str="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"

if [[ -z "$command_str" ]]; then
  allow
fi

if ! [[ "$command_str" =~ gh[[:space:]]+pr[[:space:]]+create ]]; then
  allow
fi

base_branch="main"
if ! git rev-parse --verify "origin/${base_branch}" >/dev/null 2>&1; then
  allow
fi

diff_files="$(git diff --name-only "origin/${base_branch}...HEAD" 2>/dev/null || true)"
commit_messages="$(git log "origin/${base_branch}..HEAD" --format=%B 2>/dev/null || true)"

references_plan=false
if [[ "$command_str" =~ HU[1-8] ]] || [[ "$commit_messages" =~ HU[1-8] ]] || printf '%s' "$diff_files" | grep -q '^openspec/changes/'; then
  references_plan=true
fi

if [[ "$references_plan" == false ]]; then
  deny "El PR no referencia ningún change de openspec/changes/ ni menciona una HU (HU1-HU8) en el título/cuerpo del comando o en los mensajes de commit. Agregá esa referencia antes de abrir el PR (ver openspec/project.md, sección 'Convenciones para changes')."
fi

touches_src_or_research=false
if printf '%s' "$diff_files" | grep -qE '^(src/|docs/research/)'; then
  touches_src_or_research=true
fi

touches_seguimiento=false
if printf '%s' "$diff_files" | grep -q '^docs/seguimiento-tareas.md$'; then
  touches_seguimiento=true
fi

if [[ "$touches_src_or_research" == true && "$touches_seguimiento" == false ]]; then
  deny "El PR modifica src/ o docs/research/ pero no actualiza docs/seguimiento-tareas.md. Actualizá el seguimiento de tareas antes de abrir el PR."
fi

allow
```

- [ ] **Step 2: Dar permisos de ejecución al script**

Run: `chmod +x .claude/hooks/check-pr-traceability.sh`
Expected: sin salida (éxito).

- [ ] **Step 3: Pipe-test — comando que no es `gh pr create` (debe permitir sin evaluar nada más)**

Run: `echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | .claude/hooks/check-pr-traceability.sh`
Expected: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"}}`

- [ ] **Step 4: Pipe-test — `gh pr create` sin referencia a HU/OpenSpec (debe bloquear)**

Situarse en una rama de prueba sin relación con el plan para este test (o simular con una rama actual que no mencione HU en sus commits). Run:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"gh pr create --title \"prueba\" --body \"sin referencia\""}}' | .claude/hooks/check-pr-traceability.sh
```

Expected: JSON con `"permissionDecision": "deny"` y una razón que menciona `openspec/changes` o `HU`. (Si en este punto la rama de trabajo actual sí tiene commits con "HU" en el mensaje, este test da `allow` en lugar de `deny` — es correcto, refleja el comportamiento real; para forzar el caso `deny` en el pipe-test, usar `git log` de una rama sin esas menciones, o mockear `commit_messages` temporalmente comentando esa línea, solo para esta verificación puntual, y revirtiéndolo después.)

- [ ] **Step 5: Pipe-test — comando que sí menciona una HU (debe permitir, salvo por la regla de seguimiento-tareas)**

Run:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"gh pr create --title \"HU1: prueba\" --body \"referencia HU1\""}}' | .claude/hooks/check-pr-traceability.sh
```

Expected: si el diff actual contra `origin/main` no toca `src/` ni `docs/research/`, el resultado es `allow`. Si sí los toca sin tocar `docs/seguimiento-tareas.md`, el resultado es `deny` con esa razón — ambos son comportamientos correctos según el estado real de la rama en ese momento.

- [ ] **Step 6: Configurar el hook en `.claude/settings.json`**

Crear `.claude/settings.json` (no existe todavía; solo existe `.claude/settings.local.json`, que está gitignorado):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/check-pr-traceability.sh",
            "if": "Bash(gh pr create*)",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 7: Validar la sintaxis y el esquema del archivo de settings**

Run: `jq -e '.hooks.PreToolUse[] | select(.matcher == "Bash") | .hooks[] | select(.type == "command") | .command' .claude/settings.json`
Expected: exit code 0, imprime `"bash .claude/hooks/check-pr-traceability.sh"`.

- [ ] **Step 8: Commit**

```bash
git add .claude/hooks/check-pr-traceability.sh .claude/settings.json
git commit -m "feat: agrega hook de trazabilidad OpenSpec/ADR/seguimiento para gh pr create"
```

- [ ] **Step 9: Verificar que el hook se recarga y dispara de verdad**

Los cambios a `.claude/settings.json` requieren que Claude Code recargue la configuración (abrir el menú `/hooks` una vez, o reiniciar la sesión) antes de que el hook quede activo. Después de recargar, probar con un comando real y seguro: ejecutar mediante la herramienta Bash el comando `gh pr create --help` (no crea ningún PR, solo muestra ayuda) y confirmar que el hook se dispara — si el mensaje de permiso/bloqueo aparece antes de que el comando corra, el hook está activo. Si no aparece nada, avisar al usuario para que abra `/hooks` manualmente.

---

## Verificación final (requiere las tres tasks completas)

- [ ] **Paso final: Confirmar que el CI corre en un PR real**

Este plan se ejecuta en una rama nueva (siguiendo la convención de este repositorio: una rama por *change*/tarea). Al abrir el pull request de esta rama:

1. El hook de Task 3 debe evaluar ese `gh pr create` (el título/cuerpo del PR debe mencionar explícitamente ADR-0003; el diff sí toca `src/` — Task 1 reformateó `src/data_ingestion/aggregation.py` y `src/data_ingestion/schema.py` con Black —, así que la regla de seguimiento-tareas aplica y por eso esta misma rama actualiza `docs/seguimiento-tareas.md` antes de abrir el PR).
2. El check `python-quality` del workflow de Task 2 debe aparecer en la página del PR de GitHub y terminar en verde.

Si el check de CI no aparece o falla, revisar los logs de Actions en GitHub y corregir antes de mergear.
