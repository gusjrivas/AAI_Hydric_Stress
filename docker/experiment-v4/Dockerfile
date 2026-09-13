# Entorno experimental reproducible dedicado a controlled_daily_v4_external_pergamino.
# No reemplaza el Dockerfile raíz (backend/tests generales); ver docker/experiment-v4/constraints.txt
# para las versiones exactas validadas. Referencia: docs/research/controlled-daily-v4-external-pergamino-protocol.md,
# sección 15 ("Entorno reproducible").
FROM python@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534

WORKDIR /workspace

COPY docker/experiment-v4/constraints.txt ./docker/experiment-v4/constraints.txt
COPY pyproject.toml ./

RUN pip install --no-cache-dir -c docker/experiment-v4/constraints.txt \
    "pandas>=2.0" "pyarrow>=14.0" "scikit-learn>=1.4" \
    numpy scipy joblib threadpoolctl \
    "pytest>=8.0" "ruff>=0.6" "black>=24.0" \
    # Falla el build si el árbol de dependencias queda inconsistente, en lugar
    # de descubrirlo al ejecutar el experimento. Ver .dockerignore: el contexto
    # debe excluir `src/*.egg-info` para que esta comprobación sea significativa.
    && pip check

COPY src ./src
COPY tests ./tests
# Referencia versionada de identidad/entorno (hallazgos H-01/H-04): el mismo
# archivo que documenta el protocolo, nunca una copia mantenida a mano.
# `docker/experiment-v4/constraints.txt` ya se copió arriba.
COPY docs/research/controlled-daily-v4-external-pergamino-manifest.yaml \
     ./docs/research/controlled-daily-v4-external-pergamino-manifest.yaml

# Segunda comprobación, ya con `src` y `tests` en la imagen: si el contexto
# arrastrara un `*.egg-info` no versionado, pip interpretaría el proyecto como
# instalado y reclamaría dependencias que este entorno no instala a propósito.
RUN pip check

# Identidad de código dentro del contenedor (hallazgo H-05; revisión externa
# 2026-09-13, punto 1): no hay `.git` en esta imagen (no se copia el
# historial completo del repositorio, ver .dockerignore). En su lugar se
# copia un archivo de metadatos JSON con el SHA completo y el estado
# limpio/modificado del MISMO checkout usado como contexto de este build,
# generado por `docker/experiment-v4/build.py` -- NUNCA construir esta
# imagen invocando `docker build` directamente si se necesita esa identidad:
# usar en cambio
#   python docker/experiment-v4/build.py -t experiment-v4-controlled-daily-v4
# Sin ese archivo, este COPY falla explícitamente (no hay valor por defecto
# ambiguo tipo "unknown"). `code_identity.capture_code_identity()` valida el
# esquema y el formato del SHA al leerlo; un archivo malformado se trata
# como identidad inválida, nunca como una identidad aceptada a ciegas.
COPY .build_identity.json ./.build_identity.json

ENV PYTHONPATH=/workspace/src

CMD ["sh", "-c", "pytest -q tests/test_controlled_daily_v4_*.py"]
