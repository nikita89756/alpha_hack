import logging
from fastapi import FastAPI

from app.core.config import get_config
from app.middleware.cors import setup_cors
from app.api.router import api_router
from app.api.endpoints.health import router as health_router
from app.core.tags_doc import tags_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = get_config()

app = FastAPI(
    title="Чат бот",
    openapi_tags=tags_metadata
)

setup_cors(app, config)

app.include_router(health_router)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )
