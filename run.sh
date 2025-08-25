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

# Запускаем приложение
echo "🐳 Запускаю FX Dashboard в Docker..."
docker-compose up -d

echo ""
echo "🎉 FX Dashboard запущен!"
echo "🌐 Откройте браузер и перейдите по адресу: http://localhost:8501"
echo ""
echo "📋 Полезные команды:"
echo "   Остановить: docker-compose down"
echo "   Логи: docker-compose logs -f"
echo "   Перезапустить: docker-compose restart"
echo ""
echo "🔧 Для изменения настроек отредактируйте .env файл и перезапустите"
