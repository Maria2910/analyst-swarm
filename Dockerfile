FROM python:3.11-slim

# Неинтерактивный режим для apt
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Создаём non-root пользователя
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash appuser

# Рабочая директория
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код проекта (но не монтируем — код будет read-only из volume)
COPY . .

# Меняем владельца рабочей директории
RUN chown -R appuser:appuser /app

# Переключаемся на non-root пользователя
USER appuser

# По умолчанию запускаем multi_agent
CMD ["python", "multi_agent.py"]