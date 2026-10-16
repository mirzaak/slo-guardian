FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv
COPY app/requirements.txt .
RUN pip install -r requirements.txt \
 && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app

COPY app/ app/
COPY loadgen/ loadgen/

ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

USER 10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--timeout-graceful-shutdown", "20"]
