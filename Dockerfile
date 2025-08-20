FROM python:3.13-slim AS base
# FROM ghcr.io/astral-sh/uv:0.8-debian-slim AS builder
#
# WORKDIR /app
#
# COPY pyproject.toml README.md uv.lock ./
#
# RUN uv sync --frozen
#
# COPY . /app

FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY uv.lock pyproject.toml /app/
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-install-project --no-dev
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev

# TODO: Run as non-root user (but careful with output directory ownership)
FROM base AS runtime

WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app /app

ENTRYPOINT ["nightjet"]
