import pytest
import os

os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("KAFKA_TOPIC", "test-topic")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("REDIS_HISTORY_MAX_MESSAGES", "200")
os.environ.setdefault("REDIS_HISTORY_TTL_SECONDS", "604800")

