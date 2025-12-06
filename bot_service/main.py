"""Точка входа для запуска API-сервиса Support Hints."""

import os
import dotenv
import uvicorn

from web.api import app

dotenv.load_dotenv()


def serve() -> None:
    """Запускает приложение FastAPI через Uvicorn.

    Команда считывает `HOST` и `PORT` из переменных окружения, чтобы можно было
    переопределять сетевые настройки при деплое.

    Returns:
        (None): Вызов блокирует текущий поток на время работы HTTP-сервера.
    """
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8003"))

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    serve()
