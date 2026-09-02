FROM python:3.11-slim

WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies first for layer caching
COPY pyproject.toml README.md /app/
RUN uv sync --no-install-project

# Copy source code and files
COPY src /app/src
RUN uv sync

ENV CODEMESH_WORKSPACE_ROOT=/app
ENV POSTGRES_HOST=larnet-postgres
ENV POSTGRES_PORT=5432
ENV POSTGRES_DB=groundtruth_catalog
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=larnet_dev

EXPOSE 9482

CMD ["uv", "run", "uvicorn", "codemesh.service.app:app", "--host", "0.0.0.0", "--port", "9482"]

