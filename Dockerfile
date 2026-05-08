FROM python:3.12-slim

ENV UV_SYSTEM_PYTHON=1
WORKDIR /app

RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY tests ./tests
COPY data ./data
RUN uv sync --dev

CMD ["uv", "run", "pytest"]
