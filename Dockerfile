# 1. Берем легкий официальный образ Python
FROM python:3.12-slim

# 2. Устанавливаем системные зависимости для работы с PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 3. Устанавливаем рабочую паку внутри контейнера
WORKDIR /app

# 4. Отключаем буферизацию логов Python (чтобы сразу видеть ошибки в консоли Azure)
ENV PYTHONUNBUFFERED=1

# 5. Копируем и устанавливаем зависимости Django
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. Копируем весь остальной код проекта в контейнер
COPY . /app/

# 7. Открываем порт (в ACA встроенный прокси сам перенаправит трафик сюда)
EXPOSE 8000

# 8. Команда для запуска Django через production-сервер Gunicorn
# Замените 'myproject' на название папки, где лежит ваш файл wsgi.py
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "Warehouse.wsgi:application"]