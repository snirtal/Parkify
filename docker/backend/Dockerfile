FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PARKIFY_ENV=production \
    HOST=0.0.0.0 \
    PORT=5001

WORKDIR /app

RUN addgroup --system parkify \
    && adduser --system --ingroup parkify --home /app parkify

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py alembic.ini ./
COPY config ./config
COPY controllers ./controllers
COPY models ./models
COPY repositories ./repositories
COPY services ./services
COPY utils ./utils
COPY migrations ./migrations
COPY docker/backend/entrypoint.py /entrypoint.py

RUN chown -R parkify:parkify /app /entrypoint.py

USER parkify
EXPOSE 5001

ENTRYPOINT ["python", "/entrypoint.py"]

FROM runtime AS test

USER root
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
RUN chown -R parkify:parkify /app
USER parkify

ENTRYPOINT ["python", "-m", "pytest"]
CMD ["-v", "-o", "cache_dir=/tmp/pytest-cache"]
