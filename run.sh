#!/bin/bash

# FX Dashboard - Quick Start Script

echo "🚀 FX Dashboard - Quick Start"
echo "=============================="

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker и попробуйте снова."
    exit 1
fi

# Проверяем наличие docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Установите Docker Compose и попробуйте снова."
    exit 1
fi

echo "✅ Docker и Docker Compose найдены"

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создаю на основе env.example..."
    cp env.example .env
    echo "📝 Отредактируйте .env файл, добавив ваши API ключи"
    echo "💡 Затем запустите скрипт снова"
    exit 1
fi

echo "✅ Файл .env найден"

# Определяем режим запуска
MODE=${1:-dev}
case $MODE in
    "dev"|"development")
        echo "🔧 Запускаю в режиме РАЗРАБОТКИ (с автоперезагрузкой)..."
        COMPOSE_FILE="docker-compose.yml"
        ;;
    "prod"|"production")
        echo "🚀 Запускаю в режиме ПРОДАКШЕНА..."
        COMPOSE_FILE="docker-compose.prod.yml"
        ;;
    *)
        echo "❌ Неизвестный режим: $MODE"
        echo "Использование: $0 [dev|prod]"
        echo "  dev  - режим разработки с автоперезагрузкой (по умолчанию)"
        echo "  prod - режим продакшена"
        exit 1
        ;;
esac

# Останавливаем предыдущие контейнеры
echo "🛑 Останавливаю предыдущие контейнеры..."
docker-compose down

# Запускаем приложение
echo "🐳 Запускаю FX Dashboard в Docker..."
docker-compose -f $COMPOSE_FILE up -d --build

echo ""
echo "🎉 FX Dashboard запущен!"
echo "🌐 Откройте браузер и перейдите по адресу: http://localhost:8501"
echo ""
echo "📋 Полезные команды:"
echo "   Остановить: docker-compose -f $COMPOSE_FILE down"
echo "   Логи: docker-compose -f $COMPOSE_FILE logs -f"
echo "   Перезапустить: docker-compose -f $COMPOSE_FILE restart"
echo ""
if [ "$MODE" = "dev" ]; then
    echo "🔄 Автоперезагрузка включена! Изменения в main.py будут применены автоматически"
fi
echo "🔧 Для изменения настроек отредактируйте .env файл и перезапустите"
echo "💡 Для смены режима: $0 [dev|prod]"
