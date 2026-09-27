# Install OS libraries so the same image can render receipts on web and workers.
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Collect versioned assets without database access or production secrets in layers.
RUN python manage.py collectstatic --noinput --settings=config.settings.build
RUN useradd --uid 10001 --create-home feesconnect \
    && mkdir -p /app/private \
    && chown -R feesconnect:feesconnect /app
USER feesconnect
# EXPOSE is documentary; the launcher binds Render's runtime PORT when supplied.
EXPOSE 8000
CMD ["python", "deployment/start.py", "web"]
