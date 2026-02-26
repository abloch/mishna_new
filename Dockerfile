FROM ghcr.io/astral-sh/uv:python3.12-alpine

COPY uv.lock pyproject.toml /app/
WORKDIR /app
RUN uv sync --frozen --no-install-project
COPY *.py .
CMD ["uv", "run", "python", "main.py"]
