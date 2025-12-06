import os

class Config:
    PROJECT_NAME = "Auth Service"
    DESCRIPTION = """
    ## Сервис аутентификации

    Сервис управления пользователями и токенами.

    ### Возможности
    * Регистрация с валидацией email
    * Безопасное хеширование паролей (bcrypt)
    * JWT токены (Access + Refresh)
    * Верификация токенов для других сервисов

    ### Token Lifetime
    - **Access Token**: 24 часа
    - **Refresh Token**: 30 дней
    """

    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongodb:27017")
    DB_NAME = os.getenv("DB_NAME", "chatbot_db")

    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 30))

    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

    PORT = int(os.getenv("PORT", 8004))


config = Config()
