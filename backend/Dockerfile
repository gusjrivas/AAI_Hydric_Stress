FROM python:3.11-slim

WORKDIR /workspace

COPY pyproject.toml ./
COPY src ./src
COPY data ./data
COPY backend ./backend

RUN pip install --no-cache-dir -e ".[backend]"

WORKDIR /workspace/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
