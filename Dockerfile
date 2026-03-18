FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip && \
    pip install -e .[dev]

RUN mkdir -p /workspace/output /workspace/data

WORKDIR /workspace

ENTRYPOINT ["code39"]
CMD ["version"]
