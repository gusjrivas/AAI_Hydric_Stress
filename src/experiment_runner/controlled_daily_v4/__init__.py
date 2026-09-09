"""Implementación de la Etapa A de controlled_daily_v4_external_pergamino.

Protocolo normativo: docs/research/controlled-daily-v4-external-pergamino-protocol.md
(ADR-0011, ADR-0010). Este paquete implementa exclusivamente la Etapa A
(desarrollo y selección, 2015-01-07 a 2022-12-28). Las etapas B y C no están
implementadas aquí — cualquier intento de configurarlas debe rechazarse
explícitamente (ver `config.py` y `cli.py`).
"""

from __future__ import annotations
