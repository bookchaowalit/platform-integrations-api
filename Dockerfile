# Build from the repository root: docker build -t solo-integrations .
# Only the files declared in service.yaml data.reads are baked in; nothing else from the repo.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 INTEGRATIONS_API_HOST=0.0.0.0 INTEGRATIONS_API_ENV=production
WORKDIR /app
COPY vendor/service-auth /app/vendor/service-auth
COPY pyproject.toml server.py _sentry.py /app/
RUN pip install /app/vendor/service-auth /app
COPY data/external_app_registry.ts /app/data/external_app_registry.ts
COPY integrations /app/integrations

RUN useradd --system --uid 10001 app
USER app
EXPOSE 3480
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD python -c "import os, urllib.request; port=os.environ.get('INTEGRATIONS_API_PORT', os.environ.get('PORT', '3480')); urllib.request.urlopen('http://127.0.0.1:'+port+'/ready', timeout=2)"
CMD ["python", "/app/server.py"]
