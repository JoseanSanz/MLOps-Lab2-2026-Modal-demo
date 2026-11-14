# ---------------------------------------------------------------------------
# Stage 1 (builder): installs the runtime dependencies from uv.lock
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

# Compile .pyc files at install time (faster start-up) and copy instead of hard-linking
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

WORKDIR /app

# Only the dependency files: this layer is cached while they do not change
COPY pyproject.toml uv.lock ./

# 1. uv export: writes the exact versions of uv.lock (the ones tested in the CI) for
#    the runtime dependencies only (--no-dev: no pytest, pylint, black, gradio, modal)
# 2. uv pip install --prefix /install: installs them in a separate folder that is
#    copied to the system Python of the final image. They are installed in the system
#    Python (not in a virtual environment) because Modal runs the image with it.
RUN uv export --frozen --no-dev --no-emit-project --no-hashes -o requirements.txt \
    && uv pip install --system --no-cache --prefix /install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 (runtime): only the installed packages and the source code
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY --from=builder /install /usr/local
COPY api ./api
COPY mylib ./mylib
COPY templates ./templates

# Note: the image runs as root because Modal adds its own layers to it (it installs
# its client in the system Python). For other platforms (Render, Cloud Run...) add a
# non-root user: RUN useradd --create-home appuser + USER appuser

EXPOSE 8000

# Docker marks the container as unhealthy if /health does not answer
# (python is used because the slim image does not include curl)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:%s/health' % os.environ.get('PORT', '8000'), timeout=4)" || exit 1

# Used by `docker run` (locally and in the CI smoke test). Modal does not use it: it
# imports the FastAPI app directly (see modal_app.py)
CMD ["sh", "-c", "exec uvicorn api.api:app --host 0.0.0.0 --port ${PORT}"]
