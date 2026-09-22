# Handoff — entrega 2 backend productor

Fecha: 2026-09-19. Alcance detenido: únicamente los módulos recuperados de
preparación multihorizonte, contrato operacional y manifiesto de calibración,
con sus tres archivos de pruebas. No continuar con entrenamiento, calibración
real, API ni feedback desde este punto.

## Estado verificable

- Rama: `feat/hu6-backend-soporte-ui`.
- HEAD: `d463d97b7f46e39350107e33a0729e204d691ed8`.
- Upstream: `origin/feat/hu6-backend-soporte-ui`; rama local `ahead 1`.
- Commit local de esta entrega: `d463d97 feat(HU4-HU6): acepta contrato y prepara horizontes operativos`.
- Árbol antes de crear este handoff: cuatro archivos modificados, sin archivos
  untracked. El handoff queda como archivo nuevo sin seguimiento por instrucción
  expresa de no hacer commit.

Archivos modificados después del commit:

- `src/predictive_modeling/calibration_manifest.py`
- `src/predictive_modeling/operational_contract.py`
- `src/predictive_modeling/operational_preparation.py`
- `tests/test_operational_horizon_contract.py`

Resumen del diff conocido: 27 inserciones y 29 eliminaciones. Black reformateó
los tres últimos archivos; luego se corrigieron únicamente cuatro hallazgos de
Ruff: tres usos UP038 de uniones de tipos en `isinstance` y un import no usado.

## Implementado y verificado

- `operational_preparation.py`: calendario UTC, targets exactos h=1/2/3,
  particiones explícitas y purga por `target_date`.
- `operational_contract.py`: contratos separados por horizonte, identidades de
  artefacto y validación de familia compatible.
- `calibration_manifest.py`: validación fail-closed, congelado con SHA-256 y
  verificación de identidad.
- Tres archivos de tests específicos correspondientes.
- Ejecución conocida antes del último formato/lint: **37 tests passed** sobre
  `test_calibration_manifest.py`, `test_operational_horizon_contract.py` y
  `test_operational_multihorizon_preparation.py`.
- Una ejecución posterior informó **41 tests passed**, pero incluía un módulo de
  entrenamiento fuera del alcance que luego fue retirado; no se usa como evidencia
  de cierre de esta entrega.

## Cierre verificado

- `black --check` sobre los seis archivos de la entrega: **6 archivos sin cambios**.
- `ruff check` sobre los mismos seis archivos: **sin hallazgos**.
- Tests específicos (`test_calibration_manifest.py`,
  `test_operational_horizon_contract.py`,
  `test_operational_multihorizon_preparation.py`): **37 passed**.
- Regresión legacy directamente relacionada (`test_labeling.py`,
  `test_no_leakage.py`, `test_pipeline.py`): **9 passed**.
- `git diff --check`: sin errores antes del commit de cierre.

Trazabilidad: HU4/HU6; capacidades `predictive-modeling` y
`architecture-integration`; CRISP-DM preparación de datos e integración. No se
entrenaron modelos ni se modificaron configuración experimental, hipótesis,
alcance, arquitectura, datos, resultados históricos o protocolos. Las tareas
OpenSpec permanecen sin marcar como completas porque este cierre no amplía el
alcance de la entrega.
