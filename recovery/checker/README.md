# Checker científico con cambios sin commitear

- Rama original: `feat/scientific-closure`
- HEAD original: `59612ab2d1822e7bef6f22255985866de73b6cda` (`docs(science): checkpoint interrupted checker remediation`, 2026-09-19 03:48:16 -0300)
- Worktree de origen: `C:/Repo/AAI_Hydric_Stress_scientific_closure` (no modificado)
- Fecha de captura: 2026-10-06

## Archivos sucios

| Archivo | Tipo | Artefacto en esta rama |
|---|---|---|
| `scripts/check_scientific_closure.py` | tracked, modificado (397 líneas modificadas) | `check_scientific_closure.py.patch` |
| `tests/test_scientific_closure_checker.py` | tracked, modificado (221 líneas agregadas) | `test_scientific_closure_checker.py.patch` |
| `openspec/scientific-closure/validation-read-only-probe.tmp` | untracked | copia idéntica `validation-read-only-probe.tmp` |

Los patches se generaron con `git diff --binary` contra `59612ab`. Se aplican sobre ese commit, no sobre `main` actual.

## Observaciones

- El checker es estructural (verificación de forma y consistencia, no de resultados científicos); no ejecuta experimentos ni decide resultados científicos.
- Este material NO cambia el estado científico canónico (RB-05 = FAIL, sc-06 = FAIL, SC-GOV-025 = FAIL, GF = FAIL).
- La rama `feat/scientific-closure` está 58 commits detrás de su upstream, y `origin/main` contiene versiones posteriores del checker (`329cb60`, `0fd15ea`, `cc53346`); el diff entre `59612ab` y `origin/main` en esos dos archivos es de 732 inserciones y 39 eliminaciones. El cambio sucio es por tanto un checkpoint interrumpido anterior, aparentemente superado, aunque no se verificó línea por línea.
- El `.tmp` es una sonda de escritura de sandbox sin valor científico.

## SHA-256

Ver la lista completa en `../manifest/SHA256SUMS.txt`.
