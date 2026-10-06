import json
from pathlib import Path
root = Path("/repo")
p = root / "config/producer-calibration-plan.draft.json"
text = p.read_text(encoding="utf-8")
data = json.loads(text)
old = json.dumps(data["tolerances"], ensure_ascii=False, indent=2)
start = text.index('  "tolerances": {')
end = text.index('\n  "log_loss":', start)
tolerances = {
"epsilon_ece": 0.10,
"epsilon_bin": 0.15,
"justification": "Aprobacion explicita del autor el 2026-09-20: tolerancias operacionales de 10 puntos porcentuales para el limite superior de ECE y 15 para el limite superior del error por intervalo respaldado. Solo evaluacion exploratoria del prototipo; no son garantias estadisticas ni validacion agronomica. No equivalen a accuracy ni autorizan publicar porcentajes sin superar todos los criterios del assessment.",
"approval": {"date": "2026-09-20", "scope": "exploratory_operational_product_tolerances", "approved_by": "project_author"}
}
block = json.dumps(tolerances, ensure_ascii=False, indent=2)
lines = block.splitlines()
replacement = '  "tolerances": ' + lines[0] + '\n' + '\n'.join('  '+line for line in lines[1:]) + ','
text = text[:start] + replacement + text[end:]
p.write_text(text, encoding="utf-8")
p = root / "tests/test_calibration_manifest.py"
text = p.read_text(encoding="utf-8")
start = text.index('    # Única decisión sustantiva pendiente:')
end = text.index('\n    with pytest.raises(CalibrationManifestError, match="status no es ready_for_fit"):', start)
text = text[:start] + '''    # Approved product tolerances do not automatically authorize fitting.
    assert draft["tolerances"]["epsilon_ece"] == 0.10
    assert draft["tolerances"]["epsilon_bin"] == 0.15
    assert draft["tolerances"]["justification"]
    assert draft["tolerances"]["approval"]["date"] == "2026-09-20"
    assert report.issues == ()
''' + text[end:]
p.write_text(text, encoding="utf-8")
p = root / "docs/design/operational-calibration-manifest-decisions.md"
text = p.read_text(encoding="utf-8")
pos = text.index("\n")
note = """
## Actualizacion 2026-09-20 — tolerancias aprobadas
El autor aprobo explicitamente epsilon_ece=0.10 y epsilon_bin=0.15 como
criterios de producto para evaluacion exploratoria. Se registran en el JSON.
Esta actualizacion reemplaza el pendiente de tolerancias descrito en la nota
historica siguiente. No cambia soporte, ventanas, modelos o datos.

El archivo permanece draft: aceptar tolerancias no congela el plan ni acredita
calibracion. Antes de congelar, verificar hash del dataset sin evaluar resultados,
variables/unidades y versiones efectivas del entorno como exige el diseno.
Precisar tambien el algoritmo de limites simultaneos (estadistico centrado y
construccion del limite) y la regla para replicas invalidas: el texto actual
dice que se excluyen, pero tambien afirma que no se descartan replicas.
La longitud de huecos no justifica por si sola la dependencia temporal.
Son comprobaciones tecnicas pendientes; no requieren volver a pedir aprobacion
de estas dos tolerancias ni permiten ajustarlas mirando resultados.

Trazabilidad: HU4/predictive-modeling, CRISP-DM modelado/evaluacion de desarrollo.
Sin cambio de protocolos v3/v4, configuraciones formales, hipotesis, arquitectura,
datasets o resultados HU7/HU8. No se entreno, calibro ni evaluo ningun modelo.

## Registro previo a la aprobacion (historico)
"""
p.write_text(text[:pos+1]+note+text[pos+1:], encoding="utf-8")
