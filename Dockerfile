# Используем официальный Python образ
FROM python:3.11-slim as base

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Этап разработки
FROM base as development
# В режиме разработки код монтируется через volumes
# Запускаем с автоперезагрузкой
CMD ["streamlit", "run", "main.py", "--server.runOnSave", "true", "--server.fileWatcherType", "poll"]

# Этап продакшена
FROM base as production
# Копируем код приложения
COPY . .

# Открываем порт для Streamlit
EXPOSE 8501

# Устанавливаем переменные окружения для Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

# Запускаем приложение
CMD ["streamlit", "run", "main.py"]
