# FX Dashboard

Веб-приложение для отслеживания курсов валют с использованием API Bitkub и Rapira, написанное на Python с использованием Streamlit.

## Возможности

- Получение курсов валют в реальном времени
- Расчёт маржи и конвертационных курсов
- Поддержка API ключей Bitkub для аутентифицированных запросов
- Экспорт данных в JSON формате
- Современный веб-интерфейс

## Установка

### Локальная установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd rate_dashboard
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env` на основе `env.example`:
```bash
cp env.example .env
# Отредактируйте .env файл, добавив ваши API ключи
```

5. Запустите приложение:
```bash
streamlit run main.py
```

### Запуск в Docker

1. Создайте файл `.env` с вашими настройками:
```bash
cp env.example .env
# Отредактируйте .env файл
```

2. Запустите с помощью Docker Compose:
```bash
docker-compose up -d
```

Или соберите и запустите вручную:
```bash
docker build -t fx-dashboard .
docker run -p 8501:8501 --env-file .env fx-dashboard
```

## Конфигурация

Создайте файл `.env` со следующими переменными:

```env
# Rapira API
RAPIRA_URL=https://api.rapira.net/open/market/rates

# Bitkub API
BITKUB_SERVER_TIME_URL=https://api.bitkub.com/api/servertime
BITKUB_TICKER_URL=https://api.bitkub.com/api/market/ticker?sym=THB_USDT

# Bitkub Authentication (опционально)
BITKUB_API_KEY=your_api_key_here
BITKUB_API_SECRET=your_api_secret_here

# Настройки
SUBTRACT_CONST=0.1
DEFAULT_MARGIN=3.5
```

## Использование

1. Откройте браузер и перейдите по адресу `http://localhost:8501`
2. Настройте источники API в боковой панели
3. При необходимости введите API ключи Bitkub
4. Нажмите "Обновить сейчас" для получения актуальных данных
5. Используйте настройки маржи для расчёта курсов

## Структура проекта

```
rate_dashboard/
├── main.py              # Основное приложение
├── requirements.txt     # Python зависимости
├── Dockerfile          # Docker образ
├── docker-compose.yml  # Docker Compose конфигурация
├── .env.example        # Пример переменных окружения
├── .gitignore          # Git ignore файл
├── .dockerignore       # Docker ignore файл
└── README.md           # Документация
```

## Разработка

Для разработки:

1. Установите зависимости разработки:
```bash
pip install -r requirements.txt
```

2. Запустите в режиме разработки:
```bash
streamlit run main.py --server.runOnSave true
```

## Лицензия

MIT License