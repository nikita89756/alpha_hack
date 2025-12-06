import pytest
import os

# Устанавливаем переменные окружения для тестов
os.environ.setdefault("KAFKA_URL", "localhost:9092")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("DATABASE_NAME", "test_db")
os.environ.setdefault("OPENROUTER_API_KEY", "test_key")

