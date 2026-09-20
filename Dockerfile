FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LOAD_DOTENV=0
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-production.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt
COPY . .
# No production secrets or local database are included in the image.
RUN DEBUG=1 SECRET_KEY=build-only-not-used-at-runtime python manage.py collectstatic --noinput \
 && DEBUG=1 SECRET_KEY=build-only-not-used-at-runtime python manage.py install_portrait_model
RUN useradd --create-home optimus && chown -R optimus:optimus /app
USER optimus
CMD ["python", "deploy/start.py"]
