FROM python:3.11-slim

# Evitar prompts interactivos y buffering de Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Instalar dependencias del sistema mínimas requeridas
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Instalar requerimientos Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar explícitamente los módulos de aplicación sin incluir artefactos locales ni secretos
COPY app.py .
COPY form.py .
COPY __init__.py .
COPY forms/ ./forms/
COPY models/ ./models/
COPY domain/ ./domain/
COPY services/ ./services/
COPY blueprints/ ./blueprints/
COPY templates/ ./templates/
COPY static/ ./static/
COPY Conexión/ ./Conexión/
COPY conexion/ ./conexion/
COPY database/ ./database/

# Crear usuario sin privilegios para ejecutar la app
RUN useradd -m -u 1001 ecogrow && chown -R ecogrow:ecogrow /app
USER ecogrow

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "app:app"]
