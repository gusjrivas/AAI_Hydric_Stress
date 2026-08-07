FROM python:3.11-slim

WORKDIR /workspace

COPY pyproject.toml ./
COPY src ./src
COPY tests ./tests

RUN pip install --no-cache-dir -e ".[dev]"

CMD ["pytest", "-q"]
