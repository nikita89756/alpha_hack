from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Config


def setup_cors(app: FastAPI, config: Config):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
