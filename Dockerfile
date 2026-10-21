# syntax=docker/dockerfile:1
FROM python:3.13-slim AS wheels
WORKDIR /build
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip wheel --wheel-dir=/wheels -r requirements.txt

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN --mount=type=bind,from=wheels,source=/wheels,target=/wheels pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && useradd --uid 10001 --create-home memely
COPY --chown=memely:memely backend ./backend
COPY --chown=memely:memely css ./css
COPY --chown=memely:memely js ./js
COPY --chown=memely:memely index.html alembic.ini ./
COPY --chown=memely:memely migrations ./migrations
USER memely
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-", "backend.app:create_app()"]

FROM runtime AS test
USER root
RUN pip install --no-cache-dir pytest==9.0.2
COPY --chown=memely:memely tests ./tests
USER memely
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

FROM runtime AS production
