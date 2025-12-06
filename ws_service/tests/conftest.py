import pytest
import os

os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("KAFKA_BOT_RESPONSE_TOPIC", "test-bot-responses")
os.environ.setdefault("KAFKA_TITLE_TOPIC", "test-title-topic")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("MESSAGE_SERVICE_URL", "http://localhost:8001")
os.environ.setdefault("CHAT_AUTO_DELETE_DELAY", "15")

