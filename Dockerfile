# Imagen base
FROM python:3.12-slim

# Establecer directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema (ejemplo: psycopg2 necesita gcc y libpq-dev)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el proyecto
COPY . .

# Exponer el puerto para Django
EXPOSE 8000

# Comando por defecto (se puede sobreescribir en docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
