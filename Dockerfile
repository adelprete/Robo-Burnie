FROM python:3.13.9-slim-trixie

ENV POETRY_VERSION=2.2.1

WORKDIR /app

COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry=="${POETRY_VERSION}" --no-cache-dir; \
    poetry config virtualenvs.create false; \
    poetry install --no-interaction

ENV PATH="/root/.local/bin:$PATH"
