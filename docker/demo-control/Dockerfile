# Imagen del adaptador HTTP local de control de la demo acelerada
# (HU6, `openspec/changes/add-accelerated-sensor-demo/`, entrega 2).
#
# Solo se usa bajo el perfil Docker Compose opcional `demo`; no forma
# parte del arranque normal del sistema (`docker compose up` sin
# `--profile demo` no la construye ni la levanta).
#
# No copia `data/`: el worker de control accede al estado del backend
# únicamente vía HTTP (`GET /quality`, `GET /feedback`, diseño sección
# 3.4: "acceso de lectura al mismo almacenamiento mediante el
# contrato, no mediante lectura Parquet ad hoc"), nunca por lectura
# directa de archivos.
FROM python:3.11-slim

WORKDIR /workspace

COPY pyproject.toml ./
COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir -e ".[backend]"

EXPOSE 8010

ENTRYPOINT ["python", "-m", "scripts.demo_simulation"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8010"]
