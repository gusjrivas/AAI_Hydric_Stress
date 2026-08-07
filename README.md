# AAI_Hydric_Stress

Prototipo experimental de la arquitectura de inteligencia artificial para detección temprana de estrés hídrico en cultivos hortícolas — Trabajo Final, Maestría en Inteligencia Artificial (FIUBA).

Ver [`docs/adr/`](docs/adr/) para las decisiones de arquitectura y stack técnico, y [`openspec/project.md`](openspec/project.md) para el contexto, alcance y convenciones del proyecto.

## Desarrollo y tests

Se recomienda ejecutar el proyecto dentro del devcontainer/Docker incluido, para evitar restricciones de políticas de Control de Aplicaciones de Windows sobre las DLL nativas de pandas/pyarrow en algunos equipos:

```bash
docker build -t aai-hydric-stress-test .
docker run --rm aai-hydric-stress-test
```

También puede abrirse la carpeta en VS Code con la extensión Dev Containers (`.devcontainer/devcontainer.json`).

Si el entorno local no tiene esa restricción, alternativamente:

```bash
pip install -e ".[dev]"
pytest -q
```
