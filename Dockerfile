FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# 1. Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 2. Instalar librerías de Python (ESTO ES LO QUE FALTABA)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 3. Copiar el proyecto
COPY . .

EXPOSE 8000
# Esto corre Django de forma profesional
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "sistema.wsgi:application"]