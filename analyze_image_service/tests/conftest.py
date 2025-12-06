import pytest
import os

os.environ.setdefault("OPENROUTER_API_KEY", "test_key")
os.environ.setdefault("DEFAULT_MODEL", "test-model")
os.environ.setdefault("MAX_FILE_SIZE", "10485760")  # 10MB
os.environ.setdefault("S3_ACCESS_KEY", "test_access_key")
os.environ.setdefault("S3_SECRET_KEY", "test_secret_key")
os.environ.setdefault("S3_BUCKET_NAME", "test_bucket")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_PUBLIC_URL", "http://localhost:9000")

