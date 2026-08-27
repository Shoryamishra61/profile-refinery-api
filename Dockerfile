FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY pyproject.toml README.md ./
COPY src ./src
COPY schemas ./schemas
COPY config ./config
COPY tests/fixtures ./tests/fixtures
RUN pip install --no-cache-dir .
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "uvicorn tross_linkedin_api.main:app --host 0.0.0.0 --port ${PORT}"]
