"""Herramienta local de demostración acelerada (HU6, capacidad
`demo-simulation`, `openspec/changes/add-accelerated-sensor-demo/`).

Reproduce un período pasado sintético, un día calendario por paso,
contra los endpoints reales de ingesta y pronóstico del backend. No
entrena modelos ni escribe feedback directamente: solo consume la API.
No forma parte del pipeline experimental (HU7/HU8) ni del aumento
sintético de HU3.
"""
