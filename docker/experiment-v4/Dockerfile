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

# Segunda comprobación, ya con `src` y `tests` en la imagen: si el contexto
# arrastrara un `*.egg-info` no versionado, pip interpretaría el proyecto como
# instalado y reclamaría dependencias que este entorno no instala a propósito.
RUN pip check

ENV PYTHONPATH=/workspace/src

CMD ["sh", "-c", "pytest -q tests/test_controlled_daily_v4_*.py"]
