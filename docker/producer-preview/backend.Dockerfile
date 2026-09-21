FROM python:3.11-slim
WORKDIR /workspace
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[backend]" pytest
COPY backend ./backend
# Fixtures are synthetic and explicitly reused only by this local preview.
COPY tests/__init__.py tests/test_operational_run.py ./tests/
COPY docker/producer-preview/prepare.py ./preview/prepare.py
ENV PYTHONPATH=/workspace:/workspace/src:/workspace/backend
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace/backend
