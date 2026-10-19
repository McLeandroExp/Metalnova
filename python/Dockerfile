# Imagen del pipeline MetalNova: generación, carga y simulación.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Por defecto solo informa; los comandos reales se pasan con `docker compose run`.
CMD ["python", "-c", "print('MetalNova ingestor listo. Ejemplo: docker compose run --rm ingestor python src/check_connection.py')"]
