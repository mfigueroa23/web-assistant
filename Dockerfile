# Base images pinned as tag@digest. When updating the uv stage, align `version:` of astral-sh/setup-uv in
# .github/workflows (tests/runtime_test.py checks it).
FROM ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 AS uv

# pyyaml, zstandard and websockets publish no wheels for Python 3.15 yet, so they are compiled here. The compiler
# stays in this stage and never reaches the final image.
FROM python:3.15-alpine@sha256:0f9552bb28711333da16915ec146f5e6bb44a7fdac9ced15dc17c2e0206346dd AS build
RUN apk add --no-cache build-base
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Same base image as the build stage, so the virtual environment's interpreter links stay valid. Migrations are not
# run here: the Release workflow applies them before deploying.
FROM python:3.15-alpine@sha256:0f9552bb28711333da16915ec146f5e6bb44a7fdac9ced15dc17c2e0206346dd
RUN apk upgrade --no-cache \
 && addgroup -S app \
 && adduser -S -G app -H app
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=build /app/.venv ./.venv
COPY main.py ./
COPY src ./src
USER app
EXPOSE 8000
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
