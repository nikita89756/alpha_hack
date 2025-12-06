import os

class Settings:
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.default_model = os.getenv("DEFAULT_MODEL", "google/gemma-3-12b-it")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))
        self.allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        self.prompt: str = "Опиши всё, что видишь на этом изображении."
        self.max_tokens: int = 2048
        if not self.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is not set in environment variables")

settings = Settings()